import paramiko

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)

test_connect_script = """
import os, django, sys
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
print('Response Status Code:', resp.status_code)
print('Redirect URL:', resp.get('Location', ''))
"""

stdin, stdout, stderr = ssh.exec_command(f"cd /var/www/panel && /var/www/panel/venv/bin/python3 -c \"{test_connect_script}\"")
print("STDOUT:\n", stdout.read().decode())
print("STDERR:\n", stderr.read().decode())

ssh.close()
