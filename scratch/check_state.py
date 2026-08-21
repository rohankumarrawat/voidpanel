import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('207.180.209.216', port=22, username='root', password='19072002ROHANkumar!', timeout=15)

# Check debug log and DB state
stdin, stdout, stderr = ssh.exec_command('tail -60 /tmp/fb_callback_debug.log')
print("=== DEBUG LOG ===")
print(stdout.read().decode())

script = r'''
import sys, os
sys.path.insert(0, '/var/www/panel')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "panel.settings")
import django
django.setup()
from control.models import SocialAccount
print("\n=== CURRENT DB STATE ===")
for a in SocialAccount.objects.filter(platform="fb"):
    print("id=%s domain='%s' name=%s page_id=%s account_id=%s" % (
        a.id, a.domain, a.account_name, a.page_id, a.account_id))
'''

sftp = ssh.open_sftp()
with sftp.file('/tmp/check_state.py', 'w') as f:
    f.write(script)
sftp.close()

stdin2, stdout2, stderr2 = ssh.exec_command('cd /var/www/panel && /var/www/panel/venv/bin/python3 /tmp/check_state.py')
print(stdout2.read().decode())
ssh.close()
