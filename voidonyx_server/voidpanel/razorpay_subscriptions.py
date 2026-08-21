"""
VoidOnyx — Razorpay Subscriptions API Integration
===================================================
Handles creation/management of Razorpay Plans and Subscriptions
for the auto-pay feature (monthly only, 30-day free trial).

Razorpay Subscriptions API docs:
  https://razorpay.com/docs/api/payments/subscriptions/

Flow:
  1. get_or_create_plan()  → ensures a Razorpay Plan exists for the package
  2. create_subscription() → creates a subscription with 30-day trial
  3. Webhook handles lifecycle events (authenticated, charged, halted, cancelled)
"""

import logging
from decimal import Decimal
from typing import Optional, Tuple

_logger = logging.getLogger(__name__)

TRIAL_DAYS = 30  # Free trial period for auto-pay


def _get_razorpay_client():
    """
    Return an authenticated razorpay.Client using the active RazorpayConfig.
    Raises RuntimeError if Razorpay is not configured or the SDK is missing.
    """
    try:
        import razorpay
    except ImportError:
        raise RuntimeError("razorpay SDK not installed. Run: pip install razorpay")

    from data.models import RazorpayConfig
    config = RazorpayConfig.get()
    if not config or not config.is_ready:
        raise RuntimeError("Razorpay is not configured or inactive.")

    if config.is_live_mode:
        key_id, key_secret = config.live_key_id, config.live_key_secret
    else:
        key_id, key_secret = config.test_key_id, config.test_key_secret

    if not key_id or not key_secret:
        raise RuntimeError("Razorpay key_id/key_secret not set.")

    return razorpay.Client(auth=(key_id, key_secret)), config


def get_or_create_plan(
    service_type: str,
    package_id: str,
    plan_name: str,
    monthly_amount: Decimal,
    currency: str = 'INR',
) -> 'RazorpayPlan':
    """
    Get or create a Razorpay Plan for the given VoidOnyx package.
    Plans are cached in the RazorpayPlan model.

    Args:
        service_type:   e.g. 'hosting', 'suite_hrms', 'email'
        package_id:     VoidOnyx package identifier (e.g. '1', '2', 'starter')
        plan_name:      Human-readable name (e.g. "Cloud Pro — Monthly Auto-Pay")
        monthly_amount: Price in INR (e.g. Decimal('299.00'))
        currency:       Currency code (default 'INR')

    Returns:
        RazorpayPlan instance
    """
    from data.models import RazorpayPlan

    # Check cache first
    existing = RazorpayPlan.objects.filter(
        service_type=service_type,
        package_id=str(package_id),
        is_active=True,
    ).first()

    if existing:
        # Verify amount hasn't changed
        if existing.amount != monthly_amount:
            _logger.warning(
                "Plan price mismatch for %s/%s: DB=₹%s vs requested=₹%s. "
                "Creating new Razorpay plan.",
                service_type, package_id, existing.amount, monthly_amount
            )
            existing.is_active = False
            existing.save(update_fields=['is_active'])
        else:
            return existing

    # Create plan on Razorpay
    client, config = _get_razorpay_client()

    amount_paise = int(monthly_amount * 100)  # Razorpay expects paise

    razorpay_plan = client.plan.create({
        "period": "monthly",
        "interval": 1,
        "item": {
            "name": plan_name,
            "amount": amount_paise,
            "currency": currency,
            "description": f"VoidOnyx {plan_name} — Monthly Auto-Pay",
        },
    })

    razorpay_plan_id = razorpay_plan['id']
    _logger.info("Created Razorpay plan: %s for %s/%s (₹%s/mo)",
                 razorpay_plan_id, service_type, package_id, monthly_amount)

    # Cache in DB
    db_plan = RazorpayPlan.objects.create(
        service_type=service_type,
        package_id=str(package_id),
        razorpay_plan_id=razorpay_plan_id,
        plan_name=plan_name,
        amount=monthly_amount,
        currency=currency,
        razorpay_interval=1,
        razorpay_period='monthly',
        is_active=True,
    )

    return db_plan


