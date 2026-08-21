import paramiko, io

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

SCRIPT = '''
import os, sys, django
sys.path.insert(0, '/var/www/panel')
os.environ['DJANGO_SETTINGS_MODULE'] = 'panel.settings'
django.setup()

# Check X Developer App settings by looking at what's in the redirect_uri field
from control.models import DomainSocialAPIConfig
d = DomainSocialAPIConfig.objects.filter(domain='rkrawat1907').first()
if d:
    print("redirect_uri field:", repr(d.redirect_uri))

# Now check the actual URL the browser would be redirected to
# by simulating a real request with a proper Host header
from django.test import RequestFactory
from django.contrib.auth import get_user_model
User = get_user_model()
u = User.objects.filter(is_superuser=True).first()

rf = RequestFactory()

# Simulate with Host: fast.voidpanel.com:8082 (as the browser sends)
req = rf.get('/control/social/rkrawat1907/connect/twitter/', 
             HTTP_HOST='fast.voidpanel.com:8082', 
             HTTP_X_FORWARDED_PROTO='https')
req.user = u
from django.contrib.sessions.backends.db import SessionStore
req.session = SessionStore()

from control.views import social_connect
resp = social_connect(req, 'rkrawat1907', 'twitter')
print()
print("=== Redirect URL from social_connect ===")
print("URL:", resp.url)
print()

# Parse the URL and extract redirect_uri param
import urllib.parse
parsed = urllib.parse.urlparse(resp.url)
params = urllib.parse.parse_qs(parsed.query)
print("=== Parsed OAuth params ===")
for k, v in params.items():
    print(f"  {k}: {v[0]}")
print()

# Check if redirect_uri matches what X expects
redirect_uri = params.get('redirect_uri', [''])[0]
print("=== Redirect URI analysis ===")
print("  redirect_uri:", redirect_uri)
print("  Has port:", ':808' in redirect_uri)
print("  Is https:", redirect_uri.startswith('https://'))

# Also check the scopes
scope = params.get('scope', [''])[0]
print()
print("=== Scope check ===")
print("  scope:", repr(scope))
print("  Contains tweet.write:", 'tweet.write' in scope)
print("  Note: tweet.write requires elevated access or Pro plan on X!")
'''

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)

sftp = ssh.open_sftp()
with sftp.open('/var/www/panel/diag_tw3.py', 'w') as f:
    f.write(SCRIPT)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('cd /var/www/panel && /var/www/panel/venv/bin/python3 /var/www/panel/diag_tw3.py 2>&1', timeout=30)
print(stdout.read().decode())

ssh.exec_command('rm /var/www/panel/diag_tw3.py')
ssh.close()
