#!/usr/bin/env python3
"""Deploy Lead Generator checkout flow to VoidPanel server (voidpanel.com)."""
import paramiko, os

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'
REMOTE_BASE = '/home/voidpanelc091/voidpanel'
LOCAL_BASE = '/Users/rohan/Desktop/voidpanel/website/voidpanel'

FILES_TO_DEPLOY = [
    'data/models.py',
    'data/migrations/0066_alter_khatabookorder_package_id_and_more.py',
    'voidpanel/settings.py',
    'voidpanel/urls.py',
    'voidpanel/views.py',
    'templates/lead_generator_configure.html',
    'templates/lead_generator_pricing.html',
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
    print("✅ Connected to voidpanel.com server\n")

    # Upload files
    for f in FILES_TO_DEPLOY:
        local = os.path.join(LOCAL_BASE, f)
        remote = f"{REMOTE_BASE}/{f}"
        print(f"📤 Uploading {f} ...")
        run(ssh, f"cp {remote} {remote}.bak 2>/dev/null", show=False)
        # Ensure remote dir exists
        remote_dir = os.path.dirname(remote)
        run(ssh, f"mkdir -p {remote_dir}", show=False)
        sftp.put(local, remote)
        print(f"   ✅ Done")

    # Run migrations
    print("\n── Running migrations ──")
    run(ssh, f"cd {REMOTE_BASE} && source venv/bin/activate && python manage.py migrate data --noinput 2>&1")

    # Collect static
    print("\n── Collecting static files ──")
    run(ssh, f"cd {REMOTE_BASE} && source venv/bin/activate && python manage.py collectstatic --noinput 2>&1 | tail -5")

    # Restart VoidPanel service
    print("\n── Restarting VoidPanel service ──")
    run(ssh, "systemctl restart voidpanel 2>/dev/null || systemctl restart app-voidpanelc091-voidpanel 2>/dev/null")
    run(ssh, "sleep 3")
    
    # Check status
    out, _ = run(ssh, "systemctl list-units --type=service | grep -i void | head -5")
    
    # Verify
    print("\n── Verifying Lead Generator page ──")
    out, _ = run(ssh, "curl -s -o /dev/null -w '%{http_code}' https://voidpanel.com/lead-generator/")
    print(f"GET /lead-generator/ → HTTP {out.strip()}")
    
    out, _ = run(ssh, "curl -s -o /dev/null -w '%{http_code}' https://voidpanel.com/lead-generator/configure/1/")
    print(f"GET /lead-generator/configure/1/ → HTTP {out.strip()}")

    sftp.close()
    ssh.close()
    print("\n✅ VoidPanel deployment complete!")

if __name__ == '__main__':
    main()
