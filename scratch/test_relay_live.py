import paramiko

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)

test_relay_script = """
import os, django, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'voidpanel.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from voidpanel.views import social_oauth_connect

factory = RequestFactory()
request = factory.get('/social/oauth/connect/fb/?license=b3ff1a9ffdce127d0cf3093f76f31a6201f1adc2030eb54d14ae95c019122225&callback_uri=https://fast.voidpanel.com:8082/control/social/callback/fb/')
middleware = SessionMiddleware(lambda r: None)
middleware.process_request(request)
request.session.save()

resp = social_oauth_connect(request, 'fb')
print('Relay Response Code:', resp.status_code)
print('Relay Redirect Target:', resp.get('Location', ''))
if resp.status_code != 302:
    print('Relay Content:', resp.content.decode())
"""

stdin, stdout, stderr = ssh.exec_command(f"cd /home/voidonyx/voidonyx && /home/voidonyx/voidonyx/venv/bin/python3 -c \"{test_relay_script}\"")
print("STDOUT:\n", stdout.read().decode())
print("STDERR:\n", stderr.read().decode())

ssh.close()
