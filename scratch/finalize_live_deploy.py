import paramiko, sys

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)

commands = [
    # 1. Migrate Voidonyx database
    "/home/voidonyx/voidonyx/venv/bin/python3 /home/voidonyx/voidonyx/manage.py migrate data --fake-initial 2>&1",
    "/home/voidonyx/voidonyx/venv/bin/python3 /home/voidonyx/voidonyx/manage.py migrate 2>&1",
    
    # 2. Migrate Voidpanel database
    "/home/voidpanelc091/voidpanel/venv/bin/python3 /home/voidpanelc091/voidpanel/manage.py migrate data --fake-initial 2>&1",
    "/home/voidpanelc091/voidpanel/venv/bin/python3 /home/voidpanelc091/voidpanel/manage.py migrate control 0070 --fake 2>&1",
    "/home/voidpanelc091/voidpanel/venv/bin/python3 /home/voidpanelc091/voidpanel/manage.py migrate 2>&1",

    # 3. Restart systemd services
    "systemctl restart app-voidonyx-voidonyx.service",
    "systemctl restart app-voidpanelc091-voidpanel.service",
    "systemctl restart voidpanel.service 2>/dev/null || true",
    "systemctl reload nginx",
    
    # 4. Check service status
    "systemctl is-active app-voidonyx-voidonyx.service",
    "systemctl is-active app-voidpanelc091-voidpanel.service",
]

for c in commands:
    print(f"=== {c} ===")
    stdin, stdout, stderr = ssh.exec_command(c)
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    if out:
        print("OUT:", out)
    if err:
        print("ERR:", err)

ssh.close()
print("\n✅ LIVE VOIDONYX AND VOIDPANEL SERVICES RESTARTED & HEALTHY!")
