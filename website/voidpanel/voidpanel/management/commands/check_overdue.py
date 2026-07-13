"""
management/commands/check_overdue.py

Daily management command to enforce overdue invoice auto-suspension.

Usage:
    python manage.py check_overdue

Cron (runs daily at 6 AM):
    0 6 * * * cd /var/www/voidpanel-web && python manage.py check_overdue >> /var/log/voidpanel_overdue.log 2>&1
"""
import logging
import requests
from datetime import date

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import EmailMessage
from django.template.loader import render_to_string

from data.models import AutoSuspendSettings, HostingService, Invoice, PortalActivity

logger = logging.getLogger('voidpanel')


class Command(BaseCommand):
    help = 'Check overdue invoices and auto-suspend services as configured by superadmin.'

    def handle(self, *args, **options):
        settings = AutoSuspendSettings.get()

        if not settings.enabled:
            self.stdout.write(self.style.WARNING('Auto-suspend is DISABLED. Skipping.'))
            return

        today = date.today()
        self.stdout.write(f'[check_overdue] Running on {today} | suspend_at={settings.overdue_days}d | warn_at={settings.warning_days}d')

        # Find all active hosting services
        active_services = HostingService.objects.filter(
            status='active'
        ).select_related('user', 'server')

        suspended_count = 0
        warned_count = 0

        for service in active_services:
            # Find the oldest overdue/unpaid invoice for this user
            overdue_inv = Invoice.objects.filter(
                user=service.user,
                status__in=['overdue', 'unpaid'],
                due_date__lt=today,
            ).order_by('due_date').first()

            if not overdue_inv:
                continue

            days_overdue = (today - overdue_inv.due_date).days

            self.stdout.write(
                f'  → {service.domain}: {days_overdue} days overdue (Invoice: {overdue_inv.invoice_number})'
            )

            # ── Warning email (before suspension threshold) ─────────────────
            if settings.send_warning_email and settings.warning_days <= days_overdue < settings.overdue_days:
                if self._send_overdue_warning(service, overdue_inv, days_overdue, settings.overdue_days):
                    warned_count += 1
                    self.stdout.write(self.style.WARNING(f'    ⚠ Warning email sent to {service.user.email}'))

            # ── Suspend ─────────────────────────────────────────────────────
            elif days_overdue >= settings.overdue_days:
                self._suspend_service(service, overdue_inv, days_overdue, settings)
                suspended_count += 1
                self.stdout.write(self.style.ERROR(f'    ✗ SUSPENDED {service.domain} ({days_overdue} days overdue)'))

        self.stdout.write(self.style.SUCCESS(
            f'[check_overdue] Done. Suspended: {suspended_count}, Warned: {warned_count}'
        ))

    def _suspend_service(self, service, invoice, days_overdue, settings):
        """Call VoidPanel API to suspend the account and update service status."""
        # Call VoidPanel API v2
        panel_base = service.panel_base_url
        if panel_base and service.server:
            try:
                api_key = service.server.api_key or ''
                resp = requests.post(
                    f'{panel_base}/api/v2/accounts/suspend/',
                    json={'domain': service.domain},
                    headers={'X-API-Token': api_key},
                    timeout=15,
                )
                logger.info('Panel suspend response for %s: %s %s', service.domain, resp.status_code, resp.text[:200])
            except Exception as exc:
                logger.error('Failed to call panel suspend for %s: %s', service.domain, exc)

        # Update service status
        service.status = 'suspended'
        service.save(update_fields=['status'])

        # Log activity
        PortalActivity.objects.create(
            user=service.user,
            category='billing',
            title=f'Service auto-suspended: {service.domain}',
            description=(
                f'Invoice {invoice.invoice_number} is {days_overdue} days overdue. '
                f'Service automatically suspended per billing policy.'
            ),
        )

        # Send suspension email
        if settings.send_suspension_email:
            self._send_suspension_email(service, invoice, days_overdue)

    def _send_overdue_warning(self, service, invoice, days_overdue, suspend_at_days):
        """Send a warning email that suspension is approaching."""
        try:
            from data.models import OutboundEmailProfile
            smtp_profile = (
                OutboundEmailProfile.objects
                .filter(is_active=True)
                .order_by('-is_default')
                .first()
            )
            days_left = suspend_at_days - days_overdue
            subject = f'⚠ Payment Overdue — {service.domain} will be suspended in {days_left} day(s)'
            body = (
                f'Dear {service.user.get_full_name() or service.user.username},\n\n'
                f'This is a reminder that your invoice {invoice.invoice_number} '
                f'for {service.domain} is {days_overdue} days overdue.\n\n'
                f'Your service will be automatically SUSPENDED in {days_left} day(s) '
                f'if payment is not received.\n\n'
                f'Please pay your invoice immediately at: https://voidpanel.com/portal/\n\n'
                f'Amount due: {invoice.total} {invoice.currency}\n\n'
                f'— VoidPanel Billing Team'
            )
            email = EmailMessage(
                subject=subject,
                body=body,
                from_email='billing@voidpanel.com',
                to=[service.user.email],
            )
            email.send(fail_silently=True)
            return True
        except Exception as exc:
            logger.error('Warning email failed for %s: %s', service.domain, exc)
            return False

    def _send_suspension_email(self, service, invoice, days_overdue):
        """Send suspension notification email."""
        try:
            subject = f'🚨 Service Suspended: {service.domain} — Payment Overdue'
            body = (
                f'Dear {service.user.get_full_name() or service.user.username},\n\n'
                f'Your hosting service for {service.domain} has been suspended because '
                f'invoice {invoice.invoice_number} is {days_overdue} days overdue.\n\n'
                f'To reactivate your service, please pay your outstanding balance at:\n'
                f'https://voidpanel.com/portal/\n\n'
                f'Amount due: {invoice.total} {invoice.currency}\n\n'
                f'Once payment is received, your service will be reactivated within minutes.\n\n'
                f'If you believe this is an error, please open a support ticket:\n'
                f'https://voidpanel.com/portal/ticket/new/\n\n'
                f'— VoidPanel Billing Team'
            )
            email = EmailMessage(
                subject=subject,
                body=body,
                from_email='billing@voidpanel.com',
                to=[service.user.email],
            )
            email.send(fail_silently=True)
        except Exception as exc:
            logger.error('Suspension email failed for %s: %s', service.domain, exc)
