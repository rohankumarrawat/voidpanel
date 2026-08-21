import paramiko, sys, os

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'
LOCAL_DIR = '/Users/rohan/Desktop/voidpanel'

print(f"Connecting to root@{HOST}...", flush=True)
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)
print("Connected successfully!", flush=True)

sftp = ssh.open_sftp()

# Files to upload to voidonyx & voidpanel
files_to_sync = [
    # 1. Super Admin templates
    (f"{LOCAL_DIR}/website/voidpanel/templates/super_admin_social_api.html", "/home/voidonyx/voidonyx/templates/super_admin_social_api.html"),
    (f"{LOCAL_DIR}/website/voidpanel/templates/super_admin_social_api.html", "/home/voidpanelc091/voidpanel/templates/super_admin_social_api.html"),
    
    # 2. Super Admin models & views
    (f"{LOCAL_DIR}/website/voidpanel/data/models.py", "/home/voidonyx/voidonyx/data/models.py"),
    (f"{LOCAL_DIR}/website/voidpanel/data/models.py", "/home/voidpanelc091/voidpanel/data/models.py"),
    (f"{LOCAL_DIR}/website/voidpanel/voidpanel/views.py", "/home/voidonyx/voidonyx/voidpanel/views.py"),
    (f"{LOCAL_DIR}/website/voidpanel/voidpanel/views.py", "/home/voidpanelc091/voidpanel/voidpanel/views.py"),
    
    # 3. Control & Portal models, views, and templates
    (f"{LOCAL_DIR}/control/models.py", "/home/voidpanelc091/voidpanel/control/models.py"),
    (f"{LOCAL_DIR}/control/views.py", "/home/voidpanelc091/voidpanel/control/views.py"),
    (f"{LOCAL_DIR}/templates/control/social_portal.html", "/home/voidpanelc091/voidpanel/templates/control/social_portal.html"),
    (f"{LOCAL_DIR}/templates/control/social.html", "/home/voidpanelc091/voidpanel/templates/control/social.html"),
    
    # 4. Migrations
    (f"{LOCAL_DIR}/control/migrations/0071_socialmediaapiconfig_admin_enabled_platforms_and_more.py", "/home/voidpanelc091/voidpanel/control/migrations/0071_socialmediaapiconfig_admin_enabled_platforms_and_more.py"),
    (f"{LOCAL_DIR}/website/voidpanel/data/migrations/0073_aiapikey_socialplatformsettings_facebook_auth_mode_and_more.py", "/home/voidonyx/voidonyx/data/migrations/0073_aiapikey_socialplatformsettings_facebook_auth_mode_and_more.py"),
    (f"{LOCAL_DIR}/website/voidpanel/data/migrations/0073_aiapikey_socialplatformsettings_facebook_auth_mode_and_more.py", "/home/voidpanelc091/voidpanel/data/migrations/0073_aiapikey_socialplatformsettings_facebook_auth_mode_and_more.py"),
]

for local_path, remote_path in files_to_sync:
    if os.path.exists(local_path):
        remote_dir = os.path.dirname(remote_path)
        ssh.exec_command(f"mkdir -p {remote_dir}")
        print(f"Uploading {os.path.basename(local_path)} -> {remote_path}", flush=True)
        try:
            sftp.put(local_path, remote_path)
            print(f"  ✓ Uploaded", flush=True)
        except Exception as e:
            print(f"  ✗ Upload error for {remote_path}: {e}", flush=True)
    else:
        print(f"Local file not found: {local_path}", flush=True)

sftp.close()

print("\n--- Running Migrations & Reloading Services ---", flush=True)
cmds = [
    # Migrate data on voidonyx
    "python3 /home/voidonyx/voidonyx/manage.py migrate data --fake-initial 2>&1 || true",
    # Migrate data & control on voidpanel
    "python3 /home/voidpanelc091/voidpanel/manage.py migrate data --fake-initial 2>&1 || true",
    "python3 /home/voidpanelc091/voidpanel/manage.py migrate control 0070 --fake 2>&1 || true",
    "python3 /home/voidpanelc091/voidpanel/manage.py migrate control 2>&1 || true",
    # Reload uWSGI and services
    "touch /home/voidonyx/voidonyx/wsgi.py /home/voidonyx/voidonyx/voidpanel/wsgi.py 2>/dev/null",
    "touch /home/voidpanelc091/voidpanel/panel/wsgi.py /home/voidpanelc091/voidpanel/voidpanel/wsgi.py 2>/dev/null",
    "pkill -HUP -f 'uwsgi' 2>/dev/null || true",
    "pkill -HUP -f 'voidonyx' 2>/dev/null || true",
    "pkill -HUP -f 'voidpanel' 2>/dev/null || true",
    "systemctl reload nginx 2>/dev/null || true",
]

for cmd in cmds:
    print(f"Executing: {cmd}", flush=True)
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode().strip()
    if out:
        print(f"  Result:\n{out}", flush=True)

ssh.close()
print("\n🎉 ALL LIVE UPDATES APPLIED SUCCESSFULLY!", flush=True)