def create_subscription(
    user,
    razorpay_plan: 'RazorpayPlan',
    service_type: str,
    service_id: int,
    package_id: str,
    package_name: str,
    customer_email: str = '',
    customer_contact: str = '',
) -> Tuple['AutoPaySubscription', dict]:
    """
    Create a Razorpay Subscription with a 30-day free trial.

    Args:
        user:             Django user
        razorpay_plan:    RazorpayPlan instance
        service_type:     e.g. 'hosting'
        service_id:       PK of the linked VoidOnyx service
        package_id:       Package identifier
        package_name:     Human-readable package name
        customer_email:   For Razorpay notifications
        customer_contact: Phone number for Razorpay

    Returns:
        (AutoPaySubscription, razorpay_response_dict)
    """
    from data.models import AutoPaySubscription
    from django.utils import timezone
    from datetime import timedelta

    client, config = _get_razorpay_client()

    # Build subscription payload
    sub_data = {
        "plan_id": razorpay_plan.razorpay_plan_id,
        "total_count": 0,          # 0 = infinite (until cancelled)
        "quantity": 1,
        "customer_notify": 1,      # Razorpay sends payment reminders
        "start_at": int((timezone.now() + timedelta(days=TRIAL_DAYS)).timestamp()),
        "notes": {
            "voidonyx_user_id": str(user.pk),
            "service_type": service_type,
            "service_id": str(service_id),
            "package_id": str(package_id),
            "package_name": package_name,
        },
    }

    # Add customer info if available
    if customer_email or customer_contact:
        sub_data["notify_info"] = {}
        if customer_email:
            sub_data["notify_info"]["notify_email"] = customer_email
        if customer_contact:
            sub_data["notify_info"]["notify_phone"] = customer_contact

    razorpay_sub = client.subscription.create(sub_data)

    _logger.info(
        "Created Razorpay subscription: %s for user %s (%s/%s), "
        "trial ends: %s",
        razorpay_sub['id'], user.pk, service_type, package_id,
        timezone.now() + timedelta(days=TRIAL_DAYS),
    )

    # Create local record
    trial_start = timezone.now()
    trial_end = trial_start + timedelta(days=TRIAL_DAYS)

    db_sub = AutoPaySubscription.objects.create(
        user=user,
        razorpay_subscription_id=razorpay_sub['id'],
        razorpay_plan=razorpay_plan,
        service_type=service_type,
        service_id=service_id,
        package_id=str(package_id),
        package_name=package_name,
        amount=razorpay_plan.amount,
        currency=razorpay_plan.currency,
        total_count=0,
        has_free_trial=True,
        trial_days=TRIAL_DAYS,
        trial_start=trial_start,
        trial_end=trial_end,
        status='created',
        short_url=razorpay_sub.get('short_url', ''),
    )

    return db_sub, razorpay_sub


def cancel_subscription(subscription_id: str, cancel_at_cycle_end: bool = True) -> dict:
    """
    Cancel a Razorpay subscription.

    Args:
        subscription_id:     Razorpay subscription ID (sub_XXXX)
        cancel_at_cycle_end: If True, cancel at end of current billing period.
                             If False, cancel immediately.
    Returns:
        Razorpay response dict
    """
    client, config = _get_razorpay_client()

    result = client.subscription.cancel(subscription_id, {
        "cancel_at_cycle_end": 1 if cancel_at_cycle_end else 0,
    })

    _logger.info("Cancelled Razorpay subscription: %s (at_cycle_end=%s)",
                 subscription_id, cancel_at_cycle_end)

    # Update local record
    from data.models import AutoPaySubscription
    from django.utils import timezone

    AutoPaySubscription.objects.filter(
        razorpay_subscription_id=subscription_id
    ).update(
        status='cancelled',
        ended_at=timezone.now(),
        updated_at=timezone.now(),
    )

    return result


def fetch_subscription(subscription_id: str) -> dict:
    """Fetch current subscription details from Razorpay."""
    client, config = _get_razorpay_client()
    return client.subscription.fetch(subscription_id)


def verify_webhook_signature(body: bytes, signature: str) -> bool:
    """
    Verify a Razorpay webhook signature.

    Args:
        body:      Raw request body bytes
        signature: X-Razorpay-Signature header value

    Returns:
        True if signature is valid
    """
    try:
        import razorpay
    except ImportError:
        _logger.error("razorpay SDK not installed — cannot verify webhook")
        return False

    from data.models import RazorpayConfig
    config = RazorpayConfig.get()
    if not config or not config.webhook_secret:
        _logger.error("Webhook secret not configured in RazorpayConfig")
        return False

    try:
        client = razorpay.Client(auth=('', ''))  # Auth not needed for verification
        client.utility.verify_webhook_signature(
            body.decode('utf-8'),
            signature,
            config.webhook_secret,
        )
        return True
    except razorpay.errors.SignatureVerificationError:
        _logger.warning("Webhook signature verification failed")
        return False
    except Exception as e:
        _logger.error("Webhook verification error: %s", e)
        return False
