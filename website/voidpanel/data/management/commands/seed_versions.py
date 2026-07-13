"""
Management command: seed_versions
Usage:
    python manage.py seed_versions

Populates the `updates` table with all known VoidPanel releases.
Run this once on the voidpanel.com server after deployment.
To add a new release, append an entry to VERSIONS below, then re-run.
"""
from django.core.management.base import BaseCommand
from data.models import updates

BASE_URL = 'https://voidpanel.com/static/updates'

# ── Add each release here ────────────────────────────────────────────────────
# Fields: version, notes, script_url, min_version, is_breaking
VERSIONS = [
    {
        'version':    '2.0.0',
        'notes':      'Major rewrite: new reseller dashboard, auto-login, Quick Access shortcut cards, improved DNS manager.',
        'script_url': f'{BASE_URL}/2.0.0/update.sh',
        'min_version': '',
        'is_breaking': True,   # Breaking — servers must not skip from 1.x directly to 2.1.0
    },
    {
        'version':    '2.1.0',
        'notes':      'Step-by-step update system, migration path API, Update Manager in Super Admin, checkversion endpoint, version.txt fallback.',
        'script_url': f'{BASE_URL}/2.1.0/update.sh',
        'min_version': '2.0.0',   # Must be on 2.0.0 first
        'is_breaking': False,
    },
]
# ─────────────────────────────────────────────────────────────────────────────


class Command(BaseCommand):
    help = 'Seed the updates table with all known VoidPanel release versions.'

    def handle(self, *args, **options):
        created_count = 0
        updated_count = 0

        for entry in VERSIONS:
            obj, created = updates.objects.update_or_create(
                version=entry['version'],
                defaults={
                    'notes':       entry.get('notes', ''),
                    'script_url':  entry.get('script_url', ''),
                    'min_version': entry.get('min_version', ''),
                    'is_breaking': entry.get('is_breaking', False),
                    'is_active':   True,
                }
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'  ✅ Created: v{obj.version}'))
            else:
                updated_count += 1
                self.stdout.write(self.style.WARNING(f'  🔄 Updated: v{obj.version}'))

        self.stdout.write(
            self.style.SUCCESS(
                f'\nDone. {created_count} version(s) created, {updated_count} updated.'
            )
        )
        self.stdout.write(
            '\nTo add a new version:\n'
            '  1. Add an entry to VERSIONS in data/management/commands/seed_versions.py\n'
            '  2. Upload the update script to static/updates/{version}/update.sh\n'
            '  3. Re-run: python manage.py seed_versions\n'
        )
