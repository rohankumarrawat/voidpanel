import paramiko

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)

cmd = '''/var/www/panel/venv/bin/python3 -c "
import sys, os
sys.path.insert(0, '/var/www/panel')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'panel.settings')
import django; django.setup()
from control.models import SocialAccount
for a in SocialAccount.objects.filter(domain='rkrawat1907'):
    print(f'PLATFORM: {a.platform} | ID: {a.account_id} | NAME: {a.account_name} | USERNAME: {a.account_username} | PIC: {a.profile_picture_url} | PAGE_ID: {a.page_id} | PAGE_NAME: {a.page_name} | FOLLOWERS: {a.followers_count} | TOKEN: {a.access_token[:20]}...')
"'''

stdin, stdout, stderr = ssh.exec_command(cmd)
print("STDOUT:")
print(stdout.read().decode())
print("STDERR:")
print(stderr.read().decode())
ssh.close()
