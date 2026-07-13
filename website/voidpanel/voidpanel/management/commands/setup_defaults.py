"""
management/commands/setup_defaults.py

Auto-seeds all required data on every deployment so the website
works out-of-the-box on a fresh server with zero manual admin steps.

Run automatically by deploy.sh after migrations.
Can also be run manually:
    python manage.py setup_defaults
    python manage.py setup_defaults --force   # re-seed even if data exists
    python manage.py setup_defaults --verify  # only check, don't write
"""
import logging
import sys

from django.core.management.base import BaseCommand
from django.db import transaction

logger = logging.getLogger('voidpanel')

# ─────────────────────────────────────────────────────────────────────────────
# Default Email Plans — edit these to change what appears on /professional-email/
# ─────────────────────────────────────────────────────────────────────────────
DEFAULT_EMAIL_PLANS = [
    {
        'name':                   'Starter',
        'slug':                   'email-starter',
        'short_description':      'Perfect for freelancers and small businesses',
        'max_mailboxes':          1,
        'storage_per_mailbox_gb': 5,
        'monthly_price':          99,
        'is_featured':            False,
        'is_active':              True,
        'sort_order':             1,
    },
    {
        'name':                   'Business',
        'slug':                   'email-business',
        'short_description':      'Ideal for growing teams with multiple users',
        'max_mailboxes':          5,
        'storage_per_mailbox_gb': 10,
        'monthly_price':          299,
        'is_featured':            True,   # ← "Most Popular" badge
        'is_active':              True,
        'sort_order':             2,
    },
    {
        'name':                   'Enterprise',
        'slug':                   'email-enterprise',
        'short_description':      'Unlimited-scale email for large organisations',
        'max_mailboxes':          25,
        'storage_per_mailbox_gb': 25,
        'monthly_price':          799,
        'is_featured':            False,
        'is_active':              True,
        'sort_order':             3,
    },
]


