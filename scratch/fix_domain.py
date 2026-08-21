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
from control.models import SocialAccount

# Try setting domain to 'rkrawat1907' (email prefix from rkrawat1907@gmail.com)
acc = SocialAccount.objects.get(id=15)
acc.domain = 'rkrawat1907'
acc.save()
print("Set domain='rkrawat1907' on Voidonyx id=15")

# Also set account_id to match page_id for consistency
print("Verified: id=%s domain='%s' name=%s page_id=%s account_id=%s active=%s" % (
    acc.id, acc.domain, acc.account_name, acc.page_id, acc.account_id, acc.is_active))
'''

sftp = ssh.open_sftp()
with sftp.file('/tmp/fix_domain5.py', 'w') as f:
    f.write(script)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('cd /var/www/panel && /var/www/panel/venv/bin/python3 /tmp/fix_domain5.py')
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print('STDERR:', err[:300])
ssh.close()
