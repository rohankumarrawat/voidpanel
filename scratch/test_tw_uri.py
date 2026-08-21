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
from django.contrib.auth import get_user_model
from control.views import social_connect

User = get_user_model()
u = User.objects.filter(is_superuser=True).first()

rf = RequestFactory()

# Test 1: Host fast.voidpanel.com
req1 = rf.get('/control/social/rkrawat1907/connect/twitter/?src=suite', HTTP_HOST='fast.voidpanel.com', HTTP_X_FORWARDED_PROTO='https')
req1.user = u
req1.session = {}
resp1 = social_connect(req1, 'rkrawat1907', 'twitter')
print('TEST 1 (Host: fast.voidpanel.com):')
print('  Redirect location:', resp1.url)

# Test 2: Host fast.voidpanel.com:8082
req2 = rf.get('/control/social/rkrawat1907/connect/twitter/?src=suite', HTTP_HOST='fast.voidpanel.com:8082', HTTP_X_FORWARDED_PROTO='https')
req2.user = u
req2.session = {}
resp2 = social_connect(req2, 'rkrawat1907', 'twitter')
print()
print('TEST 2 (Host: fast.voidpanel.com:8082):')
print('  Redirect location:', resp2.url)
"""

cmd = f'cd /var/www/panel && /var/www/panel/venv/bin/python3 -c "{script}" 2>&1'
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())

ssh.close()
