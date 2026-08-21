import requests, urllib.parse

client_id = 'TTBUa2RhLUNDbExOcFNMNmRUSkE6MTpjaQ'
redirect_uri_1 = 'https://fast.voidpanel.com/control/social/callback/twitter/'
redirect_uri_2 = 'https://fast.voidpanel.com:8082/control/social/callback/twitter/'

# Test with safe='' (fully encoded) vs safe='/' (partially encoded)
for domain_host in ['twitter.com', 'x.com']:
    for r_uri in [redirect_uri_1, redirect_uri_2]:
        for safe_param in ['', '/']:
            enc_uri = urllib.parse.quote(r_uri, safe=safe_param)
            url = f"https://{domain_host}/i/oauth2/authorize?response_type=code&client_id={client_id}&redirect_uri={enc_uri}&scope=tweet.read%20tweet.write%20users.read%20offline.access&state=test1234&code_challenge=testchallenge123456789012345678901234567890&code_challenge_method=plain"
            r = requests.get(url, allow_redirects=False, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'})
            print(f"Host: {domain_host} | safe: {repr(safe_param)} | URI: {r_uri}")
            print(f"  Status: {r.status_code} | Location: {r.headers.get('Location', '')[:100]}")
            if r.status_code == 200:
                print(f"  Body snippet: {r.text[:200]}")
            print()
