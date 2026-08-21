import paramiko, time

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
for _ in range(5):
    try:
        ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)
        break
    except:
        time.sleep(2)

sftp = ssh.open_sftp()

script_content = '''
import sys, os, json, requests
sys.path.insert(0, '/var/www/panel')
os.chdir('/var/www/panel')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'panel.settings')
import django
django.setup()

from control.models import SocialAccount, SocialPost

domain = 'rkrawat1907'
print("=== 1. ALL SOCIAL ACCOUNTS ===")
accounts = list(SocialAccount.objects.filter(domain=domain))
for acc in accounts:
    print(f"ID:{acc.id} | Plat:{acc.platform} | Name:{acc.account_name} | User:{acc.account_username} | AccID:{acc.account_id} | PageID:{acc.page_id} | Active:{acc.is_active} | Followers:{acc.followers_count}")

print("\\n=== 2. ALL POSTS IN DB ===")
posts = list(SocialPost.objects.filter(domain=domain).order_by('-created_at'))
print(f"Total posts in DB: {len(posts)}")
for p in posts:
    print(f"  Post #{p.id} [{p.status}] Plats:{[a.platform for a in p.accounts.all()]} | Caption:{repr(p.caption_text[:60])} | PostIDs:{p.platform_post_ids}")

print("\\n=== 3. LIVE INSTAGRAM GRAPH API ===")
ig_acc = SocialAccount.objects.filter(domain=domain, platform='ig', is_active=True).first()
if ig_acc:
    r = requests.get(f"https://graph.facebook.com/v19.0/{ig_acc.account_id}/media?fields=id,caption,permalink,timestamp,like_count,comments_count,comments{{id,text,username,timestamp,from}}&limit=15&access_token={ig_acc.access_token}", timeout=10)
    print("IG Status Code:", r.status_code)
    try:
        res = r.json()
        print("IG Media count:", len(res.get('data', [])))
        for m in res.get('data', []):
            print(f"  Media ID: {m.get('id')} | Likes: {m.get('like_count')} | Comments: {m.get('comments_count')} | Link: {m.get('permalink')}")
            print(f"    Caption: {repr(m.get('caption',''))[:80]}")
            for c in m.get('comments', {}).get('data', []):
                print(f"    -> Comment {c.get('id')}: User:{c.get('username')} From:{c.get('from')} Text:{c.get('text')} Time:{c.get('timestamp')}")
    except Exception as e:
        print("IG Parse Error:", e, r.text[:200])

print("\\n=== 4. LIVE FACEBOOK GRAPH API ===")
fb_acc = SocialAccount.objects.filter(domain=domain, platform='fb', is_active=True).first()
if fb_acc:
    target_id = fb_acc.page_id or 'me'
    r = requests.get(f"https://graph.facebook.com/v19.0/{target_id}?fields=id,name,fan_count,followers_count,feed{{id,message,permalink_url,created_time,likes.summary(true),comments.summary(true){{id,message,from,created_time}}}}&access_token={fb_acc.access_token}", timeout=10)
    print("FB Status Code:", r.status_code)
    try:
        res = r.json()
        print("FB Name:", res.get('name'), "Followers:", res.get('followers_count'))
        for p in res.get('feed', {}).get('data', []):
            print(f"  FB Post: {p.get('id')} | Likes: {p.get('likes',{}).get('summary',{}).get('total_count')} | Msg: {repr(p.get('message',''))[:60]}")
            for c in p.get('comments', {}).get('data', []):
                print(f"    -> Comment: {c}")
    except Exception as e:
        print("FB Parse Error:", e, r.text[:200])

print("\\n=== 5. LIVE GOOGLE BUSINESS PROFILE ===")
gb_accs = SocialAccount.objects.filter(domain=domain, platform='gb', is_active=True)
for gb_acc in gb_accs:
    print(f"GB Account {gb_acc.id} - {gb_acc.account_name}: LocID={gb_acc.page_id or gb_acc.account_id}")
    r = requests.get(f"https://mybusinessaccountmanagement.googleapis.com/v1/accounts", headers={'Authorization': f"Bearer {gb_acc.access_token}"}, timeout=8)
    print("  GB Accounts API Status:", r.status_code, r.text[:150])

print("\\n=== 6. LIVE YOUTUBE API ===")
yt_acc = SocialAccount.objects.filter(domain=domain, platform='yt', is_active=True).first()
if yt_acc:
    r = requests.get("https://www.googleapis.com/youtube/v3/channels?part=snippet,statistics&mine=true", headers={'Authorization': f"Bearer {yt_acc.access_token}"}, timeout=8)
    print("YT Channel Status:", r.status_code)
    try:
        res = r.json()
        if res.get('items'):
            print("YT Channel:", res.get('items')[0].get('snippet', {}).get('title'), "Stats:", res.get('items')[0].get('statistics', {}))
        else:
            print("YT items empty:", res)
    except Exception as e:
        print("YT Error:", e, r.text[:150])

print("\\n=== 7. LIVE TWITTER/X API ===")
tw_acc = SocialAccount.objects.filter(domain=domain, platform='tw', is_active=True).first()
if tw_acc:
    r = requests.get("https://api.twitter.com/2/users/me?user.fields=public_metrics,description", headers={'Authorization': f"Bearer {tw_acc.access_token}"}, timeout=8)
    print("TW Status:", r.status_code, r.text[:150])
'''

with sftp.file('/var/www/panel/inspect_real.py', 'w') as f:
    f.write(script_content)

stdin, stdout, stderr = ssh.exec_command('/var/www/panel/venv/bin/python3 /var/www/panel/inspect_real.py')
print(stdout.read().decode())
print(stderr.read().decode())

sftp.close()
ssh.close()
