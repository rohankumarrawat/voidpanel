import paramiko

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)

# Fix the domain mismatch: update rkrawat1907 -> ranjaka.com
# Also check what the suite subscription says for this user
script = """
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'panel.settings')
django.setup()

from control.models import SocialAccount, SuiteSubscription

# First check what domain is expected
sub = SuiteSubscription.objects.filter(email='rkrawat1907@gmail.com', suite='social').first()
expected_domain = ''
if sub:
    expected_domain = sub.hosting_domain or sub.email.split('@')[0]
    print('Suite subscription hosting_domain: %s' % sub.hosting_domain)
    print('Expected domain_key: %s' % expected_domain)

# Find the mismatched account
acc = SocialAccount.objects.filter(domain='rkrawat1907', platform='fb').first()
if acc:
    print('Found mismatched account: id=%s domain=%s name=%s' % (acc.id, acc.domain, acc.account_name))
    if expected_domain:
        acc.domain = expected_domain
        acc.save()
        print('FIXED: Updated domain to: %s' % expected_domain)
    else:
        print('No expected domain found, skipping fix')
else:
    print('No mismatched account found')

# Verify
print('')
print('=== All SocialAccounts after fix ===')
for a in SocialAccount.objects.all():
    print('  id=%s domain=%s platform=%s name=%s active=%s' % (a.id, a.domain, a.platform, a.account_name, a.is_active))
"""

stdin, stdout, stderr = ssh.exec_command('cd /var/www/panel && /var/www/panel/venv/bin/python3 -c "%s"' % script.replace('"', '\\"'))
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print("STDERR:", err[:500])

ssh.close()
