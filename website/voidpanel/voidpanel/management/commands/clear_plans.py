"""
Management command: clear_plans
Usage:
    python manage.py clear_plans            # dry-run, shows counts
    python manage.py clear_plans --confirm  # actually deletes
    python manage.py clear_plans --confirm --keep-licenses  # keep license records
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Remove all hosting, reseller, SSL, WordPress and license plan records from the database.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Actually delete the records (omit for dry-run)',
        )
        parser.add_argument(
            '--keep-licenses',
            action='store_true',
            help='Skip deleting PanelLicenseRecord rows',
        )

    def handle(self, *args, **options):
        confirm = options['confirm']
        keep_lic = options['keep_licenses']

        self.stdout.write(self.style.WARNING(
            '\n🗑  VoidPanel — Clear Plans' + (' (DRY RUN)' if not confirm else '')
        ))
        self.stdout.write('─' * 52)

        targets = []
        if not keep_lic:
            targets.append(
                ('PanelLicenseRecord', 'Panel License Records', 'data.models', 'PanelLicenseRecord')
            )

        total_deleted = 0

        for _label, friendly, module_path, class_name in targets:
            try:
                import importlib
                mod = importlib.import_module(module_path)
                Model = getattr(mod, class_name)
                count = Model.objects.count()

                if count == 0:
                    self.stdout.write(f'  ✅ {friendly}: already empty')
                    continue

                if confirm:
                    Model.objects.all().delete()
                    self.stdout.write(self.style.SUCCESS(
                        f'  🗑  {friendly}: deleted {count} record(s)'
                    ))
                    total_deleted += count
                else:
                    self.stdout.write(self.style.WARNING(
                        f'  ⚠  {friendly}: {count} record(s) WOULD be deleted'
                    ))
                    total_deleted += count

            except Exception as exc:
                self.stdout.write(self.style.ERROR(
                    f'  ❌ {friendly}: error — {exc}'
                ))

        self.stdout.write('─' * 52)
        if confirm:
            self.stdout.write(self.style.SUCCESS(
                f'\n✅ Done. {total_deleted} total record(s) removed.\n'
                'You can now add fresh plans via Super Admin.\n'
            ))
        else:
            self.stdout.write(self.style.WARNING(
                f'\n📋 Dry run complete. {total_deleted} record(s) would be deleted.'
                '\nRe-run with --confirm to actually delete.\n'
            ))
