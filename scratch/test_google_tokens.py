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

yt = SocialAccount.objects.filter(domain='rkrawat1907', platform='yt').first()
if yt:
    print('=== YOUTUBE TOKEN TEST ===')
    headers = {'Authorization': f'Bearer {yt.access_token}'}
    
    # 1. userinfo
    r = requests.get('https://www.googleapis.com/oauth2/v2/userinfo', headers=headers)
    print('Userinfo:', r.status_code, r.text[:300])
    
    # 2. youtube channels mine=true
    r = requests.get('https://www.googleapis.com/youtube/v3/channels?part=snippet,statistics,brandingSettings,contentDetails&mine=true', headers=headers)
    print('YouTube mine=true:', r.status_code, r.text[:600])

gb = SocialAccount.objects.filter(domain='rkrawat1907', platform='gb').first()
if gb:
    print('=== GBP TOKEN TEST ===')
    headers = {'Authorization': f'Bearer {gb.access_token}'}
    
    # 1. userinfo
    r = requests.get('https://www.googleapis.com/oauth2/v2/userinfo', headers=headers)
    print('Userinfo:', r.status_code, r.text[:300])
    
    # 2. accounts
    r = requests.get('https://mybusinessaccountmanagement.googleapis.com/v1/accounts', headers=headers)
    print('GBP Accounts:', r.status_code, r.text[:600])
    if r.status_code == 200:
        for acc in r.json().get('accounts', []):
            acc_name = acc.get('name')
            print('Checking locations for:', acc_name)
            loc_r = requests.get(f'https://mybusinessbusinessinformation.googleapis.com/v1/{acc_name}/locations?readMask=name,title,storefrontAddress,profile,categories', headers=headers)
            print('  Locations:', loc_r.status_code, loc_r.text[:600])
"'''

stdin, stdout, stderr = ssh.exec_command(cmd)
print("STDOUT:")
print(stdout.read().decode())
print("STDERR:")
print(stderr.read().decode())
ssh.close()
