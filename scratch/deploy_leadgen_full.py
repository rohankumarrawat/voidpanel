#!/usr/bin/env python3
"""
Deploy Lead Generator SaaS checkout flow to the VoidPanel production server.
Uploads: views.py, urls.py, models.py, migration, templates, settings.
Then runs migrations and restarts the service.
"""
import paramiko
import os
import sys

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'
REMOTE_BASE = '/home/voidpanelc091/voidpanel'
LOCAL_BASE  = '/Users/rohan/Desktop/voidpanel/website/voidpanel'

FILES_TO_DEPLOY = [
    # Core backend
    'voidpanel/views.py',
    'voidpanel/urls.py',
    'voidpanel/settings.py',

    # Models + migration
    'data/models.py',
    'data/migrations/0066_alter_khatabookorder_package_id_and_more.py',

    # Templates (new)
    'templates/lead_generator_pricing.html',
    'templates/lead_generator_configure.html',
    'templates/emails/welcome_leadgen.html',

    # Templates (updated)
    'templates/portal_services.html',
    'templates/voidonyx/header.html',
]


def connect():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)
    return ssh


def run(ssh, cmd, show=True):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=180)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    if show:
        if out.strip():
            print(out.strip())
        if err.strip():
            print(f"  STDERR: {err.strip()}")
    return out, err


def main():
    ssh = connect()
    sftp = ssh.open_sftp()
    print("✅ Connected to production server\n")

    # ── 1. Upload files ──────────────────────────────────────────────────
    print("═══ Uploading files ═══")
    for f in FILES_TO_DEPLOY:
        local  = os.path.join(LOCAL_BASE, f)
        remote = f"{REMOTE_BASE}/{f}"

        if not os.path.exists(local):
            print(f"  ⚠️  SKIP (not found locally): {f}")
            continue

        # Backup existing file
        run(ssh, f"cp {remote} {remote}.bak 2>/dev/null", show=False)
        # Ensure remote dir exists
        remote_dir = os.path.dirname(remote)
        run(ssh, f"mkdir -p {remote_dir}", show=False)

        sftp.put(local, remote)
        print(f"  📤 {f}")

    # ── 2. Run migrations ────────────────────────────────────────────────
    print("\n═══ Running migrations ═══")
    activate = f"source {REMOTE_BASE}/venv/bin/activate"
    run(ssh, f"cd {REMOTE_BASE} && {activate} && python manage.py migrate data --noinput 2>&1")

    # ── 3. Django system check ───────────────────────────────────────────
    print("\n═══ Django system check ═══")
    out, _ = run(ssh, f"cd {REMOTE_BASE} && {activate} && python manage.py check 2>&1 | tail -3")

    # ── 4. Collect static ────────────────────────────────────────────────
    print("\n═══ Collecting static files ═══")
    run(ssh, f"cd {REMOTE_BASE} && {activate} && python manage.py collectstatic --noinput 2>&1 | tail -3")

    # ── 5. Restart service ───────────────────────────────────────────────
    print("\n═══ Restarting service ═══")
    # Try known service names
    run(ssh, "systemctl restart voidpanel 2>/dev/null || "
            "systemctl restart app-voidpanelc091-voidpanel 2>/dev/null || "
            "systemctl restart voidpanel.service 2>/dev/null")
    run(ssh, "sleep 3", show=False)

    # Check service status
    out, _ = run(ssh, "systemctl is-active voidpanel 2>/dev/null || systemctl is-active app-voidpanelc091-voidpanel 2>/dev/null")
    print(f"  Service status: {out.strip()}")

    # ── 6. Verify routes ────────────────────────────────────────────────
    print("\n═══ Verifying Lead Generator routes ═══")
    
    out, _ = run(ssh, "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/lead-generator/ 2>/dev/null || "
                      "curl -s -o /dev/null -w '%{http_code}' https://voidpanel.com/lead-generator/ 2>/dev/null")
    print(f"  GET /lead-generator/           → HTTP {out.strip()}")

    out, _ = run(ssh, "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/lead-generator/configure/1/ 2>/dev/null || "
                      "curl -s -o /dev/null -w '%{http_code}' https://voidpanel.com/lead-generator/configure/1/ 2>/dev/null")
    print(f"  GET /lead-generator/configure/1/ → HTTP {out.strip()}")

    out, _ = run(ssh, "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/lead-generator/checkout/ 2>/dev/null || "
                      "curl -s -o /dev/null -w '%{http_code}' https://voidpanel.com/lead-generator/checkout/ 2>/dev/null")
    print(f"  GET /lead-generator/checkout/    → HTTP {out.strip()}")

    sftp.close()
    ssh.close()
    print("\n✅ Deployment complete!")
    print("Expected: pricing=200, configure=302 (login redirect), checkout=302 (login redirect)")


if __name__ == '__main__':
    main()
