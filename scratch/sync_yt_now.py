import paramiko

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)

cmd = '''/var/www/panel/venv/bin/python3 -c "
import sys, os, requests
sys.path.insert(0, '/var/www/panel')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'panel.settings')
import django; django.setup()
from control.models import SocialAccount

yt = SocialAccount.objects.filter(domain='rkrawat1907', platform='yt').first()
if yt:
    headers = {'Authorization': f'Bearer {yt.access_token}'}
    r = requests.get('https://www.googleapis.com/youtube/v3/channels?part=snippet,statistics&mine=true', headers=headers)
    if r.status_code == 200:
        items = r.json().get('items', [])
        if items:
            ch = items[0]
            snip = ch.get('snippet', {})
            stats = ch.get('statistics', {})
            yt.account_id = ch.get('id', yt.account_id)
            yt.account_name = snip.get('title', yt.account_name)
            yt.account_username = snip.get('customUrl', '')
            yt.profile_picture_url = snip.get('thumbnails', {}).get('high', {}).get('url') or snip.get('thumbnails', {}).get('default', {}).get('url', '')
            yt.followers_count = int(stats.get('subscriberCount', 0))
            yt.save()
            print('Successfully updated YouTube account in DB:', yt.account_name, yt.account_username, yt.profile_picture_url, yt.followers_count)
"'''

stdin, stdout, stderr = ssh.exec_command(cmd)
print("STDOUT:")
print(stdout.read().decode())
print("STDERR:")
print(stderr.read().decode())
ssh.close()
