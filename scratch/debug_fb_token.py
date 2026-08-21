import paramiko

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)

cmd = '''/var/www/panel/venv/bin/python3 -c "
import sys, os, requests, json
sys.path.insert(0, '/var/www/panel')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'panel.settings')
import django; django.setup()
from control.models import SocialAccount
from control.views import _resolve_platform_credentials

fb = SocialAccount.objects.filter(domain='rkrawat1907', platform='fb').first()
app_id, app_secret = _resolve_platform_credentials('rkrawat1907', 'fb')
print('App ID:', app_id)
if fb and app_id and app_secret:
    r = requests.get(f'https://graph.facebook.com/debug_token?input_token={fb.access_token}&access_token={app_id}|{app_secret}')
    print('Token debug:')
    print(json.dumps(r.json(), indent=2))
"'''

stdin, stdout, stderr = ssh.exec_command(cmd)
print("STDOUT:")
print(stdout.read().decode())
print("STDERR:")
print(stderr.read().decode())
ssh.close()
