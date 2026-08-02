#!/usr/bin/env python3
"""Deploy Lead Generator provisioning API to leads.voidonyx.in (207.180.209.216)"""
import paramiko, os

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'
REMOTE_BASE = '/home/voidonyx/leads'
LOCAL_BASE = '/Users/rohan/Desktop/LEads'

FILES_TO_DEPLOY = [
    'api/api_v1.py',
    'api/urls.py',
]

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
        if err.strip(): print(f"  STDERR: {err.strip()}")
    return out, err

def main():
    ssh = connect()
    sftp = ssh.open_sftp()
    print("✅ Connected to leads.voidonyx.in")

    # Upload files
    for f in FILES_TO_DEPLOY:
        local = os.path.join(LOCAL_BASE, f)
        remote = f"{REMOTE_BASE}/{f}"
        print(f"\n📤 Uploading {f} ...")
        # Backup first
        run(ssh, f"cp {remote} {remote}.bak 2>/dev/null", show=False)
        sftp.put(local, remote)
        print(f"   ✅ {f} uploaded")

    # Restart the uWSGI service
    print("\n🔄 Restarting Leads service ...")
    run(ssh, "systemctl restart leads 2>/dev/null || touch /home/voidonyx/leads/leads.sock")
    
    # Try different restart methods
    out, _ = run(ssh, "systemctl list-units --type=service | grep -i lead", show=True)
    if not out.strip():
        print("  No systemd service found, trying uwsgi reload...")
        run(ssh, "pkill -HUP -f 'uwsgi.*leads' 2>/dev/null")
        run(ssh, "touch /home/voidonyx/leads/voidonyx/wsgi.py 2>/dev/null")
    
    # Verify the API endpoint
    print("\n🔍 Testing provisioning endpoint ...")
    out, _ = run(ssh, f"curl -s -o /dev/null -w '%{{http_code}}' https://leads.voidonyx.in/api/v1/saas/packages/")
    print(f"   GET /api/v1/saas/packages/ → HTTP {out.strip()}")

    out, _ = run(ssh, f"curl -s https://leads.voidonyx.in/api/v1/saas/packages/ 2>/dev/null | head -200")
    print(f"   Response: {out[:300]}")

    sftp.close()
    ssh.close()
    print("\n✅ Deployment complete!")

if __name__ == '__main__':
    main()
