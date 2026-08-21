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

from django.test import RequestFactory
from control.views import social_connect

rf = RequestFactory()
# Simulate request to fast.voidpanel.com:8082
req = rf.get('/control/social/ranjaka.com/connect/fb/?src=suite', HTTP_HOST='fast.voidpanel.com:8082')
req.session = {'suite_user': {'username': 'rkrawat1907', 'hosting_domain': 'ranjaka.com'}}
req.user = type('User', (), {'is_authenticated': False, 'username': 'anonymous'})()

resp = social_connect(req, 'ranjaka.com', 'fb')
print('Response status:', resp.status_code)
print('Redirect target URL:')
print(resp.url)
"""

stdin, stdout, stderr = ssh.exec_command(f'cd /var/www/panel && /var/www/panel/venv/bin/python3 -c "{script}"')
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print("STDERR:", err)

ssh.close()
