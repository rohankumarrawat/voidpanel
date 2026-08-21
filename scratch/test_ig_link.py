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

fb = SocialAccount.objects.filter(domain='rkrawat1907', platform='fb').first()
if fb:
    print('=== TESTING META / FACEBOOK TOKEN FOR INSTAGRAM ===')
    print('FB Token:', fb.access_token[:30] + '...')
    print('Page ID:', fb.page_id)
    
    # 1. Check me/accounts
    r1 = requests.get(f'https://graph.facebook.com/v19.0/me/accounts?fields=id,name,access_token,instagram_business_account{{id,username,name,profile_picture_url,followers_count}}&access_token={fb.access_token}')
    print('me/accounts:', r1.status_code, r1.text[:600])
    
    # 2. Check specific page directly
    page_id = fb.page_id or '1248611408333420'
    r2 = requests.get(f'https://graph.facebook.com/v19.0/{page_id}?fields=id,name,instagram_business_account{{id,username,name,profile_picture_url,followers_count}}&access_token={fb.access_token}')
    print(f'page/{page_id}:', r2.status_code, r2.text[:600])
    
    # 3. Check page with page access token if available
    if r1.status_code == 200:
        data = r1.json().get('data', [])
        for p in data:
            p_tok = p.get('access_token')
            p_id = p.get('id')
            p_name = p.get('name')
            print(f'Checking Page: {p_name} ({p_id})')
            r3 = requests.get(f'https://graph.facebook.com/v19.0/{p_id}?fields=id,name,instagram_business_account{{id,username,name,profile_picture_url,followers_count}}&access_token={p_tok}')
            print('  ->', r3.status_code, r3.text[:600])
"'''

stdin, stdout, stderr = ssh.exec_command(cmd)
print("STDOUT:")
print(stdout.read().decode())
print("STDERR:")
print(stderr.read().decode())
ssh.close()
