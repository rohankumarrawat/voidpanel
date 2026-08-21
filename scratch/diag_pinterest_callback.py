import paramiko

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

SCRIPT = '''
import os, sys, django
sys.path.insert(0, '/var/www/panel')
os.environ['DJANGO_SETTINGS_MODULE'] = 'panel.settings'
django.setup()

from control.models import SocialAccount
accounts = SocialAccount.objects.all().order_by('-created_at')[:10]
print("=== Last 10 SocialAccount records ===")
for acc in accounts:
    print(f"ID={acc.id} plat={acc.platform} name={acc.account_name} domain={acc.domain} user={acc.user} active={acc.is_active} created={acc.created_at}")
'''

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)

sftp = ssh.open_sftp()
with sftp.open('/var/www/panel/diag_pi.py', 'w') as f:
    f.write(SCRIPT)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('/var/www/panel/venv/bin/python3 /var/www/panel/diag_pi.py 2>&1')
print("=== Social Accounts ===")
print(stdout.read().decode())

stdin, stdout, stderr = ssh.exec_command('tail -n 40 /var/log/nginx/access.log 2>&1 | grep -i "pinterest\\|callback"')
print("=== Nginx callback access log ===")
print(stdout.read().decode())

stdin, stdout, stderr = ssh.exec_command('tail -n 40 /var/log/nginx/error.log 2>&1')
print("=== Nginx error log ===")
print(stdout.read().decode())

ssh.exec_command('rm /var/www/panel/diag_pi.py')
ssh.close()
