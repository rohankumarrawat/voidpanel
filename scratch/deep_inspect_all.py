import paramiko, time, json

HOST = '207.180.209.216'; PORT = 22; USER = 'root'; PASS = '19072002ROHANkumar!'
ssh = paramiko.SSHClient(); ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
for _ in range(5):
    try:
        ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=20)
        break
    except:
        time.sleep(3)

sftp = ssh.open_sftp()
script = r'''
import sys, os, json, requests
sys.path.insert(0, "/var/www/panel")
os.chdir("/var/www/panel")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "panel.settings")
import django; django.setup()
from control.models import SocialAccount

domain = "rkrawat1907"
result = {}

# 1. Instagram - Full media + comments + tagged media
ig = SocialAccount.objects.filter(domain=domain, platform="ig", is_active=True).first()
if ig:
    r = requests.get(f"https://graph.facebook.com/v19.0/{ig.account_id}/media?fields=id,caption,permalink,timestamp,like_count,comments_count,media_type,comments{{id,text,username,timestamp,from{{id,username}},like_count}}&limit=25&access_token={ig.access_token}", timeout=10)
    result["ig_media"] = r.json() if r.status_code == 200 else {"error": r.status_code, "msg": r.text[:300]}

    r2 = requests.get(f"https://graph.facebook.com/v19.0/{ig.account_id}/tags?fields=id,caption,permalink,timestamp,like_count,comments_count,username&limit=25&access_token={ig.access_token}", timeout=10)
    result["ig_tags"] = r2.json() if r2.status_code == 200 else {"error": r2.status_code, "msg": r2.text[:300]}

# 2. Facebook - Full feed with comments
fb = SocialAccount.objects.filter(domain=domain, platform="fb", is_active=True).first()
if fb:
    tid = fb.page_id or "me"
    r = requests.get(f"https://graph.facebook.com/v19.0/{tid}?fields=id,name,fan_count,followers_count,overall_star_rating,rating_count,feed{{id,message,permalink_url,created_time,full_picture,likes.summary(true),comments.summary(true){{id,message,from{{id,name}},created_time,like_count}},shares}}&access_token={fb.access_token}", timeout=10)
    result["fb_page"] = r.json() if r.status_code == 200 else {"error": r.status_code, "msg": r.text[:300]}

    r2 = requests.get(f"https://graph.facebook.com/v19.0/{tid}/ratings?fields=reviewer{{id,name}},rating,review_text,created_time&access_token={fb.access_token}", timeout=10)
    result["fb_ratings"] = r2.json() if r2.status_code == 200 else {"error": r2.status_code, "msg": r2.text[:300]}

# 3. YouTube
yt = SocialAccount.objects.filter(domain=domain, platform="yt", is_active=True).first()
if yt:
    r = requests.get("https://www.googleapis.com/youtube/v3/channels?part=snippet,statistics&mine=true", headers={"Authorization": f"Bearer {yt.access_token}"}, timeout=8)
    result["yt_channel"] = r.json() if r.status_code == 200 else {"error": r.status_code, "msg": r.text[:300]}
    r2 = requests.get("https://www.googleapis.com/youtube/v3/search?part=snippet&forMine=true&type=video&maxResults=10", headers={"Authorization": f"Bearer {yt.access_token}"}, timeout=8)
    result["yt_videos"] = r2.json() if r2.status_code == 200 else {"error": r2.status_code, "msg": r2.text[:300]}

# 4. Twitter
tw = SocialAccount.objects.filter(domain=domain, platform="tw", is_active=True).first()
if tw:
    r = requests.get("https://api.twitter.com/2/users/me?user.fields=public_metrics,description,profile_image_url", headers={"Authorization": f"Bearer {tw.access_token}"}, timeout=8)
    result["tw_me"] = r.json() if r.status_code == 200 else {"error": r.status_code, "msg": r.text[:300]}
    uid = "2090099107226677248"
    r2 = requests.get(f"https://api.twitter.com/2/users/{uid}/mentions?max_results=10&tweet.fields=public_metrics,created_at,text,author_id&expansions=author_id&user.fields=name,username,profile_image_url,public_metrics", headers={"Authorization": f"Bearer {tw.access_token}"}, timeout=8)
    result["tw_mentions"] = r2.json() if r2.status_code == 200 else {"error": r2.status_code, "msg": r2.text[:300]}

# 5. Google Business Reviews
gb_accs = SocialAccount.objects.filter(domain=domain, platform="gb", is_active=True)
result["gb_reviews"] = []
for gb in gb_accs:
    loc_id = gb.page_id or gb.account_id
    r = requests.get(f"https://mybusiness.googleapis.com/v4/accounts/-/locations/{loc_id}/reviews", headers={"Authorization": f"Bearer {gb.access_token}"}, timeout=8)
    result["gb_reviews"].append({"name": gb.account_name, "loc_id": loc_id, "status": r.status_code, "body": r.text[:500]})

# 6. LinkedIn
li = SocialAccount.objects.filter(domain=domain, platform="li", is_active=True).first()
if li:
    r = requests.get("https://api.linkedin.com/v2/userinfo", headers={"Authorization": f"Bearer {li.access_token}"}, timeout=8)
    result["li_profile"] = r.json() if r.status_code == 200 else {"error": r.status_code, "msg": r.text[:300]}

print(json.dumps(result, default=str))
'''

