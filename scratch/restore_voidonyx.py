import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('207.180.209.216', port=22, username='root', password='19072002ROHANkumar!', timeout=15)

VOIDONYX_PAGE_TOKEN = "EAGLWFZBvhn8YBSTe3fGTAaBp9XEO1ylTwOXjZCDNsnjSUGYlKeqfLawQDYMLjEhf79k1Wke1VhIZBXuD1sQQyr0AtW9CZBaMq7oThm2qLrn3GY6xM9KCOZBWYNjpJd3bLaq9IkLgPJ9uxXSapKwkfIBr0eDtZAzr2czxOsBIuFZBJpJZCl8jOnptlLJxjsfgE5yTXIcSZACoQ"

script = r'''
import sys, os
sys.path.insert(0, '/var/www/panel')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "panel.settings")
import django
django.setup()
from control.models import SocialAccount

# Delete the "Rohan Rawat" user profile account
deleted = SocialAccount.objects.filter(platform="fb", account_id="1593307522191206")
print("Deleting %d 'Rohan Rawat' accounts..." % deleted.count())
deleted.delete()

# Also delete any other non-Voidonyx FB accounts
SocialAccount.objects.filter(platform="fb").exclude(page_id="1248611408333420").delete()

# Re-create Voidonyx
acc, created = SocialAccount.objects.update_or_create(
    domain="rkrawat1907",
    platform="fb",
    account_id="1248611408333420",
    defaults={
        "username": "rkrawat1907",
        "account_name": "Voidonyx",
        "account_username": "Voidonyx",
        "access_token": "''' + VOIDONYX_PAGE_TOKEN + r'''",
        "page_id": "1248611408333420",
        "page_name": "Voidonyx",
        "profile_picture_url": "https://scontent.fdel6-1.fna.fbcdn.net/v/t39.30808-1/759823982_122097958869422986_6449347865103869528_n.jpg",
        "is_active": True,
    }
)
print("%s Voidonyx: id=%s domain=%s" % ("Created" if created else "Updated", acc.id, acc.domain))

# Verify
print("\nFinal FB accounts:")
for a in SocialAccount.objects.filter(platform="fb"):
    print("  id=%s domain='%s' name=%s page_id=%s" % (a.id, a.domain, a.account_name, a.page_id))
'''

sftp = ssh.open_sftp()
with sftp.file('/tmp/restore_voidonyx.py', 'w') as f:
    f.write(script)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('cd /var/www/panel && /var/www/panel/venv/bin/python3 /tmp/restore_voidonyx.py')
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print('STDERR:', err[:300])
ssh.close()
