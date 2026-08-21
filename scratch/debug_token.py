import paramiko

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)

script = """
import os, django, requests, json
os.environ['DJANGO_SETTINGS_MODULE'] = 'panel.settings'
django.setup()
from control.models import SocialAccount, SocialMediaAPIConfig
cfg = SocialMediaAPIConfig.get()
acc = SocialAccount.objects.filter(platform='fb').first()
if acc:
    app_token = cfg.facebook_app_id + '|' + cfg.facebook_app_secret
    url = 'https://graph.facebook.com/debug_token?input_token=' + acc.access_token + '&access_token=' + app_token
    r = requests.get(url)
    print('Debug token result:')
    print(json.dumps(r.json(), indent=2))
"""

stdin, stdout, stderr = ssh.exec_command(f'cd /var/www/panel && /var/www/panel/venv/bin/python3 -c "{script}"')
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print("STDERR:", err)

ssh.close()
