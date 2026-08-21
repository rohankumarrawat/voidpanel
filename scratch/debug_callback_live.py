import paramiko

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)

script = """
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'panel.settings')
django.setup()

from control.models import SocialAccount
accounts = SocialAccount.objects.all()
print('Total SocialAccount:', accounts.count())
for a in accounts:
    print(f'  ID: {a.id}, Domain: {a.domain}, Username: {a.username}, Plat: {a.platform}, AccName: {a.account_name}, Active: {a.is_active}')

from control.models import PanelLicense
lic = PanelLicense.objects.first()
print('Panel License Key:', lic.key if lic else 'NONE')
"""

stdin, stdout, stderr = ssh.exec_command(f"cd /var/www/panel && /var/www/panel/venv/bin/python3 -c \"{script}\"")
print("PANEL DB OUTPUT:\n", stdout.read().decode())
print(stderr.read().decode())

# Check voidonyx DB for OAuthRelayState
voidonyx_script = """
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'voidpanel.settings')
django.setup()

from data.models import OAuthRelayState
relays = OAuthRelayState.objects.all()
print('Total OAuthRelayState in voidonyx:', relays.count())
for r in relays:
    print(f'  Relay: {r.relay_code}, Lic: {r.license_key}, TokenData: {r.token_data}, Created: {r.created_at}')
"""

stdin, stdout, stderr = ssh.exec_command(f"cd /home/voidonyx/voidonyx && /home/voidonyx/voidonyx/venv/bin/python3 -c \"{voidonyx_script}\"")
print("VOIDONYX RELAY OUTPUT:\n", stdout.read().decode())
print(stderr.read().decode())

# Check recent nginx access logs for /social/ or /control/social/
stdin, stdout, stderr = ssh.exec_command("tail -n 35 /var/log/nginx/access.log | grep -E 'social|oauth'")
print("NGINX LOGS:\n", stdout.read().decode())

ssh.close()
