#!/usr/bin/env python3
"""
Deploy WhatsApp Business API changes to live voidonyx server.
Only touches 3 files + 1 new migration. No data removed.
"""
import subprocess, sys, os

SERVER   = 'root@207.180.209.216'
PASSWORD = '19072002ROHANkumar!'
LOCAL_BASE = '/Users/rohan/Desktop/voidpanel/website/voidpanel'
REMOTE_BASE = '/home/voidonyx/voidonyx'

FILES = [
    ('data/models.py',                                      'data/models.py'),
    ('data/migrations/0070_whatsappconfig_api_fields.py',   'data/migrations/0070_whatsappconfig_api_fields.py'),
    ('voidpanel/views.py',                                   'voidpanel/views.py'),
    ('templates/super_admin_whatsapp.html',                  'templates/super_admin_whatsapp.html'),
]

def run_expect(commands_str):
    """Run SSH commands via expect."""
    script = f'''
spawn ssh -o StrictHostKeyChecking=no {SERVER}
expect {{
    "*password*" {{send "{PASSWORD}\\r"}}
    timeout {{exit 1}}
}}
expect {{
    "*#*" {{send "{commands_str}\\r"}}
    timeout {{exit 1}}
}}
expect {{
    "*#*" {{send "exit\\r"}}
    timeout {{}}
}}
expect eof
'''
    result = subprocess.run(['expect', '-c', script], capture_output=True, text=True, timeout=60)
    print(result.stdout)
    if result.returncode != 0:
        print(f"STDERR: {result.stderr}")
    return result.returncode

def scp_file(local_path, remote_path):
    """SCP a file to the remote server using expect."""
    script = f'''
spawn scp -o StrictHostKeyChecking=no {local_path} {SERVER}:{remote_path}
expect {{
    "*password*" {{send "{PASSWORD}\\r"}}
    timeout {{exit 1}}
}}
expect eof
'''
    result = subprocess.run(['expect', '-c', script], capture_output=True, text=True, timeout=30)
    print(f"  SCP {os.path.basename(local_path)} -> {remote_path}: {'OK' if result.returncode == 0 else 'FAIL'}")
    if result.returncode != 0:
        print(f"  Error: {result.stderr}")
    return result.returncode == 0

def main():
    print("=" * 60)
    print("WhatsApp Business API — Live Deployment")
    print("=" * 60)

    # Step 1: Upload files
    print("\n[1/3] Uploading files to live server...")
    all_ok = True
    for local_rel, remote_rel in FILES:
        local = os.path.join(LOCAL_BASE, local_rel)
        remote = os.path.join(REMOTE_BASE, remote_rel)
        if not os.path.exists(local):
            print(f"  ERROR: Local file not found: {local}")
            all_ok = False
            continue
        if not scp_file(local, remote):
            all_ok = False

    if not all_ok:
        print("\nSome file uploads failed. Aborting.")
        sys.exit(1)

    # Step 2: Run migration
    print("\n[2/3] Running database migration...")
    run_expect("cd /home/voidonyx/voidonyx && source venv/bin/activate && python manage.py migrate data --no-input && echo 'MIGRATION_OK'")

    # Step 3: Restart gunicorn
    print("\n[3/3] Restarting gunicorn service...")
    run_expect("systemctl restart voidonyx && sleep 2 && systemctl status voidonyx --no-pager -l | head -15 && echo 'RESTART_OK'")

    print("\n" + "=" * 60)
    print("Deployment complete!")
    print("=" * 60)

if __name__ == '__main__':
    main()
