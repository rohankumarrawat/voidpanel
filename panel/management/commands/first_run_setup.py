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

        # ── 4. Print activation URL ──────────────────────────────────────────
        self.stdout.write(self.style.MIGRATE_HEADING('\n[4/4] Setup complete!\n'))
        try:
            ip = socket.gethostbyname(socket.gethostname())
        except Exception:
            ip = '127.0.0.1'
        self.stdout.write(self.style.SUCCESS(
            f'  ✅ VoidPanel is ready. Open your browser and activate:\n'
            f'     http://{ip}:8080/activate/\n'
        ))
