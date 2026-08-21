import paramiko

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

APP_ID = '27819945947668422'
APP_SECRET = '4f917b362d4357a9be63c0f74f4d95af'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)

# 1. Update / verify on voidonyx (relay / master)
script_master = f"""
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'voidonyx.settings')
django.setup()

from data.models import SocialPlatformSettings
cfg = SocialPlatformSettings.get()
print('=== MASTER (voidonyx) SocialPlatformSettings ===')
print(f'Old Facebook App ID: {{cfg.facebook_app_id}}')
cfg.facebook_app_id = '{APP_ID}'
cfg.facebook_app_secret = '{APP_SECRET}'
cfg.threads_app_id = '{APP_ID}'
cfg.threads_app_secret = '{APP_SECRET}'
cfg.save()
print(f'Updated Facebook App ID: {{cfg.facebook_app_id}}')
print(f'Enabled platforms: {{cfg.enabled_platforms}}')
"""

print("--- Updating Master / Relay (voidonyx) ---")
stdin, stdout, stderr = ssh.exec_command(f'cd /home/voidonyx/voidonyx && /home/voidonyx/voidonyx/venv/bin/python3 -c """{script_master}"""')
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print("Master STDERR:", err)

# 2. Update / verify on panel (/var/www/panel)
script_panel = f"""
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'panel.settings')
django.setup()

from control.models import SocialMediaAPIConfig
cfg = SocialMediaAPIConfig.get()
print('=== PANEL SocialMediaAPIConfig ===')
print(f'Old Panel FB App ID: {{cfg.facebook_app_id}}')
cfg.facebook_app_id = '{APP_ID}'
cfg.facebook_app_secret = '{APP_SECRET}'
cfg.save()
print(f'Updated Panel FB App ID: {{cfg.facebook_app_id}}')
print(f'Enabled platforms: {{cfg.enabled_platforms}}')
print(f'Admin enabled platforms: {{cfg.admin_enabled_platforms}}')
"""

print("--- Updating Panel (/var/www/panel) ---")
stdin, stdout, stderr = ssh.exec_command(f'cd /var/www/panel && /var/www/panel/venv/bin/python3 -c """{script_panel}"""')
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print("Panel STDERR:", err)

# 3. Restart services to ensure cache/process reload
stdin, stdout, stderr = ssh.exec_command('systemctl restart voidpanel.service app-voidonyx-voidonyx.service')
stdout.read()

print("Restarted services. Status check:")
stdin, stdout, stderr = ssh.exec_command('systemctl is-active voidpanel.service app-voidonyx-voidonyx.service')
print(stdout.read().decode())

ssh.close()
