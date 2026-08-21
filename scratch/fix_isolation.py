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
from control.models import SocialAccount, SuiteSubscription

# FIX 1: Clear hosting_domain on the SuiteSubscription to avoid overlap with panel user ranjaka14ef
# This makes domain_key = email prefix = 'rkrawat1907' (properly isolated)
sub = SuiteSubscription.objects.get(id=8)
print("BEFORE: SuiteSubscription id=%s hosting_domain='%s'" % (sub.id, sub.hosting_domain))
sub.hosting_domain = ''
sub.save()
print("AFTER:  SuiteSubscription id=%s hosting_domain='%s'" % (sub.id, sub.hosting_domain))
print("  => domain_key will now be '%s' (email prefix)" % sub.email.split('@')[0])

# FIX 2: Voidonyx domain is already 'rkrawat1907' - verify
acc = SocialAccount.objects.get(id=15)
print("\nVoidonyx: domain='%s' name=%s page_id=%s" % (acc.domain, acc.account_name, acc.page_id))

# VERIFY: No more overlaps
from control.models import domain as DomainModel
panel_domains = set(DomainModel.objects.values_list('domain', flat=True))
suite_keys = set()
for s in SuiteSubscription.objects.filter(suite="social"):
    key = s.hosting_domain or s.email.split('@')[0]
    suite_keys.add(key)

overlap = panel_domains & suite_keys
if overlap:
    print("\n⚠️  STILL OVERLAP: %s" % overlap)
else:
    print("\n✅ ISOLATION CONFIRMED - no overlap between panel and suite domain keys")

# Show final state
print("\nFinal domain_key for rkrawat1907: '%s'" % (sub.hosting_domain or sub.email.split('@')[0]))
matching = SocialAccount.objects.filter(domain='rkrawat1907')
print("Matching social accounts: %d" % matching.count())
for a in matching:
    print("  -> %s (%s) page_id=%s" % (a.account_name, a.platform, a.page_id))
'''

sftp = ssh.open_sftp()
with sftp.file('/tmp/fix_isolation.py', 'w') as f:
    f.write(script)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('cd /var/www/panel && /var/www/panel/venv/bin/python3 /tmp/fix_isolation.py')
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print('STDERR:', err[:300])
ssh.close()
