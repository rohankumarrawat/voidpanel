import requests

url = "https://x.com/i/oauth2/authorize?response_type=code&client_id=TTBUa2RhLUNDbExOcFNMNmRUSkE6MTpjaQ&redirect_uri=https%3A%2F%2Ffast.voidpanel.com%2Fcontrol%2Fsocial%2Fcallback%2Ftwitter%2F&scope=tweet.read+tweet.write+users.read+offline.access&state=Ktx9Nb3D3Ij9OSiGNxAoSw&code_challenge=gc77_92wXYny-byCBPm3eyhq0gxwfl90anI7bLoaTFM&code_challenge_method=S256"

r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'})
print("Status code:", r.status_code)
print("Content-Type:", r.headers.get('content-type'))
print("Contains 'Authorize':", 'Authorize' in r.text or 'authorize' in r.text or 'consent' in r.text or 'Log in' in r.text)