with sftp.file('/var/www/panel/deep_inspect.py', 'w') as f:
    f.write(script)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('/var/www/panel/venv/bin/python3 /var/www/panel/deep_inspect.py')
out = stdout.read().decode()
err = stderr.read().decode()

# Save full output
with open('/Users/rohan/Desktop/voidpanel/scratch/api_results.json', 'w') as f:
    f.write(out)

# Print summary
try:
    data = json.loads(out)
    
    print("=== INSTAGRAM MEDIA ===")
    for m in data.get("ig_media", {}).get("data", []):
        print(f"  {m.get('id')} | {m.get('like_count')} likes | {m.get('comments_count')} comments | {m.get('permalink')}")
        print(f"    Caption: {(m.get('caption') or '')[:60]}")
        for c in m.get('comments', {}).get('data', []):
            print(f"    COMMENT: user={c.get('username')} from={c.get('from')} text={c.get('text')} time={c.get('timestamp')}")
    
    print("\n=== INSTAGRAM TAGS (posts tagging @voidonyx_llp) ===")
    print(json.dumps(data.get("ig_tags", {}), indent=2)[:500])
    
    print("\n=== FACEBOOK PAGE + FEED ===")
    fb = data.get("fb_page", {})
    print(f"  Name: {fb.get('name')} | Followers: {fb.get('followers_count')} | Rating: {fb.get('overall_star_rating')}/{fb.get('rating_count')} ratings")
    for p in fb.get("feed", {}).get("data", []):
        likes = p.get('likes', {}).get('summary', {}).get('total_count', 0)
        cmts = p.get('comments', {}).get('summary', {}).get('total_count', 0)
        print(f"  Post {p.get('id')}: {likes} likes, {cmts} comments | msg={repr(p.get('message',''))[:50]}")
        for c in p.get('comments', {}).get('data', []):
            print(f"    FB COMMENT: from={c.get('from')} msg={c.get('message')} time={c.get('created_time')}")
    
    print("\n=== FACEBOOK RATINGS ===")
    print(json.dumps(data.get("fb_ratings", {}), indent=2)[:500])
    
    print("\n=== YOUTUBE ===")
    yt_ch = data.get("yt_channel", {})
    if yt_ch.get("items"):
        stats = yt_ch["items"][0].get("statistics", {})
        print(f"  Subs: {stats.get('subscriberCount')} | Videos: {stats.get('videoCount')} | Views: {stats.get('viewCount')}")
    yt_v = data.get("yt_videos", {})
    print(f"  Videos found: {len(yt_v.get('items', []))}")
    
    print("\n=== TWITTER ===")
    tw_me = data.get("tw_me", {}).get("data", {})
    tw_pm = tw_me.get("public_metrics", {})
    print(f"  Handle: @{tw_me.get('username')} | Followers: {tw_pm.get('followers_count')} | Tweets: {tw_pm.get('tweet_count')}")
    tw_m = data.get("tw_mentions", {})
    print(f"  Mentions: {json.dumps(tw_m, indent=2)[:400]}")
    
    print("\n=== GOOGLE BUSINESS REVIEWS ===")
    for gb in data.get("gb_reviews", []):
        print(f"  {gb.get('name')}: status={gb.get('status')} body={gb.get('body')[:200]}")
    
    print("\n=== LINKEDIN ===")
    print(json.dumps(data.get("li_profile", {}), indent=2)[:400])

except Exception as e:
    print(f"Parse error: {e}")
    print(out[:3000])

ssh.close()
