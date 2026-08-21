import paramiko

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)

# The page token we got from the direct query
VOIDONYX_PAGE_TOKEN = "EAGLWFZBvhn8YBSTe3fGTAaBp9XEO1ylTwOXjZCDNsnjSUGYlKeqfLawQDYMLjEhf79k1Wke1VhIZBXuD1sQQyr0AtW9CZBaMq7oThm2qLrn3GY6xM9KCOZBWYNjpJd3bLaq9IkLgPJ9uxXSapKwkfIBr0eDtZAzr2czxOsBIuFZBJpJZCl8jOnptlLJxjsfgE5yTXIcSZACoQ"
VOIDONYX_PAGE_ID = "1248611408333420"
VOIDONYX_PIC = "https://scontent.fdel6-1.fna.fbcdn.net/v/t39.30808-1/759823982_122097958869422986_6449347865103869528_n.jpg"

script = r'''
import sys, os
sys.path.insert(0, '/var/www/panel')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "panel.settings")
import django
django.setup()
from control.models import SocialAccount

# Find the user's social accounts
username = "rkrawat1907"
all_accs = SocialAccount.objects.filter(username=username, platform="fb")
print("Current FB accounts for %s:" % username)
for a in all_accs:
    print("  id=%s name=%s page_id=%s" % (a.id, a.account_name, a.page_id))

# Delete non-Voidonyx accounts (Sell Websites, RKM Classes)
deleted = SocialAccount.objects.filter(username=username, platform="fb").exclude(page_id="''' + VOIDONYX_PAGE_ID + r'''")
print("\nDeleting %d non-Voidonyx accounts..." % deleted.count())
deleted.delete()

# Check if Voidonyx already exists
existing = SocialAccount.objects.filter(username=username, platform="fb", page_id="''' + VOIDONYX_PAGE_ID + r'''").first()
if existing:
    print("Updating existing Voidonyx account (id=%s)..." % existing.id)
    existing.access_token = "''' + VOIDONYX_PAGE_TOKEN + r'''"
    existing.account_name = "Voidonyx"
    existing.account_username = "Voidonyx"
    existing.page_name = "Voidonyx"
    existing.profile_picture_url = "''' + VOIDONYX_PIC + r'''"
    existing.save()
    print("Updated!")
else:
    print("Creating new Voidonyx account...")
    acc = SocialAccount(
        username=username,
        platform="fb",
        account_id="''' + VOIDONYX_PAGE_ID + r'''",
        account_name="Voidonyx",
        account_username="Voidonyx",
        access_token="''' + VOIDONYX_PAGE_TOKEN + r'''",
        page_id="''' + VOIDONYX_PAGE_ID + r'''",
        page_name="Voidonyx",
        profile_picture_url="''' + VOIDONYX_PIC + r'''",
    )
    acc.save()
    print("Created! id=%s" % acc.id)

# Verify
final = SocialAccount.objects.filter(username=username, platform="fb")
print("\nFinal FB accounts:")
for a in final:
    print("  id=%s name=%s page_id=%s token=%s..." % (a.id, a.account_name, a.page_id, a.access_token[:20]))
'''

sftp = ssh.open_sftp()
with sftp.file('/tmp/save_voidonyx.py', 'w') as f:
    f.write(script)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('cd /var/www/panel && /var/www/panel/venv/bin/python3 /tmp/save_voidonyx.py')
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print('STDERR:', err[:500])
ssh.close()
