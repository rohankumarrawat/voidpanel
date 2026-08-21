import paramiko

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)

script = r'''
import sys, os
sys.path.insert(0, '/var/www/panel')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "panel.settings")
import django
django.setup()
from control.models import SocialAccount

VOIDONYX_PAGE_ID = "1248611408333420"

# Delete ALL non-Voidonyx FB accounts
deleted = SocialAccount.objects.filter(platform="fb").exclude(page_id=VOIDONYX_PAGE_ID)
print("Deleting %d non-Voidonyx accounts:" % deleted.count())
for a in deleted:
    print("  Deleting id=%s name=%s page_id=%s" % (a.id, a.account_name, a.page_id))
deleted.delete()

# Verify only Voidonyx remains
remaining = SocialAccount.objects.filter(platform="fb")
print("\nRemaining FB accounts:")
for a in remaining:
    print("  id=%s name=%s page_id=%s token=%s..." % (a.id, a.account_name, a.page_id, a.access_token[:30] if a.access_token else "NONE"))
'''

sftp = ssh.open_sftp()
with sftp.file('/tmp/cleanup_db.py', 'w') as f:
    f.write(script)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('cd /var/www/panel && /var/www/panel/venv/bin/python3 /tmp/cleanup_db.py')
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print('STDERR:', err[:300])
ssh.close()
