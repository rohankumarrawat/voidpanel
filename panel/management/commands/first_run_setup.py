"""
panel/management/commands/first_run_setup.py

Run automatically after every install to bootstrap the panel.
Usage: python manage.py first_run_setup [--force]

Does the following (each step is idempotent):
  1. Runs migrations if pending
  2. Collects static files
  3. Creates a temporary local license so /activate/ doesn't loop to 404
  4. Prints the activation URL
"""
import secrets
import socket
import sys

from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Bootstrap a fresh VoidPanel installation (migrations, static, temp license).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Re-run even if already set up.',
        )

    def handle(self, *args, **options):
        force = options.get('force', False)

        # ── 1. Run any pending migrations ────────────────────────────────────
        self.stdout.write(self.style.MIGRATE_HEADING('\n[1/4] Running migrations...'))
        from django.core.management import call_command
        # Always make migrations first to catch new model fields (e.g. db_pass on InstalledScript)
        try:
            call_command('makemigrations', '--no-input', verbosity=0)
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'    ⚠ makemigrations warning: {e}'))
        call_command('migrate', '--run-syncdb', verbosity=1)
        self.stdout.write(self.style.SUCCESS('    ✔ Migrations complete'))

        # ── 2. Collect static files ───────────────────────────────────────────
        self.stdout.write(self.style.MIGRATE_HEADING('\n[2/4] Collecting static files...'))
        try:
            call_command('collectstatic', '--noinput', verbosity=0)
            self.stdout.write(self.style.SUCCESS('    ✔ Static files collected'))
        except Exception as exc:
            self.stdout.write(self.style.WARNING(f'    ⚠ collectstatic warning: {exc}'))

        # ── 3. Ensure a local (pending) license record exists ────────────────
        self.stdout.write(self.style.MIGRATE_HEADING('\n[3/4] Checking license record...'))
        try:
            from control.models import PanelLicense
            existing = PanelLicense.objects.first()
            if existing and not force:
                self.stdout.write(
                    self.style.SUCCESS(f'    ✔ License already exists — status: {existing.status}')
                )
            else:
                # Create a placeholder record with status='pending_activation'
                # This is enough to prevent the 404 loop but still shows /activate/.
                # The middleware checks status == 'active', so the wizard will still appear.
                if existing:
                    existing.delete()

                hostname = socket.getfqdn()
                PanelLicense.objects.create(
                    key='PENDING-' + secrets.token_hex(16),
                    email='',
                    status='pending_activation',
                    hostname=hostname,
                )
                self.stdout.write(self.style.SUCCESS('    ✔ Placeholder license record created'))
        except Exception as exc:
            self.stdout.write(self.style.WARNING(f'    ⚠ Could not create license record: {exc}'))

        # ── 4. Seed default hosting packages ─────────────────────────────────
        self.stdout.write(self.style.MIGRATE_HEADING('\n[4/5] Seeding hosting packages...'))
        try:
            from control.models import package
            packages = [
                # Shared Hosting
                ('Starter', '10', '5', '5', '100', '5', '3', True, 'starter', False, '', False, ''),
                ('Pro', '30', '20', '20', '300', '20', '10', True, 'growth', True, 'lite', True, 'starter'),
                ('Business', '100', '100', '100', '1000', '100', '50', True, 'agency', True, 'standard', True, 'pro'),
                # WordPress Hosting
                ('WordPress Starter', '15', '5', '5', '150', '5', '3', True, 'starter', False, '', False, ''),
                ('WordPress Pro', '50', '20', '20', '500', '20', '10', True, 'growth', True, 'lite', True, 'starter'),
                ('WordPress Enterprise', '150', '50', '50', '1500', '50', '30', True, 'agency', True, 'standard', True, 'pro'),
                # Reseller Hosting
                ('Reseller Starter', '50', '100', '100', '500', '100', '50', True, 'growth', True, 'lite', True, 'starter'),
                ('Reseller Pro', '150', '9999', '9999', '1500', '9999', '9999', True, 'agency', True, 'standard', True, 'pro'),
                ('Reseller Enterprise', '500', '9999', '9999', '5000', '9999', '9999', True, 'agency', True, 'advanced', True, 'pro'),
            ]
            for p_info in packages:
                name, storage, ftp, subdomain, bandwidth, emails, dbs, inc_soc, soc_pl, inc_seo, seo_pl, inc_mkt, mkt_pl = p_info
                pkg, created = package.objects.get_or_create(
                    name=name,
                    defaults={
                        'storage': storage,
                        'ftp': ftp,
                        'subdomain': subdomain,
                        'bandwidth': bandwidth,
                        'email_accounts': emails,
                        'databases_allowed': dbs,
                        'includes_social': inc_soc,
                        'social_plan': soc_pl,
                        'includes_seo': inc_seo,
                        'seo_plan': seo_pl,
                        'includes_marketing': inc_mkt,
                        'marketing_plan': mkt_pl,
                    }
                )
                if created:
                    self.stdout.write(f"    ✔ Created package '{name}'")
            self.stdout.write(self.style.SUCCESS('    ✔ Hosting packages seeded'))
        except Exception as exc:
            self.stdout.write(self.style.WARNING(f'    ⚠ Could not seed hosting packages: {exc}'))

        # ── 5. Print activation URL ──────────────────────────────────────────
        self.stdout.write(self.style.MIGRATE_HEADING('\n[5/5] Setup complete!\n'))
        try:
            ip = socket.gethostbyname(socket.gethostname())
        except Exception:
            ip = '127.0.0.1'
        self.stdout.write(self.style.SUCCESS(
            f'  ✅ VoidPanel is ready. Open your browser and activate:\n'
            f'     http://{ip}:8080/activate/\n'
        ))
