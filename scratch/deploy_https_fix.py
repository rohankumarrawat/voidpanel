import paramiko, os

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)
sftp = ssh.open_sftp()

# 1. Upload control/views.py to panel
local_views = '/Users/rohan/Desktop/voidpanel/control/views.py'
remote_views = '/var/www/panel/control/views.py'
print(f'Uploading control/views.py ({os.path.getsize(local_views)} bytes)...')
sftp.put(local_views, remote_views)
print('  -> Uploaded control/views.py')

# 2. Upload relay views.py
local_relay = '/Users/rohan/Desktop/voidpanel/website/voidpanel/voidpanel/views.py'
remote_relay = '/home/voidonyx/voidonyx/voidpanel/views.py'
print(f'Uploading relay views.py ({os.path.getsize(local_relay)} bytes)...')
sftp.put(local_relay, remote_relay)
print('  -> Uploaded relay views.py')

sftp.close()

# 3. Restart services
stdin, stdout, stderr = ssh.exec_command('systemctl restart voidpanel.service app-voidonyx-voidonyx.service')
stdout.read()

stdin, stdout, stderr = ssh.exec_command('systemctl is-active voidpanel.service app-voidonyx-voidonyx.service')
print('Services status:\n', stdout.read().decode())

# 4. Test simulate connect URL again to verify HTTPS
script = """
import os, django
os.environ['DJANGO_SETTINGS_MODULE'] = 'panel.settings'
django.setup()

from django.test import RequestFactory
from control.views import social_connect

rf = RequestFactory()
req = rf.get('/control/social/ranjaka.com/connect/fb/?src=suite', HTTP_HOST='fast.voidpanel.com:8082')
req.session = {'suite_user': {'username': 'rkrawat1907', 'hosting_domain': 'ranjaka.com'}}
req.user = type('User', (), {'is_authenticated': False, 'username': 'anonymous'})()

resp = social_connect(req, 'ranjaka.com', 'fb')
print('Simulated OAuth Target URL:')
print(resp.url)
"""

stdin, stdout, stderr = ssh.exec_command(f'cd /var/www/panel && /var/www/panel/venv/bin/python3 -c "{script}"')
print('\n--- Verification ---')
print(stdout.read().decode())

ssh.close()
