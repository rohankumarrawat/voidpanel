"""
Management command: fix_wp_token_scopes
Run on the CLIENT VOIDPANEL server to add WordPress scopes to existing API tokens.

Usage:
    python manage.py fix_wp_token_scopes
    python manage.py fix_wp_token_scopes --token-key abc123...  # specific token only
    python manage.py fix_wp_token_scopes --list                 # just list tokens
"""
from django.core.management.base import BaseCommand
from control.models import APIToken, ALL_SCOPES

WP_SCOPES = [
    'wordpress.status',
    'wordpress.install',
    'wordpress.uninstall',
    'wordpress.reset_password',
    'ssl.issue',
    'ssl.list',
]


class Command(BaseCommand):
    help = 'Add WordPress scopes to API tokens to fix "Token missing required scope: wordpress.install" error'

    def add_arguments(self, parser):
        parser.add_argument('--token-key', type=str, help='Only update token with this key')
        parser.add_argument('--list',      action='store_true', help='List all tokens and their scopes')

    def handle(self, *args, **options):
        if options['list']:
            tokens = APIToken.objects.all()
            if not tokens.exists():
                self.stdout.write(self.style.WARNING('No API tokens found.'))
                return
            self.stdout.write(f'\n{"Label":<30} {"Type":<12} {"Active":<8} {"Scopes"}')
            self.stdout.write('-' * 80)
            for t in tokens:
                self.stdout.write(
                    f'{t.label[:28]:<30} {t.owner_type:<12} {"Yes" if t.is_active else "No":<8} '
                    f'{", ".join(t.scopes or [])}'
                )
            return

        key_filter = options.get('token_key')
        qs = APIToken.objects.filter(is_active=True)
        if key_filter:
            qs = qs.filter(key=key_filter)
            if not qs.exists():
                self.stdout.write(self.style.ERROR(f'No active token found with key: {key_filter}'))
                return

        if not qs.exists():
            self.stdout.write(self.style.WARNING('No active API tokens found.'))
            self.stdout.write('Create one at: VoidPanel → Settings → API Tokens → Create Token')
            return

        valid_scopes = set(ALL_SCOPES)
        updated = 0

        for token in qs:
            current = set(token.scopes or [])
            missing = [s for s in WP_SCOPES if s in valid_scopes and s not in current]

            if not missing:
                self.stdout.write(self.style.SUCCESS(
                    f'✓ [{token.label}] already has all WordPress scopes'
                ))
                continue

            new_scopes = sorted(current | set(missing))
            token.scopes = new_scopes
            token.save(update_fields=['scopes'])
            updated += 1

            self.stdout.write(self.style.SUCCESS(
                f'✓ [{token.label}] Added: {", ".join(missing)}'
            ))

        self.stdout.write('')
        if updated:
            self.stdout.write(self.style.SUCCESS(
                f'Done! Updated {updated} token(s). '
                f'WordPress management from voidpanel.com portal should now work.'
            ))
        else:
            self.stdout.write(self.style.SUCCESS('All tokens already have WordPress scopes.'))
