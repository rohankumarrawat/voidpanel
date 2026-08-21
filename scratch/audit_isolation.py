import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('207.180.209.216', port=22, username='root', password='19072002ROHANkumar!', timeout=15)

script = r'''
import sys, os
sys.path.insert(0, '/var/www/panel')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "panel.settings")
import django
django.setup()
from control.models import SocialAccount, SuiteSubscription, user as UserModel, domain as DomainModel

print("=" * 60)
print("ISOLATION AUDIT: Panel Users vs Suite Users")
print("=" * 60)

# 1. All Social Accounts with their domain scoping
print("\n1. ALL SOCIAL ACCOUNTS (scoping check):")
for a in SocialAccount.objects.all().order_by("domain"):
    print("   domain='%s' | platform=%s | name=%s | user=%s | page_id=%s" % (
        a.domain, a.platform, a.account_name, a.username, a.page_id))

# 2. Panel users and their domains
print("\n2. PANEL USERS (access via domain):")
for u in UserModel.objects.all():
    print("   username=%s | domain=%s | email=%s" % (u.username, u.domain, u.email))

# 3. Suite users (subscriptions)
print("\n3. SUITE USERS (access via login):")
for s in SuiteSubscription.objects.filter(suite="social"):
    print("   email=%s | hosting_domain='%s' | suite=%s | active=%s" % (
        s.email, s.hosting_domain, s.suite, s.is_active))

# 4. Check for CONFLICTS - domain_key overlap
print("\n4. CONFLICT CHECK:")
panel_domains = set(DomainModel.objects.values_list('domain', flat=True))
suite_domain_keys = set()
for s in SuiteSubscription.objects.filter(suite="social"):
    key = s.hosting_domain or s.email.split('@')[0]
    suite_domain_keys.add(key)
    
overlap = panel_domains & suite_domain_keys
if overlap:
    print("   ⚠️  OVERLAP FOUND: %s" % overlap)
    print("   These domains are used by BOTH panel users AND suite users!")
else:
    print("   ✅ No overlap between panel domains and suite domain keys")

# 5. Show what domain_key each suite social user would get
print("\n5. SUITE SOCIAL DOMAIN_KEY RESOLUTION:")
for s in SuiteSubscription.objects.filter(suite="social"):
    domain_key = s.hosting_domain or s.email.split('@')[0]
    matching_accounts = SocialAccount.objects.filter(domain=domain_key, platform='fb')
    print("   email=%s -> domain_key='%s' -> %d FB account(s)" % (
        s.email, domain_key, matching_accounts.count()))
    for a in matching_accounts:
        print("      -> %s (page_id=%s)" % (a.account_name, a.page_id))

# 6. Check what the session actually produces
# Simulate the suite portal domain_key derivation
print("\n6. SUITE SESSION SIMULATION for rkrawat1907@gmail.com:")
sub = SuiteSubscription.objects.filter(email="rkrawat1907@gmail.com", suite="social", is_active=True).first()
if sub:
    domain_key = sub.hosting_domain or sub.email.split('@')[0]
    print("   SuiteSubscription.hosting_domain = '%s'" % sub.hosting_domain)
    print("   Email prefix = '%s'" % sub.email.split('@')[0])
    print("   => domain_key = '%s'" % domain_key)
    accs = SocialAccount.objects.filter(domain=domain_key)
    print("   => Matching accounts: %d" % accs.count())
    for a in accs:
        print("      %s (%s) page_id=%s" % (a.account_name, a.platform, a.page_id))
else:
    print("   No active social subscription found")
'''

sftp = ssh.open_sftp()
with sftp.file('/tmp/audit_isolation.py', 'w') as f:
    f.write(script)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('cd /var/www/panel && /var/www/panel/venv/bin/python3 /tmp/audit_isolation.py')
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print('STDERR:', err[:300])
ssh.close()
