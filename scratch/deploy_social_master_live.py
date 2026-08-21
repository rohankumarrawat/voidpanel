import os, sys, paramiko

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'
LOCAL_DIR = '/Users/rohan/Desktop/voidpanel'

print(f"Connecting to root@{HOST}...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)
print("SSH Connected!")

# Find all locations of voidpanel and voidonyx on the server
stdin, stdout, stderr = ssh.exec_command("find /home /var/www -maxdepth 4 -name 'super_admin_social_api.html' -o -name 'social_portal.html' -o -name 'social.html' 2>/dev/null")
found_files = [l.strip() for l in stdout.read().decode().splitlines() if l.strip()]
print("Found remote template files:\n", "\n".join(found_files))

stdin, stdout, stderr = ssh.exec_command("find /home /var/www -maxdepth 4 -name 'models.py' -path '*/data/models.py' -o -path '*/control/models.py' 2>/dev/null")
found_models = [l.strip() for l in stdout.read().decode().splitlines() if l.strip()]
print("\nFound remote model files:\n", "\n".join(found_models))

sftp = ssh.open_sftp()

# 1. Upload Super Admin files (voidonyx.in / voidpanel.com)
local_sa_tpl = f"{LOCAL_DIR}/website/voidpanel/templates/super_admin_social_api.html"
local_web_models = f"{LOCAL_DIR}/website/voidpanel/data/models.py"
local_web_views = f"{LOCAL_DIR}/website/voidpanel/voidpanel/views.py"

# Known voidonyx/website locations
for path in found_files:
    if 'super_admin_social_api.html' in path:
        print(f"Updating: {path}")
        sftp.put(local_sa_tpl, path)

for path in found_models:
    if '/data/models.py' in path:
        print(f"Updating data model: {path}")
        sftp.put(local_web_models, path)

# Find views.py for voidonyx / website
stdin, stdout, stderr = ssh.exec_command("find /home /var/www -maxdepth 4 -name 'views.py' -path '*/voidpanel/views.py' -o -path '*/voidonyx/views.py' 2>/dev/null")
found_web_views = [l.strip() for l in stdout.read().decode().splitlines() if l.strip()]
for path in found_web_views:
    print(f"Updating website views: {path}")
    sftp.put(local_web_views, path)

# 2. Upload Panel & Social Portal files (fast.voidpanel.com / panel instances)
local_ctrl_models = f"{LOCAL_DIR}/control/models.py"
local_ctrl_views = f"{LOCAL_DIR}/control/views.py"
local_portal_tpl = f"{LOCAL_DIR}/templates/control/social_portal.html"
local_social_tpl = f"{LOCAL_DIR}/templates/control/social.html"

for path in found_files:
    if 'social_portal.html' in path:
        print(f"Updating portal template: {path}")
        sftp.put(local_portal_tpl, path)
    elif 'social.html' in path and 'control' in path:
        print(f"Updating social template: {path}")
        sftp.put(local_social_tpl, path)

for path in found_models:
    if '/control/models.py' in path:
        print(f"Updating control model: {path}")
        sftp.put(local_ctrl_models, path)

stdin, stdout, stderr = ssh.exec_command("find /home /var/www -maxdepth 4 -name 'views.py' -path '*/control/views.py' 2>/dev/null")
found_ctrl_views = [l.strip() for l in stdout.read().decode().splitlines() if l.strip()]
for path in found_ctrl_views:
    print(f"Updating control views: {path}")
    sftp.put(local_ctrl_views, path)

# Also copy migrations
sftp.close()

print("\n--- Running Migrations on Live Server ---")
commands = [
    # Run migrations for voidonyx / website
    "cd /home/voidonyx/voidonyx 2>/dev/null && python3 manage.py makemigrations data && python3 manage.py migrate data || true",
    "cd /home/voidpanelc091/voidpanel 2>/dev/null && python3 manage.py makemigrations data && python3 manage.py migrate data || true",
    # Run migrations for control/panel instances
    "cd /home/voidpanelc091/voidpanel 2>/dev/null && python3 manage.py makemigrations control && python3 manage.py migrate control || true",
    "cd /var/www/voidpanel 2>/dev/null && python3 manage.py makemigrations control && python3 manage.py migrate control || true",
    # Reload uWSGI and services
    "systemctl restart uwsgi 2>/dev/null || true",
    "systemctl restart gunicorn 2>/dev/null || true",
    "systemctl reload nginx 2>/dev/null || true",
    "pkill -HUP -f 'uwsgi' 2>/dev/null || true",
    "touch /home/voidonyx/voidonyx/voidpanel/wsgi.py 2>/dev/null || true",
    "touch /home/voidpanelc091/voidpanel/voidpanel/wsgi.py 2>/dev/null || true",
]

for cmd in commands:
    print(f"Running: {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode()
    err = stderr.read().decode()
    if out:
        print("STDOUT:", out.strip())
    if err:
        print("STDERR:", err.strip())

ssh.close()
print("\n🎉 LIVE SERVER DEPLOYMENT COMPLETE!")
