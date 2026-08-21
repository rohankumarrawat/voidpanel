"""
VoidOnyx — Razorpay Webhook Handler
====================================
Receives and processes Razorpay subscription lifecycle events.

Endpoint: POST /api/webhook/razorpay/

Events handled:
  - subscription.authenticated  → User authorized mandate
  - subscription.activated      → First charge successful
  - subscription.charged        → Recurring charge captured
  - subscription.halted         → Payment failed
  - subscription.cancelled      → Subscription cancelled
  - subscription.completed      → All cycles done
  - subscription.pending        → Charge pending
"""

import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal

from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.db import transaction

from .razorpay_subscriptions import verify_webhook_signature

_logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def razorpay_webhook(request):
    """
    Razorpay webhook receiver.
    Verifies signature, then dispatches to the appropriate handler.
    """
    signature = request.headers.get('X-Razorpay-Signature', '')
    body = request.body

    if not signature:
        _logger.warning("Webhook received without signature header")
        return JsonResponse({'error': 'Missing signature'}, status=400)

    # Verify webhook signature
    if not verify_webhook_signature(body, signature):
        _logger.warning("Webhook signature verification failed")
        return JsonResponse({'error': 'Invalid signature'}, status=401)

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    event = payload.get('event', '')
    _logger.info("Razorpay webhook received: %s", event)

    # Dispatch to handler
    handlers = {
        'subscription.authenticated': _handle_subscription_authenticated,
        'subscription.activated':     _handle_subscription_activated,
        'subscription.charged':       _handle_subscription_charged,
        'subscription.halted':        _handle_subscription_halted,
        'subscription.cancelled':     _handle_subscription_cancelled,
        'subscription.completed':     _handle_subscription_completed,
        'subscription.pending':       _handle_subscription_pending,
    }

    handler = handlers.get(event)
    if handler:
        try:
            handler(payload)
        except Exception as e:
            _logger.error("Error handling webhook event %s: %s", event, e, exc_info=True)
            # Still return 200 to prevent Razorpay retries on app errors
            return HttpResponse(status=200)
    else:
        _logger.info("Unhandled webhook event: %s", event)

    return HttpResponse(status=200)


def _get_subscription_from_payload(payload):
    """Extract the AutoPaySubscription from the webhook payload."""
    from data.models import AutoPaySubscription

    entity = payload.get('payload', {}).get('subscription', {}).get('entity', {})
    sub_id = entity.get('id', '')

    if not sub_id:
        _logger.warning("No subscription ID in webhook payload")
        return None, entity

    try:
        db_sub = AutoPaySubscription.objects.get(razorpay_subscription_id=sub_id)
        return db_sub, entity
    except AutoPaySubscription.DoesNotExist:
        _logger.warning("Subscription %s not found in DB", sub_id)
        return None, entity


def _handle_subscription_authenticated(payload):
    """
    User has authorized the auto-pay mandate.
    Activate the service immediately (trial period starts now).
    """
    db_sub, entity = _get_subscription_from_payload(payload)
    if not db_sub:
        return

    _logger.info("Subscription authenticated: %s (user=%s)", db_sub.razorpay_subscription_id, db_sub.user_id)

    with transaction.atomic():
        db_sub.status = 'authenticated'
        db_sub.auth_attempts += 1
        db_sub.trial_start = timezone.now()
        db_sub.trial_end = timezone.now() + timedelta(days=db_sub.trial_days)
        db_sub.save(update_fields=[
            'status', 'auth_attempts', 'trial_start', 'trial_end', 'updated_at'
        ])

    # Activate the linked service (free trial starts)
    _activate_service_for_subscription(db_sub)

    # Log portal activity
    _log_activity(db_sub.user, 'subscription',
                  f'Auto-pay activated: {db_sub.package_name}',
                  f'30-day free trial started. First charge on {db_sub.trial_end:%Y-%m-%d}.')

    # Send notification
    _send_subscription_notification(
        db_sub,
        f"✅ Auto-pay activated for {db_sub.package_name}! "
        f"Your 30-day free trial has started. "
        f"First charge of ₹{db_sub.amount} on {db_sub.trial_end:%d %b %Y}."
    )