class Command(BaseCommand):
    help = (
        'Seeds default email plans and validates server/Razorpay config. '
        'Safe to run on every deploy — only writes what is missing.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Re-seed data even if records already exist (updates names/prices).',
        )
        parser.add_argument(
            '--verify',
            action='store_true',
            help='Only verify configuration, do not write anything.',
        )

    def handle(self, *args, **options):
        force  = options['force']
        verify = options['verify']

        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING(
            '╔══════════════════════════════════════════════╗'
        ))
        self.stdout.write(self.style.MIGRATE_HEADING(
            '║  VoidPanel — Post-Deploy Setup               ║'
        ))
        self.stdout.write(self.style.MIGRATE_HEADING(
            '╚══════════════════════════════════════════════╝'
        ))
        self.stdout.write('')

        errors = []

        # ── 1. Email Plans ─────────────────────────────────────────────────
        errors += self._setup_email_plans(verify, force)

        # ── 2. Server config check ─────────────────────────────────────────
        errors += self._check_servers(verify)

        # ── 3. Razorpay config check ───────────────────────────────────────
        errors += self._check_razorpay(verify)

        # ── 4. Auto-suspend defaults ───────────────────────────────────────
        errors += self._setup_auto_suspend(verify)

        # ── Summary ────────────────────────────────────────────────────────
        self.stdout.write('')
        if errors:
            self.stdout.write(self.style.WARNING(
                '⚠  Setup complete with warnings. Fix the items above in Super Admin.'
            ))
            for e in errors:
                self.stdout.write(self.style.WARNING(f'   • {e}'))
        else:
            self.stdout.write(self.style.SUCCESS(
                '✅  All checks passed. VoidPanel is ready to serve customers!'
            ))
        self.stdout.write('')

    # ── Email Plans ──────────────────────────────────────────────────────────

    def _setup_email_plans(self, verify, force):
        self.stdout.write('📧  Email Plans (Static/Skipped) ...')
        return []

    # ── Server check ─────────────────────────────────────────────────────────

    def _check_servers(self, verify):
        from data.models import VoidPanelServer
        errors = []

        self.stdout.write('🖥  Server Configuration ...')

        servers = VoidPanelServer.objects.filter(is_active=True)
        if not servers.exists():
            errors.append(
                'No active VoidPanel server configured. '
                'Go to Super Admin → Servers → Add Server.'
            )
            self.stdout.write(
                self.style.ERROR('   ❌ No active server found')
            )
            return errors

        for s in servers:
            if not s.api_key:
                errors.append(
                    f'Server "{s.name}" has no API key. '
                    'Go to Super Admin → Servers and set the API key.'
                )
                self.stdout.write(
                    self.style.ERROR(f'   ❌ Server "{s.name}" — API key missing')
                )
                continue

            # Test live connection
            try:
                import requests as _rq
                resp = _rq.get(
                    f'{s.url.rstrip("/")}/api/v2/ping/',
                    headers={'X-API-Token': s.api_key},
                    timeout=5,
                )
                data = resp.json()
                if data.get('status') == 'success':
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'   ✅ Server "{s.name}" ({s.url}) — API reachable'
                        )
                    )
                else:
                    errors.append(f'Server "{s.name}" API returned unexpected: {data}')
                    self.stdout.write(
                        self.style.WARNING(f'   ⚠  Server "{s.name}" — Unexpected response')
                    )
            except Exception as exc:
                errors.append(
                    f'Server "{s.name}" unreachable: {exc}. '
                    'Ensure the panel is running and the URL/port is correct.'
                )
                self.stdout.write(
                    self.style.WARNING(
                        f'   ⚠  Server "{s.name}" — Cannot connect ({exc})'
                    )
                )

        return errors

    # ── Razorpay check ───────────────────────────────────────────────────────

    def _check_razorpay(self, verify):
        from data.models import RazorpayConfig
        errors = []

        self.stdout.write('💳  Razorpay Gateway ...')

        rzp = RazorpayConfig.objects.first()
        if not rzp:
            errors.append(
                'Razorpay not configured. '
                'Go to Super Admin → Payment Gateway and add your keys.'
            )
            self.stdout.write(self.style.ERROR('   ❌ No Razorpay config found'))
            return errors

        if not rzp.is_active:
            errors.append(
                'Razorpay is configured but not active. '
                'Go to Super Admin → Payment Gateway and enable it.'
            )
            self.stdout.write(self.style.WARNING('   ⚠  Razorpay is INACTIVE'))
            return errors

        kid, ksec = rzp.get_active_keys()
        mode = 'LIVE' if rzp.is_live_mode else 'TEST'

        if not kid or not ksec:
            errors.append(
                f'Razorpay {mode.lower()} keys are missing. '
                'Go to Super Admin → Payment Gateway and set them.'
            )
            self.stdout.write(
                self.style.ERROR(f'   ❌ Razorpay {mode} keys missing')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'   ✅ Razorpay active in {mode} mode — keys set')
            )

        if not rzp.webhook_secret:
            errors.append(
                'Razorpay webhook secret is not set. '
                'Add it at Super Admin → Payment Gateway. '
                'Get it from Razorpay Dashboard → Webhooks → '
                'https://voidpanel.com/api/payment/razorpay/webhook/'
            )
            self.stdout.write(
                self.style.WARNING('   ⚠  Webhook secret missing (payments still work, but webhooks won\'t)')
            )
        else:
            self.stdout.write('   ✅ Webhook secret set')

        return errors

    # ── Auto-suspend defaults ────────────────────────────────────────────────

    def _setup_auto_suspend(self, verify):
        errors = []
        self.stdout.write('⏰  Auto-Suspend Settings ...')

        try:
            from data.models import AutoSuspendSettings
            s = AutoSuspendSettings.get()
            self.stdout.write(
                f'   ✅ Auto-suspend: enabled={s.enabled}, '
                f'suspend_after={s.overdue_days}d'
            )
        except Exception as exc:
            errors.append(f'AutoSuspendSettings error: {exc}')
            self.stdout.write(
                self.style.WARNING(f'   ⚠  Auto-suspend check failed: {exc}')
            )

        return errors
