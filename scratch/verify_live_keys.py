import paramiko

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)

verify_script = """
import sqlite3

# Check Voidonyx DB
conn = sqlite3.connect('/home/voidonyx/voidonyx/db.sqlite3')
cur = conn.cursor()
cur.execute('SELECT facebook_enabled, facebook_app_id, facebook_auth_mode, instagram_enabled, instagram_app_id FROM data_socialplatformsettings')
row = cur.fetchone()
print('Live VoidOnyx Settings in DB:', row)
conn.close()

# Check VoidPanel DB
conn = sqlite3.connect('/home/voidpanelc091/voidpanel/db.sqlite3')
cur = conn.cursor()
cur.execute('SELECT facebook_enabled, facebook_app_id, facebook_auth_mode, instagram_enabled, instagram_app_id FROM data_socialplatformsettings')
row = cur.fetchone()
print('Live VoidPanel Settings in DB:', row)
conn.close()
"""

stdin, stdout, stderr = ssh.exec_command(f"python3 -c \"{verify_script}\"")
print(stdout.read().decode())

# Check API endpoint output
stdin, stdout, stderr = ssh.exec_command("curl -s https://voidonyx.in/api/social/platform-config/ || true")
print("API Response from voidonyx.in:\n", stdout.read().decode())

# Sync control_socialmediaapiconfig in /var/www/panel/
sync_panel_script = """
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'panel.settings')
django.setup()
from control.models import SocialMediaAPIConfig

cfg = SocialMediaAPIConfig.get()
print('Synced Panel Config in /var/www/panel/:')
print('  Enabled platforms:', cfg.enabled_platforms)
print('  Admin 1-Click platforms:', cfg.admin_enabled_platforms)
print('  Auth modes:', cfg.auth_modes)
"""
stdin, stdout, stderr = ssh.exec_command(f"cd /var/www/panel && /var/www/panel/venv/bin/python3 -c \"{sync_panel_script}\"")
print(stdout.read().decode())

ssh.close()
