import os
import sys
import tempfile
import requests
import subprocess
from django.core.management.base import BaseCommand
from django.utils import timezone
from control.models import UpdateSettings
from voidplatform.config import paths

class Command(BaseCommand):
    help = 'Checks and applies VoidPanel updates automatically if Auto Update is enabled.'

    def handle(self, *args, **options):
        settings_obj = UpdateSettings.get()
        if settings_obj.mode != UpdateSettings.MODE_AUTO:
            self.stdout.write(self.style.WARNING("Auto Update is disabled (Manual mode active). Exiting."))
            return

        self.stdout.write("Auto Update checking for new version...")

        # 1. Read current version
        current_version = '1.0'
        for path_try in [paths.VERSION_FILE,
                         os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'version.txt')]:
            try:
                with open(path_try, 'r') as f:
                    v = f.read().strip()
                    if v:
                        current_version = v
                        break
            except Exception:
                pass

        # 2. Fetch migration path
        migration_steps = []
        try:
            resp = requests.get(
                f'https://voidpanel.com/version_migration_path/?from={current_version}',
                timeout=15
            )
            if resp.status_code == 200:
                data = resp.json()
                migration_steps = data.get('steps', [])
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error checking updates: {e}"))
            return

        if not migration_steps:
            self.stdout.write(self.style.SUCCESS("System is already up to date."))
            return

        self.stdout.write(self.style.MIGRATE_HEADING(f"Found {len(migration_steps)} migration step(s). Applying..."))

        panel_dir = '/var/www/panel'
        
        # Backup
        try:
            tag = timezone.now().strftime('%Y%m%d%H%M%S')
            subprocess.run(f'cp -r {panel_dir} /var/backups/voidpanel-{tag} 2>/dev/null || true', shell=True)
        except Exception:
            pass

        for step in migration_steps:
            script_url = step.get('script_url', 'https://voidpanel.com/updatepanel.sh')
            target_ver = step.get('version')
            self.stdout.write(f"Applying update to version {target_ver or 'latest'}...")

            tmp_path = os.path.join(tempfile.gettempdir(), f'voidpanel_auto_update_{target_ver or "latest"}.sh')
            try:
                dl = subprocess.run(['curl', '-fsSL', '-o', tmp_path, script_url], capture_output=True)
                if dl.returncode != 0:
                    self.stdout.write(self.style.ERROR(f"Failed to download update script from {script_url}"))
                    break
                
                # Execute update script
                res = subprocess.run(['sudo', 'bash', tmp_path], capture_output=True, text=True)
                if res.returncode != 0:
                    self.stdout.write(self.style.ERROR(f"Update script failed: {res.stderr}"))
                    break

                # Update version files
                if target_ver:
                    subprocess.run(f'echo "{target_ver}" | sudo tee /etc/version.txt > /dev/null', shell=True)
                    try:
                        with open(os.path.join(panel_dir, 'version.txt'), 'w') as vf:
                            vf.write(target_ver)
                    except Exception:
                        pass
                    try:
                        with open(paths.VERSION_FILE, 'w') as vf:
                            vf.write(target_ver)
                    except Exception:
                        pass

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error applying step: {e}"))
                break

        # Save last check/update time
        settings_obj.last_auto_update = timezone.now()
        settings_obj.save()
        self.stdout.write(self.style.SUCCESS("Auto Update process complete."))