def _handle_subscription_activated(payload):
    """
    First charge has been made (after trial period ends).
    The subscription is now fully active.
    """
    db_sub, entity = _get_subscription_from_payload(payload)
    if not db_sub:
        return

    _logger.info("Subscription activated (first charge): %s", db_sub.razorpay_subscription_id)

    with transaction.atomic():
        db_sub.status = 'active'

        # Parse period from Razorpay
        current_start = entity.get('current_start')
        current_end = entity.get('current_end')
        if current_start:
            db_sub.current_period_start = datetime.fromtimestamp(current_start, tz=timezone.utc)
        if current_end:
            db_sub.current_period_end = datetime.fromtimestamp(current_end, tz=timezone.utc)

        charge_at = entity.get('charge_at')
        if charge_at:
            db_sub.charge_at = datetime.fromtimestamp(charge_at, tz=timezone.utc)

        db_sub.paid_count = entity.get('paid_count', db_sub.paid_count)
        db_sub.save()

    # Record the payment
    _record_payment_from_payload(db_sub, payload)


def _handle_subscription_charged(payload):
    """
    A recurring charge has been captured.
    Extend the service period and create an invoice.
    """
    db_sub, entity = _get_subscription_from_payload(payload)
    if not db_sub:
        return

    _logger.info("Subscription charged: %s (paid_count=%s)",
                 db_sub.razorpay_subscription_id, entity.get('paid_count'))

    with transaction.atomic():
        db_sub.status = 'active'

        current_start = entity.get('current_start')
        current_end = entity.get('current_end')
        if current_start:
            db_sub.current_period_start = datetime.fromtimestamp(current_start, tz=timezone.utc)
        if current_end:
            db_sub.current_period_end = datetime.fromtimestamp(current_end, tz=timezone.utc)

        charge_at = entity.get('charge_at')
        if charge_at:
            db_sub.charge_at = datetime.fromtimestamp(charge_at, tz=timezone.utc)

        db_sub.paid_count = entity.get('paid_count', db_sub.paid_count)
        db_sub.save()

    # Record the payment and create invoice
    _record_payment_from_payload(db_sub, payload)

    # Extend the service due date
    _extend_service_due_date(db_sub)

    _log_activity(db_sub.user, 'billing',
                  f'Auto-pay charged: {db_sub.package_name}',
                  f'₹{db_sub.amount} charged successfully.')


def _handle_subscription_halted(payload):
    """
    Payment failed. Suspend the service after grace period.
    """
    db_sub, entity = _get_subscription_from_payload(payload)
    if not db_sub:
        return

    _logger.warning("Subscription halted: %s", db_sub.razorpay_subscription_id)

    with transaction.atomic():
        db_sub.status = 'halted'
        db_sub.save(update_fields=['status', 'updated_at'])

    _log_activity(db_sub.user, 'subscription',
                  f'⚠️ Auto-pay failed: {db_sub.package_name}',
                  'Payment could not be processed. Service may be suspended if not resolved.')

    _send_subscription_notification(
        db_sub,
        f"⚠️ Auto-pay payment failed for {db_sub.package_name}. "
        f"Please update your payment method to avoid service interruption."
    )


def _handle_subscription_cancelled(payload):
    """
    Subscription cancelled (by user or admin).
    """
    db_sub, entity = _get_subscription_from_payload(payload)
    if not db_sub:
        return

    _logger.info("Subscription cancelled: %s", db_sub.razorpay_subscription_id)

    with transaction.atomic():
        db_sub.status = 'cancelled'
        db_sub.ended_at = timezone.now()
        db_sub.save(update_fields=['status', 'ended_at', 'updated_at'])

    _log_activity(db_sub.user, 'subscription',
                  f'Auto-pay cancelled: {db_sub.package_name}',
                  'Service will remain active until the end of the current billing period.')


def _handle_subscription_completed(payload):
    """All billing cycles completed."""
    db_sub, entity = _get_subscription_from_payload(payload)
    if not db_sub:
        return

    with transaction.atomic():
        db_sub.status = 'completed'
        db_sub.ended_at = timezone.now()
        db_sub.save(update_fields=['status', 'ended_at', 'updated_at'])


def _handle_subscription_pending(payload):
    """Charge is pending (UPI mandate, etc)."""
    db_sub, entity = _get_subscription_from_payload(payload)
    if not db_sub:
        return
    _logger.info("Subscription charge pending: %s", db_sub.razorpay_subscription_id)


# ── Helper Functions ──────────────────────────────────────────────────────────

