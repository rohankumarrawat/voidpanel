import paramiko

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)

script = """import os, django, requests, json
os.environ['DJANGO_SETTINGS_MODULE'] = 'panel.settings'
django.setup()
from control.models import SocialAccount
acc = SocialAccount.objects.filter(platform='fb').first()
if acc and acc.access_token:
    print('Testing token...')
    r = requests.get('https://graph.facebook.com/v19.0/me/accounts?fields=id,name,category,tasks&limit=100&access_token=' + acc.access_token)
    print('Status code:', r.status_code)
    print('Response JSON:', json.dumps(r.json(), indent=2))
    perm_r = requests.get('https://graph.facebook.com/v19.0/me/permissions?access_token=' + acc.access_token)
    print('Permissions JSON:', json.dumps(perm_r.json(), indent=2))
else:
    print('No active Facebook account found')
"""

stdin, stdout, stderr = ssh.exec_command(f'cd /var/www/panel && /var/www/panel/venv/bin/python3 -c "{script}"')
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print("STDERR:", err)

ssh.close()
