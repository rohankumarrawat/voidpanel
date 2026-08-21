import paramiko

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)

# 1. Check ALL recent voidpanel logs (prints go to gunicorn stderr)
print('=== VOIDPANEL FULL LOGS (last 5 min) ===')
stdin, stdout, stderr = ssh.exec_command('journalctl -u voidpanel.service --since "10 minutes ago" --no-pager | tail -60')
print(stdout.read().decode())

# 2. Check ALL recent relay logs
print('=== RELAY FULL LOGS (last 5 min) ===')
stdin, stdout, stderr = ssh.exec_command('journalctl -u app-voidonyx-voidonyx.service --since "10 minutes ago" --no-pager | tail -60')
print(stdout.read().decode())

# 3. Check gunicorn error log if exists
print('=== GUNICORN LOG ===')
stdin, stdout, stderr = ssh.exec_command('tail -40 /var/log/gunicorn/error.log 2>/dev/null || echo "no gunicorn log"')
print(stdout.read().decode())

# 4. Check DB - when were accounts last updated?
script = """import os, django
os.environ['DJANGO_SETTINGS_MODULE'] = 'panel.settings'
django.setup()
from control.models import SocialAccount
for a in SocialAccount.objects.filter(platform='fb').order_by('-id'):
    print('ID=' + str(a.id) + ' name=' + str(a.account_name) + ' page_id=' + str(a.page_id) + ' updated=' + str(a.updated_at if hasattr(a, 'updated_at') else 'N/A') + ' created=' + str(a.created_at if hasattr(a, 'created_at') else 'N/A'))
"""
stdin, stdout, stderr = ssh.exec_command('cd /var/www/panel && /var/www/panel/venv/bin/python3 -c "' + script + '"')
print('=== DB ACCOUNTS ===')
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print('STDERR:', err)

ssh.close()
