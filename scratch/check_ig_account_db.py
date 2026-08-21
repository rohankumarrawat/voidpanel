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
for a in SocialAccount.objects.filter(platform='ig'):
    print(f'ID={a.id} | domain={a.domain} | account_id={a.account_id} | name={a.account_name} | username={a.username} | account_username={a.account_username} | page_id={a.page_id} | page_name={a.page_name} | followers={a.followers_count}')
"""

stdin, stdout, stderr = ssh.exec_command(f'cd /var/www/panel && /var/www/panel/venv/bin/python3 -c "{script}"')
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print("STDERR:", err)

ssh.close()
