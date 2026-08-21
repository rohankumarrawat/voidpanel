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

for a in SocialAccount.objects.filter(domain='rkrawat1907'):
    print(f'=== SYNCING {a.platform.upper()}: {a.account_name} ===')
    if a.platform == 'tw':
        try:
            r = requests.get('https://api.twitter.com/2/users/me?user.fields=profile_image_url,public_metrics,username,name', headers={'Authorization': f'Bearer {a.access_token}'}, timeout=10)
            print('  TW Result:', r.status_code, r.text[:300])
            if r.status_code == 200:
                d = r.json().get('data', {})
                pm = d.get('public_metrics', {})
                a.followers_count = pm.get('followers_count', a.followers_count)
                a.following_count = pm.get('following_count', a.following_count)
                a.profile_picture_url = d.get('profile_image_url', a.profile_picture_url)
                a.account_name = d.get('name', a.account_name)
                a.account_username = d.get('username', a.account_username)
                a.save()
                print('  Updated TW:', a.account_name, '@'+a.account_username, 'Followers:', a.followers_count)
        except Exception as e:
            print('  TW Error:', e)

    elif a.platform == 'pi':
        try:
            r = requests.get('https://api.pinterest.com/v5/user_account', headers={'Authorization': f'Bearer {a.access_token}'}, timeout=10)
            print('  PI Result:', r.status_code, r.text[:300])
            if r.status_code == 200:
                d = r.json()
                a.followers_count = d.get('follower_count', a.followers_count)
                a.following_count = d.get('following_count', a.following_count)
                a.profile_picture_url = d.get('profile_image', a.profile_picture_url)
                a.account_name = d.get('business_name') or d.get('username') or a.account_name
                a.account_username = d.get('username', a.account_username)
                a.save()
                print('  Updated PI:', a.account_name, '@'+a.account_username, 'Followers:', a.followers_count)
        except Exception as e:
            print('  PI Error:', e)

    elif a.platform == 'yt':
        try:
            r = requests.get('https://www.googleapis.com/youtube/v3/channels?part=snippet,statistics&mine=true', headers={'Authorization': f'Bearer {a.access_token}'}, timeout=10)
            print('  YT Result:', r.status_code, r.text[:300])
            if r.status_code == 200:
                items = r.json().get('items', [])
                if items:
                    snip = items[0].get('snippet', {})
                    stats = items[0].get('statistics', {})
                    a.account_name = snip.get('title', a.account_name)
                    a.account_username = snip.get('customUrl', a.account_username)
                    a.profile_picture_url = snip.get('thumbnails', {}).get('high', {}).get('url') or a.profile_picture_url
                    a.followers_count = int(stats.get('subscriberCount', a.followers_count))
                    a.save()
                    print('  Updated YT:', a.account_name, a.account_username, 'Subs:', a.followers_count)
        except Exception as e:
            print('  YT Error:', e)

    elif a.platform == 'fb':
        try:
            target_id = a.page_id or 'me'
            r = requests.get(f'https://graph.facebook.com/v19.0/{target_id}?fields=name,username,followers_count,fan_count,picture{{url}}&access_token={a.access_token}', timeout=10)
            print('  FB Result:', r.status_code, r.text[:300])
            if r.status_code == 200:
                d = r.json()
                a.followers_count = d.get('followers_count') or d.get('fan_count') or a.followers_count
                a.account_name = d.get('name', a.account_name)
                pic = d.get('picture', {}).get('data', {}).get('url')
                if pic:
                    a.profile_picture_url = pic
                a.save()
                print('  Updated FB:', a.account_name, 'Followers:', a.followers_count)
        except Exception as e:
            print('  FB Error:', e)
"'''

stdin, stdout, stderr = ssh.exec_command(cmd)
print("STDOUT:")
print(stdout.read().decode())
print("STDERR:")
print(stderr.read().decode())
ssh.close()
