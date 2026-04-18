import requests

session = requests.Session()

# 1. Get raw CSRF token
print("Fetching / to get CSRF...")
r1 = session.get("http://178.18.250.134:8080/")
csrftoken = session.cookies.get('csrftoken', '')

# 2. Login POST to /login_user/ wait, it's just /
login_data = {
    'username': 'admin',
    'password': 'xTGlnxcqw6kremkqiZgO',
    'csrfmiddlewaretoken': csrftoken
}
r2 = session.post("http://178.18.250.134:8080/", data=login_data, headers={"Referer": "http://178.18.250.134:8080/"})
print("Login POST status:", r2.status_code)

# Get CSRF token
csrf_token2 = session.cookies.get('csrftoken', '')
print("CSRF Token:", csrf_token2)

# 3. Hit the status API
r4 = session.get("http://178.18.250.134:8080/api/nginx-cache/status/?domain=namanitwork.tech")
print("Status GET:", r4.json())

# 4. Try to TOGGLE to false (disable)
print("Turning cache OFF (enable=0)...")
toggle_data = {
    'domain': 'namanitwork.tech',
    'enable': '0'
}
headers = {
    'X-CSRFToken': csrf_token2,
    'Referer': 'http://178.18.250.134:8080/control/index/namanitwork.tech'
}
r5 = session.post("http://178.18.250.134:8080/api/nginx-cache/toggle/", data=toggle_data, headers=headers)
try:
    print("Toggle POST response JSON:", r5.json())
except Exception as e:
    print("Toggle POST response TEXT:", r5.text)

# 5. Check status again
r6 = session.get("http://178.18.250.134:8080/api/nginx-cache/status/?domain=namanitwork.tech")
print("Status GET after toggle:", r6.json())

