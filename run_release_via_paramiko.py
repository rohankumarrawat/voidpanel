#!/usr/bin/env python3
import os, subprocess, paramiko, sys

LOCAL_DIR = '/Users/rohan/Desktop/voidpanel'
HOST = 'fast.voidpanel.com'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'
VERSION = '2.5.51'
NOTES = 'Modernize services dropdown into a wide multi-column mega menu with showcase sidebar'

def run_local(cmd):
    print(f"Running local command: {cmd}")
    res = subprocess.run(cmd, shell=True, cwd=LOCAL_DIR, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Error running local command: {res.stderr}")
        sys.exit(1)
    return res.stdout

print("=== STEP 1: Copying installer scripts to website static folder ===")
run_local("cp ubuntu.sh website/voidpanel/static/ubuntu.sh")
run_local("cp almalinux.sh website/voidpanel/static/almalinux.sh")
run_local("cp install.sh website/voidpanel/static/install.sh")

print("=== STEP 2: Packaging Archive.zip locally (excluding temp/venv files) ===")
if os.path.exists(os.path.join(LOCAL_DIR, 'Archive.zip')):
    os.remove(os.path.join(LOCAL_DIR, 'Archive.zip'))

run_local('zip -r Archive.zip . -x "*.git*" -x "*venv*" -x "website/*" -x "*.env" -x "*.sqlite3" -x "media/*" -x "*.DS_Store" -x "*__pycache__*" -x "Archive.zip" -x ".gemini/*"')

print("=== STEP 3: Copying Archive.zip to website locations ===")
run_local("cp Archive.zip website/voidpanel/Archive.zip")
run_local("cp Archive.zip website/voidpanel/static/voidpanel.zip")
print("Archive packaging complete.")

print("=== STEP 4: Connecting to server via SSH/SFTP ===")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)
sftp = ssh.open_sftp()

def upload_with_progress(local, remote):
    print(f"Uploading {os.path.basename(local)} to {remote} ...")
    last_reported = [0]
    def cb(transferred, total):
        pct = (transferred / total) * 100
        if int(pct) >= last_reported[0] + 10 or transferred == total:
            print(f"  Progress: {transferred}/{total} bytes ({pct:.1f}%)")
            last_reported[0] = int(pct)
    sftp.put(local, remote, callback=cb)

print("=== STEP 5: Uploading installer scripts ===")
upload_with_progress(os.path.join(LOCAL_DIR, 'website/voidpanel/static/ubuntu.sh'), '/home/voidpanelc091/voidpanel/static/ubuntu.sh')
upload_with_progress(os.path.join(LOCAL_DIR, 'website/voidpanel/static/almalinux.sh'), '/home/voidpanelc091/voidpanel/static/almalinux.sh')
upload_with_progress(os.path.join(LOCAL_DIR, 'website/voidpanel/static/install.sh'), '/home/voidpanelc091/voidpanel/static/install.sh')

print("=== STEP 6: Uploading voidpanel.zip ===")
upload_with_progress(os.path.join(LOCAL_DIR, 'website/voidpanel/static/voidpanel.zip'), '/home/voidpanelc091/voidpanel/static/voidpanel.zip')
upload_with_progress(os.path.join(LOCAL_DIR, 'website/voidpanel/Archive.zip'), '/home/voidpanelc091/voidpanel/Archive.zip')

print("=== STEP 6b: Uploading updated website urls.py, views.py, and deploy.sh ===")
upload_with_progress(os.path.join(LOCAL_DIR, 'website/voidpanel/voidpanel/urls.py'), '/home/voidpanelc091/voidpanel/voidpanel/urls.py')
upload_with_progress(os.path.join(LOCAL_DIR, 'website/voidpanel/voidpanel/views.py'), '/home/voidpanelc091/voidpanel/voidpanel/views.py')
upload_with_progress(os.path.join(LOCAL_DIR, 'website/voidpanel/deploy/deploy.sh'), '/home/voidpanelc091/voidpanel/deploy/deploy.sh')

# Upload ERP integration database files
upload_with_progress(os.path.join(LOCAL_DIR, 'website/voidpanel/data/models.py'), '/home/voidpanelc091/voidpanel/data/models.py')
upload_with_progress(os.path.join(LOCAL_DIR, 'website/voidpanel/data/admin.py'), '/home/voidpanelc091/voidpanel/data/admin.py')

# Upload ERP templates
upload_with_progress(os.path.join(LOCAL_DIR, 'website/voidpanel/templates/portal.html'), '/home/voidpanelc091/voidpanel/templates/portal.html')
upload_with_progress(os.path.join(LOCAL_DIR, 'website/voidpanel/templates/header.html'), '/home/voidpanelc091/voidpanel/templates/header.html')
upload_with_progress(os.path.join(LOCAL_DIR, 'website/voidpanel/templates/erp_crm_pricing.html'), '/home/voidpanelc091/voidpanel/templates/erp_crm_pricing.html')
upload_with_progress(os.path.join(LOCAL_DIR, 'website/voidpanel/templates/erp_crm_configure.html'), '/home/voidpanelc091/voidpanel/templates/erp_crm_configure.html')
upload_with_progress(os.path.join(LOCAL_DIR, 'website/voidpanel/templates/emails/welcome_erp_crm.html'), '/home/voidpanelc091/voidpanel/templates/emails/welcome_erp_crm.html')
upload_with_progress(os.path.join(LOCAL_DIR, 'website/voidpanel/templates/super_admin_services.html'), '/home/voidpanelc091/voidpanel/templates/super_admin_services.html')

# Upload migrations
upload_with_progress(os.path.join(LOCAL_DIR, 'website/voidpanel/data/migrations/0059_license_tiers.py'), '/home/voidpanelc091/voidpanel/data/migrations/0059_license_tiers.py')
upload_with_progress(os.path.join(LOCAL_DIR, 'website/voidpanel/data/migrations/0060_alter_panellicenserecord_tier_erpcrmorder_and_more.py'), '/home/voidpanelc091/voidpanel/data/migrations/0060_alter_panellicenserecord_tier_erpcrmorder_and_more.py')
upload_with_progress(os.path.join(LOCAL_DIR, 'website/voidpanel/data/migrations/0061_erp_service_custom_domain.py'), '/home/voidpanelc091/voidpanel/data/migrations/0061_erp_service_custom_domain.py')
upload_with_progress(os.path.join(LOCAL_DIR, 'website/voidpanel/data/migrations/0062_erp_order_custom_domain.py'), '/home/voidpanelc091/voidpanel/data/migrations/0062_erp_order_custom_domain.py')

sftp.close()
print("SFTP Upload completed successfully.")

print("=== STEP 7: Executing deploy.sh and reloading uWSGI on the server ===")
def run_remote(cmd):
    print(f"Running remote command: {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd)
    while True:
        line = stdout.readline()
        if not line:
            break
        print(f"  [remote] {line.strip()}")
    err_out = stderr.read().decode('utf-8', errors='replace')
    if err_out:
        print(f"  [remote error] {err_out.strip()}")

run_remote(f"bash /home/voidpanelc091/voidpanel/deploy/deploy.sh {VERSION} '{NOTES}'")
run_remote("pkill -HUP -f voidpanel.ini")

ssh.close()
print("=== DEPLOYMENT AND RELEASE SUCCESSFULLY COMPLETED ===")
