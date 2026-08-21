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
from control.models import SocialAccount, SocialMediaAPIConfig

cfg = SocialMediaAPIConfig.get()
app_token = cfg.facebook_app_id + '|' + cfg.facebook_app_secret

print('=== 1. Checking Voidonyx public page via Graph API ===')
r = requests.get('https://graph.facebook.com/v19.0/voidonyx?fields=id,name,link,category&access_token=' + app_token)
print('Status:', r.status_code, r.text)

print('=== 2. Current SocialAccounts in DB ===')
for a in SocialAccount.objects.all():
    print('ID=' + str(a.id) + ' domain=' + str(a.domain) + ' platform=' + str(a.platform) + ' name=' + str(a.account_name) + ' page_id=' + str(a.page_id))
"""

stdin, stdout, stderr = ssh.exec_command(f'cd /var/www/panel && /var/www/panel/venv/bin/python3 -c "{script}"')
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print("STDERR:", err)

ssh.close()
