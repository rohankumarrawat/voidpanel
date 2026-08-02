#!/usr/bin/env python3
"""Deploy userapp API module to the live panel server at 207.180.209.216"""
import paramiko
import sys

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

def connect():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)
    return ssh

def run(ssh, cmd, show=True):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=120)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    if show:
        if out.strip(): print(out.strip())
        if err.strip(): print(f"STDERR: {err.strip()}")
    return out, err

ssh = connect()
print("=== Connected to", HOST, "===")

# Step 1: Check if userapp exists on server
print("\n=== Step 1: Checking existing state ===")
out, _ = run(ssh, "ls -la /var/www/panel/userapp/ 2>/dev/null || echo 'NOT_FOUND'")
if 'NOT_FOUND' in out:
    print("userapp not found on server — will deploy fresh.")
else:
    print("userapp exists on server — will update.")

# Step 2: Check if git is available and pull
print("\n=== Step 2: Git pull latest code ===")
out, _ = run(ssh, "cd /var/www/panel && git remote -v 2>/dev/null | head -1", show=False)
if 'github' in out or 'origin' in out:
    print("Git repo detected. Pulling latest...")
    run(ssh, "cd /var/www/panel && git stash 2>&1")
    run(ssh, "cd /var/www/panel && git pull origin main 2>&1")
else:
    print("Not a git repo. Need to rsync userapp files manually.")
    # Use SCP/SFTP to upload the userapp directory
    print("Uploading userapp via SFTP...")
    sftp = ssh.open_sftp()
    
    import os
    local_base = os.path.expanduser('~/Desktop/voidpanel/userapp')
    remote_base = '/var/www/panel/userapp'
    
    # Create remote directory structure
    def sftp_makedirs(sftp, remote_dir):
        try:
            sftp.stat(remote_dir)
        except FileNotFoundError:
            sftp.mkdir(remote_dir)
    
    def upload_dir(local_dir, remote_dir):
        sftp_makedirs(sftp, remote_dir)
        for item in os.listdir(local_dir):
            local_path = os.path.join(local_dir, item)
            remote_path = f"{remote_dir}/{item}"
            if os.path.isdir(local_path):
                if item == '__pycache__':
                    continue
                upload_dir(local_path, remote_path)
            else:
                print(f"  Uploading {item}...")
                sftp.put(local_path, remote_path)
    
    upload_dir(local_base, remote_base)
    sftp.close()
    print("SFTP upload complete.")

# Step 3: Verify userapp is in INSTALLED_APPS
print("\n=== Step 3: Verify INSTALLED_APPS ===")
out, _ = run(ssh, "grep 'userapp' /var/www/panel/panel/settings.py || echo 'NOT_IN_SETTINGS'")
if 'NOT_IN_SETTINGS' in out:
    print("WARNING: userapp not in INSTALLED_APPS! Adding it...")
    run(ssh, """python3 -c "
import re
with open('/var/www/panel/panel/settings.py', 'r') as f:
    content = f.read()
if 'userapp' not in content:
    content = content.replace(\"'control',\", \"'control',\\n    'userapp',\")
    with open('/var/www/panel/panel/settings.py', 'w') as f:
        f.write(content)
    print('Added userapp to INSTALLED_APPS')
else:
    print('Already present')
" """)
else:
    print("userapp already in INSTALLED_APPS ✓")

# Step 4: Verify URL routing
print("\n=== Step 4: Verify URL routing ===")
out, _ = run(ssh, "grep 'userapp.urls' /var/www/panel/panel/urls.py || echo 'NOT_IN_URLS'")
if 'NOT_IN_URLS' in out:
    print("WARNING: userapp URLs not included! Check panel/urls.py manually.")
else:
    print("userapp URLs included ✓")

# Step 5: Verify userapp files
print("\n=== Step 5: Verify userapp files on server ===")
run(ssh, "ls -la /var/www/panel/userapp/")
run(ssh, "ls -la /var/www/panel/userapp/views/")

# Step 6: Restart service
print("\n=== Step 6: Restarting panel service ===")
run(ssh, "systemctl restart panel 2>/dev/null || systemctl restart voidpanel 2>/dev/null || supervisorctl restart panel 2>/dev/null || echo 'Trying gunicorn...'")
run(ssh, "pkill -HUP gunicorn 2>/dev/null || echo 'No gunicorn process found'")

# Step 7: Quick API test
print("\n=== Step 7: Testing API endpoint ===")
out, _ = run(ssh, 'curl -sk -X POST http://127.0.0.1:8000/api/v1/auth/login/ -H "Content-Type: application/json" -d \'{"username":"test","password":"test"}\' 2>/dev/null || curl -sk -X POST http://127.0.0.1/api/v1/auth/login/ -H "Content-Type: application/json" -d \'{"username":"test","password":"test"}\' 2>/dev/null || echo "CURL_FAILED"')
print(f"API test response: {out[:300]}")

ssh.close()
print("\n=== Deployment complete ===")
