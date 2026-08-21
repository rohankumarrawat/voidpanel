import paramiko

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)

cmd = '''/var/www/panel/venv/bin/python3 -c "
import sys, os, requests, json
sys.path.insert(0, '/var/www/panel')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'panel.settings')
import django; django.setup()
from control.models import SocialAccount

gb = SocialAccount.objects.filter(domain='rkrawat1907', platform='gb').first()
if gb:
    headers = {'Authorization': f'Bearer {gb.access_token}'}
    
    endpoints = [
        ('mybusinessaccountmanagement v1', 'https://mybusinessaccountmanagement.googleapis.com/v1/accounts'),
        ('mybusiness v4 accounts', 'https://mybusiness.googleapis.com/v4/accounts'),
        ('mybusinessbusinessinformation v1 accounts', 'https://mybusinessbusinessinformation.googleapis.com/v1/accounts'),
        ('mybusinessplaceactions v1', 'https://mybusinessplaceactions.googleapis.com/v1/locations'),
        ('mybusinessverifications v1', 'https://mybusinessverifications.googleapis.com/v1/locations'),
    ]
    for name, url in endpoints:
        try:
            r = requests.get(url, headers=headers, timeout=10)
            print(f'[{name}] {r.status_code} => {r.text[:400]}')
        except Exception as e:
            print(f'[{name}] ERROR: {e}')
"'''

stdin, stdout, stderr = ssh.exec_command(cmd)
print("STDOUT:")
print(stdout.read().decode())
print("STDERR:")
print(stderr.read().decode())
ssh.close()
