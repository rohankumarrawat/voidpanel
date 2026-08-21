import paramiko

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)

render_script = """
import os, django, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'panel.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth.models import User
from django.contrib.sessions.middleware import SessionMiddleware
from control.views import social_portal_home

factory = RequestFactory()
request = factory.get('/control/social-portal/fast.voidpanel.com/')
middleware = SessionMiddleware(lambda r: None)
middleware.process_request(request)
request.session.save()

u = User.objects.filter(is_superuser=True).first() or User.objects.first()
request.user = u

res = social_portal_home(request, 'fast.voidpanel.com')
print('Status code:', res.status_code)
content = res.content.decode()

for line in content.splitlines():
    if any(k in line for k in ['ENABLED_PLATFORMS', 'ADMIN_1CLICK_PLATFORMS', 'AUTH_MODES', 'API_CONFIG']):
        print('LINE:', line.strip())
"""

stdin, stdout, stderr = ssh.exec_command(f"cd /var/www/panel && /var/www/panel/venv/bin/python3 -c \"{render_script}\"")
print("STDOUT:\n", stdout.read().decode())
print("STDERR:\n", stderr.read().decode())

ssh.close()
