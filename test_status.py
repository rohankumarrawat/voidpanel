import requests

session = requests.Session()

# 1. Get CSRF
print("Fetching / to get CSRF...")
r1 = session.get("http://178.18.250.134:8080/")
csrftoken = session.cookies.get('csrftoken', '')

# 2. Login
login_data = {'username': 'admin', 'password': 'xTGlnxcqw6kremkqiZgO', 'csrfmiddlewaretoken': csrftoken}
r2 = session.post("http://178.18.250.134:8080/", data=login_data, headers={"Referer": "http://178.18.250.134:8080/"})

# 3. Status API
r4 = session.get("http://178.18.250.134:8080/api/nginx-cache/status/?domain=namanitwork.tech")
print("Status GET:", r4.json())

