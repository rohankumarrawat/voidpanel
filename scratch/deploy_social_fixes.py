#!/usr/bin/env python3
"""Deploy all local changes to the server and restart services."""
import paramiko, os

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

FILES = [
    ('control/views.py', '/var/www/panel/control/views.py'),
    ('templates/control/social_portal.html', '/var/www/panel/templates/control/social_portal.html'),
]

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=30)
print("Connected")

sftp = ssh.open_sftp()
for local_rel, remote in FILES:
    local = os.path.join('/Users/rohan/Desktop/voidpanel', local_rel)
    if os.path.exists(local):
        sftp.put(local, remote)
        print(f"  ✓ Uploaded {local_rel}")
    else:
        print(f"  ✗ Missing {local_rel}")
sftp.close()

# Restart services
for svc in ['voidpanel', 'voidpanel-daphne']:
    stdin, stdout, stderr = ssh.exec_command(f'systemctl restart {svc}', timeout=15)
    stdout.read()
    print(f"  ✓ Restarted {svc}")

# Verify services are running
import time
time.sleep(2)
for svc in ['voidpanel', 'voidpanel-daphne']:
    stdin, stdout, stderr = ssh.exec_command(f'systemctl is-active {svc}', timeout=10)
    status = stdout.read().decode().strip()
    print(f"  {svc}: {status}")

ssh.close()
print("Done!")
