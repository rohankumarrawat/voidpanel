import paramiko, urllib.parse

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)

script = """
import os, django, urllib.parse
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'voidpanel.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from voidpanel.views import social_oauth_connect

factory = RequestFactory()
request = factory.get('/social/oauth/connect/fb/?license=b3ff1a9ffdce127d0cf3093f76f31a6201f1adc2030eb54d14ae95c019122225&callback_uri=https://fast.voidpanel.com:8082/control/social/callback/facebook/')
middleware = SessionMiddleware(lambda r: None)
middleware.process_request(request)
request.session.save()

resp = social_oauth_connect(request, 'fb')
target_fb_url = resp.get('Location', '')
print('Target Facebook URL:', target_fb_url)

parsed = urllib.parse.urlparse(target_fb_url)
qs = urllib.parse.parse_qs(parsed.query)
fb_redirect_uri = qs.get('redirect_uri', [''])[0]
print('\\nEXACT redirect_uri sent to Facebook:', fb_redirect_uri)
"""

stdin, stdout, stderr = ssh.exec_command(f"cd /home/voidpanelc091/voidpanel && /home/voidpanelc091/voidpanel/venv/bin/python3 -c \"{script}\"")
print("STDOUT:\n", stdout.read().decode())
print("STDERR:\n", stderr.read().decode())

ssh.close()
