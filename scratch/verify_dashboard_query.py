import paramiko

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)

script = """
import os, django, json
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'panel.settings')
django.setup()

from control.models import SocialAccount

# Simulate what _get_social_portal_data_ctx does with domain='ranjaka.com'
domain = 'ranjaka.com'
accounts = list(SocialAccount.objects.filter(domain=domain, is_active=True).values(
    'id', 'platform', 'account_name', 'account_username',
    'followers_count', 'following_count', 'profile_picture_url', 'page_name',
))
print('Domain: %s' % domain)
print('Accounts found: %d' % len(accounts))
for a in accounts:
    print('  platform=%s name=%s username=%s' % (a['platform'], a['account_name'], a['account_username']))

if len(accounts) > 0:
    print('')
    print('SUCCESS: Dashboard will show connected accounts!')
else:
    print('')
    print('PROBLEM: Dashboard will still show empty!')
"""

stdin, stdout, stderr = ssh.exec_command('cd /var/www/panel && /var/www/panel/venv/bin/python3 -c "%s"' % script.replace('"', '\\"'))
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print("STDERR:", err[:300])

ssh.close()