def _record_payment_from_payload(db_sub, payload):
    """Extract payment info from webhook and create a SubscriptionPayment + Invoice."""
    from data.models import SubscriptionPayment, Invoice

    payment_entity = payload.get('payload', {}).get('payment', {}).get('entity', {})
    if not payment_entity:
        return

    payment_id = payment_entity.get('id', '')
    if not payment_id:
        return

    # Avoid duplicates
    if SubscriptionPayment.objects.filter(razorpay_payment_id=payment_id).exists():
        return

    amount = Decimal(str(payment_entity.get('amount', 0))) / 100  # paise → rupees
    currency = payment_entity.get('currency', 'INR')

    # Create VoidOnyx Invoice
    invoice = Invoice.objects.create(
        user=db_sub.user,
        invoice_number=_auto_invoice_number(db_sub.user),
        description=f"Auto-Pay: {db_sub.package_name} — Monthly",
        status='paid',
        total=amount,
        currency=currency,
        due_date=timezone.now().date(),
        paid_date=timezone.now().date(),
    )

    # Create payment record
    SubscriptionPayment.objects.create(
        subscription=db_sub,
        razorpay_payment_id=payment_id,
        razorpay_invoice_id=payment_entity.get('invoice_id', ''),
        amount=amount,
        currency=currency,
        status='captured',
        period_start=db_sub.current_period_start,
        period_end=db_sub.current_period_end,
        invoice=invoice,
    )

    _logger.info("Recorded subscription payment: %s (₹%s)", payment_id, amount)


def _auto_invoice_number(user):
    """Generate next invoice number for auto-pay."""
    import re
    from data.models import Invoice

    prefix = f"VP-AP-{user.pk}-"
    existing = Invoice.objects.filter(
        user=user, invoice_number__startswith=prefix
    ).order_by('-invoice_number')

    if existing.exists():
        last = existing.first().invoice_number
        match = re.search(r'-(\d+)$', last)
        num = int(match.group(1)) + 1 if match else 1
    else:
        num = 1

    return f"{prefix}{num:04d}"


def _activate_service_for_subscription(db_sub):
    """
    Activate the linked VoidOnyx service when auto-pay is authorized.
    The service runs during the trial period (30 days free).
    """
    from data.models import Service, SuiteService

    try:
        if db_sub.service_type in ('hosting', 'wordpress', 'reseller'):
            service = Service.objects.filter(pk=db_sub.service_id).first()
            if service and service.status != 'active':
                service.status = 'active'
                service.save(update_fields=['status'])
                _logger.info("Activated hosting service %s for subscription %s",
                             service.pk, db_sub.razorpay_subscription_id)

        elif db_sub.service_type.startswith('suite_'):
            service = SuiteService.objects.filter(pk=db_sub.service_id).first()
            if service and service.status != 'active':
                service.status = 'active'
                service.save(update_fields=['status'])
                _logger.info("Activated suite service %s for subscription %s",
                             service.pk, db_sub.razorpay_subscription_id)

        # Add other service types as needed (email, erp, gym, etc.)

    except Exception as e:
        _logger.error("Failed to activate service for subscription %s: %s",
                       db_sub.razorpay_subscription_id, e)


def _extend_service_due_date(db_sub):
    """Extend the service next_due_date by 1 month on successful charge."""
    from data.models import Service, SuiteService
    from dateutil.relativedelta import relativedelta

    try:
        new_due = (timezone.now() + relativedelta(months=1)).date()

        if db_sub.service_type in ('hosting', 'wordpress', 'reseller'):
            Service.objects.filter(pk=db_sub.service_id).update(next_due_date=new_due)
        elif db_sub.service_type.startswith('suite_'):
            SuiteService.objects.filter(pk=db_sub.service_id).update(next_due_date=new_due)

    except Exception as e:
        _logger.error("Failed to extend due date for subscription %s: %s",
                       db_sub.razorpay_subscription_id, e)


def _log_activity(user, category, title, description):
    """Create a PortalActivity entry."""
    try:
        from data.models import PortalActivity
        PortalActivity.objects.create(
            user=user, category=category,
            title=title, description=description,
        )
    except Exception:
        pass


def _send_subscription_notification(db_sub, message):
    """Send WhatsApp/email notification about subscription event."""
    try:
        from voidpanel.views import send_whatsapp_notification_async
        send_whatsapp_notification_async(db_sub.user, message, 'subscription_update')
    except Exception as e:
        _logger.error("Failed to send subscription notification: %s", e)
