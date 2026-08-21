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
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'panel.settings')
django.setup()

from control.models import SuiteSubscription
print('=== Suite Subscriptions ===')
for s in SuiteSubscription.objects.all():
    plan_slug = s.plan.slug if s.plan else 'None'
    print('  email=%s suite=%s plan=%s hosting_domain=%s active=%s' % (s.email, s.suite, plan_slug, s.hosting_domain, s.is_active))

from control import models as m
print('')
print('=== Panel users (first 10) ===')
for u in m.user.objects.all()[:10]:
    print('  username=%s domain=%s email=%s' % (u.username, u.domain, u.email))

from control.models import SocialAccount
print('')
print('=== SocialAccounts ===')
for a in SocialAccount.objects.all():
    print('  id=%s domain=%s platform=%s name=%s active=%s page_id=%s' % (a.id, a.domain, a.platform, a.account_name, a.is_active, a.page_id))

# Simulate what the portal does
print('')
print('=== Simulating suite_social_portal domain resolution ===')
# Check what domain the admin user would get
admin_user = m.user.objects.filter(email='rkrawat1907@gmail.com').first()
if admin_user:
    print('  Admin panel user found: domain=%s' % admin_user.domain)
else:
    print('  No admin panel user with email rkrawat1907@gmail.com')
    for u in m.user.objects.all()[:5]:
        print('  Available: username=%s domain=%s email=%s' % (u.username, u.domain, u.email))

# Check django auth user
from django.contrib.auth.models import User as DjangoUser
for du in DjangoUser.objects.all():
    print('  Django user: username=%s email=%s is_staff=%s is_super=%s' % (du.username, du.email, du.is_staff, du.is_superuser))
"""

stdin, stdout, stderr = ssh.exec_command('cd /var/www/panel && /var/www/panel/venv/bin/python3 -c "%s"' % script.replace('"', '\\"'))
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print("STDERR:", err[:800])

ssh.close()
