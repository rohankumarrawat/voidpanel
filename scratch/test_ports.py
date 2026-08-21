import requests

print("Testing https://fast.voidpanel.com:8082/...")
try:
    r = requests.get('https://fast.voidpanel.com:8082/control/login/', timeout=10, verify=False)
    print("Port 8082 status:", r.status_code)
except Exception as e:
    print("Port 8082 error:", e)

print("\nTesting https://fast.voidpanel.com/ (Port 443 redirect)...")
try:
    r = requests.get('https://fast.voidpanel.com/', timeout=10, verify=False, allow_redirects=False)
    print("Port 443 status:", r.status_code)
    print("Port 443 Location header:", r.headers.get('Location'))
except Exception as e:
    print("Port 443 error:", e)
