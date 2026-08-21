import os, json, sys
os.environ['DJANGO_SETTINGS_MODULE'] = 'panel.settings'
sys.path.insert(0, '/var/www/panel')
os.chdir('/var/www/panel')
import django; django.setup()

from control.models import SocialAccount
import requests as _req

accs = SocialAccount.objects.filter(domain='rkrawat1907', is_active=True)
print("=" * 80)
print(f"Total active accounts: {accs.count()}")
print("=" * 80)

for a in accs:
    print(f"\n--- {a.platform.upper()} | {a.account_name} ---")
    print(f"  account_id: {a.account_id}")
    print(f"  page_id: {a.page_id}")
    print(f"  token (first 30): {(a.access_token or '')[:30]}...")
    print(f"  has_refresh: {bool(a.refresh_token)}")
    print(f"  followers: {a.followers_count}")

    # Test each platform API
    try:
        if a.platform == 'ig':
            r = _req.get(
                f"https://graph.facebook.com/v19.0/{a.account_id}/media?fields=id,caption,permalink,comments{{id,text,username,timestamp}}&limit=5&access_token={a.access_token}",
                timeout=10
            )
            print(f"  API Status: {r.status_code}")
            data = r.json()
            if r.status_code == 200 and data.get('data'):
                print(f"  Media count: {len(data['data'])}")
                for m in data['data'][:3]:
                    comments = m.get('comments', {}).get('data', [])
                    print(f"    Media {m['id']}: {len(comments)} comments | caption: {(m.get('caption') or '')[:50]}")
            else:
                print(f"  API Error: {json.dumps(data.get('error', data), indent=2)[:300]}")

        elif a.platform == 'fb':
            target_id = a.page_id or 'me'
            r = _req.get(
                f"https://graph.facebook.com/v19.0/{target_id}/feed?fields=id,message,permalink_url,comments{{id,message,from,created_time}}&limit=5&access_token={a.access_token}",
                timeout=10
            )
            print(f"  API Status: {r.status_code}")
            data = r.json()
            if r.status_code == 200 and data.get('data'):
                print(f"  Posts count: {len(data['data'])}")
                for p in data['data'][:3]:
                    comments = p.get('comments', {}).get('data', [])
                    print(f"    Post {p['id']}: {len(comments)} comments | msg: {(p.get('message') or '')[:50]}")
            else:
                print(f"  API Error: {json.dumps(data.get('error', data), indent=2)[:300]}")

        elif a.platform == 'gb':
            loc_id = a.page_id or a.account_id
            headers = {'Authorization': f'Bearer {a.access_token}'}
            # Try multiple endpoints
            endpoints = [
                f"https://mybusiness.googleapis.com/v4/accounts/{loc_id}/locations/{loc_id}/reviews",
                f"https://mybusiness.googleapis.com/v4/{loc_id}/reviews",
                f"https://mybusinessaccountmanagement.googleapis.com/v1/accounts",
            ]
            for ep in endpoints:
                r = _req.get(ep, headers=headers, timeout=8)
                print(f"  Endpoint: {ep}")
                print(f"  Status: {r.status_code}")
                try:
                    print(f"  Response: {json.dumps(r.json(), indent=2)[:400]}")
                except:
                    print(f"  Response: {r.text[:400]}")

        elif a.platform == 'yt':
            # Try channel info first
            r = _req.get(
                'https://www.googleapis.com/youtube/v3/channels?part=snippet,statistics&mine=true',
                headers={'Authorization': f'Bearer {a.access_token}'},
                timeout=10
            )
            print(f"  Channel API Status: {r.status_code}")
            data = r.json()
            if r.status_code == 200 and data.get('items'):
                ch = data['items'][0]
                print(f"  Channel: {ch['snippet'].get('title')} | Subs: {ch['statistics'].get('subscriberCount')}")
            else:
                print(f"  Channel Error: {json.dumps(data, indent=2)[:300]}")

            # Try comments
            r2 = _req.get(
                'https://www.googleapis.com/youtube/v3/commentThreads?allThreadsRelatedToChannelId=mine&part=snippet&maxResults=5',
                headers={'Authorization': f'Bearer {a.access_token}'},
                timeout=10
            )
            print(f"  Comments API Status: {r2.status_code}")
            data2 = r2.json()
            if r2.status_code == 200 and data2.get('items'):
                print(f"  Comment threads: {len(data2['items'])}")
                for t in data2['items'][:3]:
                    top = t['snippet']['topLevelComment']['snippet']
                    print(f"    {top.get('authorDisplayName')}: {top.get('textDisplay', '')[:60]}")
            else:
                print(f"  Comments Error: {json.dumps(data2, indent=2)[:300]}")

        elif a.platform == 'tw':
            r = _req.get(
                f'https://api.twitter.com/2/users/{a.account_id}/mentions?tweet.fields=created_at,author_id,text&max_results=10&expansions=author_id&user.fields=name,username',
                headers={'Authorization': f'Bearer {a.access_token}'},
                timeout=10
            )
            print(f"  API Status: {r.status_code}")
            data = r.json()
            if r.status_code == 200 and data.get('data'):
                print(f"  Mentions: {len(data['data'])}")
                for tw in data['data'][:3]:
                    print(f"    {tw.get('text', '')[:60]}")
            else:
                print(f"  API Error: {json.dumps(data, indent=2)[:300]}")

        elif a.platform == 'li':
            r = _req.get(
                'https://api.linkedin.com/v2/me',
                headers={'Authorization': f'Bearer {a.access_token}'},
                timeout=10
            )
            print(f"  API Status: {r.status_code}")
            print(f"  Response: {r.text[:300]}")

        elif a.platform == 'pi':
            r = _req.get(
                'https://api.pinterest.com/v5/user_account',
                headers={'Authorization': f'Bearer {a.access_token}'},
                timeout=10
            )
            print(f"  API Status: {r.status_code}")
            print(f"  Response: {r.text[:300]}")

        else:
            print(f"  Unknown platform: {a.platform}")

    except Exception as e:
        print(f"  Exception: {e}")

print("\n" + "=" * 80)
print("AUDIT COMPLETE")
