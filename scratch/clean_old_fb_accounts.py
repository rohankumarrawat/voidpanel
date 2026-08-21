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
os.environ['DJANGO_SETTINGS_MODULE'] = 'panel.settings'
django.setup()

from control.models import SocialAccount
# Delete the old FB accounts that have empty page_id so user can connect fresh with new Meta App
deleted_count, _ = SocialAccount.objects.filter(platform='fb').delete()
print(f'Deleted {deleted_count} old Facebook accounts.')

print('Remaining accounts:')
for a in SocialAccount.objects.all():
    print(f'  ID={a.id} domain={a.domain} platform={a.platform} name={a.account_name}')
"""

stdin, stdout, stderr = ssh.exec_command(f'cd /var/www/panel && /var/www/panel/venv/bin/python3 -c "{script}"')
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print("STDERR:", err)

ssh.close()
