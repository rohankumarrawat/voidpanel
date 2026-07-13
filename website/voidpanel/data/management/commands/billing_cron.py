"""
Billing Cron — run daily via OS cron:
    0 2 * * * cd /var/www/voidpanel-site && .venv/bin/python manage.py billing_cron

Actions:
  1. Generate invoices for services due in 7 days (if no invoice exists yet)
  2. Suspend services that are overdue (past due_date and invoice still unpaid)
"""
import logging
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from data.models import HostingService, Invoice
from voidpanel.provisioner import suspend_hosting_account

logger = logging.getLogger(__name__)


def _inv_number(service):
    count = Invoice.objects.filter(user=service.user).count()
    return f"VP-{service.user.id:04d}-{count + 1:03d}"


class Command(BaseCommand):
    help = 'Daily billing cron: generate upcoming invoices and suspend overdue accounts.'

    def handle(self, *args, **options):
        self.stdout.write('[billing_cron] Starting...')
        today = timezone.localdate()
        warning_date = today + timedelta(days=7)

        # ── 1. Generate invoices for services due in 7 days ──────────────────
        upcoming = HostingService.objects.filter(
            status='active',
            next_due_date=warning_date,
        )
        for service in upcoming:
            exists = Invoice.objects.filter(
                user=service.user,
                description__icontains=service.domain,
                status__in=['unpaid', 'draft'],
                due_date=service.next_due_date,
            ).exists()
            if not exists:
                Invoice.objects.create(
                    user=service.user,
                    invoice_number=_inv_number(service),
                    description=f'Renewal: {service.service_name} ({service.domain})',
                    status='unpaid',
                    total=service.monthly_price,
                    currency='USD',
                    due_date=service.next_due_date,
                )
                self.stdout.write(f'  [invoice] Created renewal invoice for {service.domain}')
                logger.info('Created renewal invoice for %s', service.domain)

        # ── 2. Suspend overdue services ───────────────────────────────────────
        overdue_services = HostingService.objects.filter(
            status='active',
            next_due_date__lt=today,
        )
        for service in overdue_services:
            has_unpaid = Invoice.objects.filter(
                user=service.user,
                description__icontains=service.domain,
                status__in=['unpaid', 'overdue'],
            ).exists()
            if has_unpaid:
                # Mark overdue
                Invoice.objects.filter(
                    user=service.user,
                    description__icontains=service.domain,
                    status='unpaid',
                ).update(status='overdue')

                # Suspend via VoidPanel API
                result = suspend_hosting_account(service.domain)
                service.status = 'suspended'
                service.save(update_fields=['status'])
                self.stdout.write(f'  [suspend] Suspended {service.domain}: {result}')
                logger.info('Suspended %s via API: %s', service.domain, result)

        self.stdout.write('[billing_cron] Done.')
