import paramiko

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)

cmd = '''/var/www/panel/venv/bin/python3 -c "
import sys, os
sys.path.insert(0, '/var/www/panel')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'panel.settings')
import django; django.setup()
from control.models import SocialAccount

# Deduplicate accounts by (domain, platform, account_id)
seen = set()
for a in SocialAccount.objects.filter(domain='rkrawat1907').order_by('-id'):
    key = (a.platform, a.account_id)
    if key in seen:
        print(f'Deleting duplicate: {a.platform} {a.account_name} ({a.id})')
        a.delete()
    else:
        seen.add(key)

print('Current clean accounts:')
for a in SocialAccount.objects.filter(domain='rkrawat1907'):
    print(f'  [{a.platform.upper()}] {a.account_name} (@{a.account_username}) | ID: {a.account_id} | PIC: {bool(a.profile_picture_url)}')
"'''

stdin, stdout, stderr = ssh.exec_command(cmd)
print("STDOUT:")
print(stdout.read().decode())
print("STDERR:")
print(stderr.read().decode())
ssh.close()
