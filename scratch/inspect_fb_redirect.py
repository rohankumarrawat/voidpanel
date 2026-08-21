import paramiko, urllib.parse

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)

# Inspect exact redirect_uri sent to facebook
script = """
import os, django, urllib.parse
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'panel.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from control.views import social_connect

factory = RequestFactory()
request = factory.get('/control/social/rkrawat1907/connect/facebook/?src=suite')
middleware = SessionMiddleware(lambda r: None)
middleware.process_request(request)
request.session['suite_user'] = {'username': 'rkrawat1907', 'email': 'rkrawat1907@khatabook.com'}
request.session.save()

resp = social_connect(request, 'rkrawat1907', 'facebook')
step1_url = resp.get('Location', '')
print('Step 1 URL:', step1_url)

# Parse parameters in step 1 url
parsed = urllib.parse.urlparse(step1_url)
qs = urllib.parse.parse_qs(parsed.query)
callback_uri = qs.get('callback_uri', [''])[0]
print('Step 1 callback_uri parameter:', callback_uri)
"""

stdin, stdout, stderr = ssh.exec_command(f"cd /var/www/panel && /var/www/panel/venv/bin/python3 -c \"{script}\"")
print("STDOUT:\n", stdout.read().decode())
print("STDERR:\n", stderr.read().decode())

ssh.close()
