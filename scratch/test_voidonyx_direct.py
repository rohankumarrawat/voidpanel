import paramiko

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)

test_script = r'''
import sys, os, requests
sys.path.insert(0, '/var/www/panel')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "panel.settings")
import django
django.setup()
from control.models import SocialAccount, SocialMediaAPIConfig

VOIDONYX_ID = "124861140833420"

cfg = SocialMediaAPIConfig.objects.first()
app_id = cfg.facebook_app_id if cfg else ""
app_secret = cfg.facebook_app_secret if cfg else ""

# Get a working page token
acc = SocialAccount.objects.filter(page_id="226889683992110").first()
if not acc:
    print("No RKM account found")
    exit()

tok = acc.access_token

# Test 1: Try vanity username lookup
r = requests.get("https://graph.facebook.com/v19.0/voidonyx",
    params={"fields": "id,name,category", "access_token": tok}, timeout=10)
print("[TEST 1] /voidonyx vanity lookup: status=%s" % r.status_code)
print("  %s" % r.text[:500])

# Test 2: Try different API versions
for ver in ["v18.0", "v17.0", "v16.0", "v21.0"]:
    r2 = requests.get("https://graph.facebook.com/%s/%s" % (ver, VOIDONYX_ID),
        params={"fields": "id,name", "access_token": tok}, timeout=10)
    print("\n[TEST 2] %s /%s: status=%s" % (ver, VOIDONYX_ID, r2.status_code))
    print("  %s" % r2.text[:300])

# Test 3: Try without version prefix
r3 = requests.get("https://graph.facebook.com/%s" % VOIDONYX_ID,
    params={"fields": "id,name", "access_token": tok}, timeout=10)
print("\n[TEST 3] No version prefix: status=%s" % r3.status_code)
print("  %s" % r3.text[:300])

# Test 4: Check the app's mode (dev vs live)
if app_id and app_secret:
    app_token = app_id + "|" + app_secret
    r4 = requests.get("https://graph.facebook.com/v19.0/%s" % app_id,
        params={"fields": "id,name,link,category", "access_token": app_token}, timeout=10)
    print("\n[TEST 4] App info: status=%s" % r4.status_code)
    print("  %s" % r4.text[:500])

# Test 5: Try /me/accounts with the RKM page token to see if it returns other pages
r5 = requests.get("https://graph.facebook.com/v19.0/me",
    params={"fields": "id,name", "access_token": tok}, timeout=10)
print("\n[TEST 5] /me with RKM token: status=%s" % r5.status_code)
print("  %s" % r5.text[:300])
'''

sftp = ssh.open_sftp()
with sftp.file('/tmp/test_voidonyx6.py', 'w') as f:
    f.write(test_script)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('cd /var/www/panel && /var/www/panel/venv/bin/python3 /tmp/test_voidonyx6.py')
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print('STDERR:', err[:300])
ssh.close()
