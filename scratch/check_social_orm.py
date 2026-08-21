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
print('Total SocialAccount in /var/www/panel DB:', accounts.count())
for a in accounts:
    print(f'  ID: {a.id}, Domain: {a.domain}, Username: {a.username}, Plat: {a.platform}, AccName: {a.account_name}, Active: {a.is_active}')
"""

stdin, stdout, stderr = ssh.exec_command(f"cd /var/www/panel && /var/www/panel/venv/bin/python3 -c \"{script}\"")
print(stdout.read().decode())
print(stderr.read().decode())

ssh.close()
