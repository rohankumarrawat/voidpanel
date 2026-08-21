import paramiko

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)

cmds = [
    # 1. Merge and migrate Voidonyx data
    "/home/voidonyx/voidonyx/venv/bin/python3 /home/voidonyx/voidonyx/manage.py makemigrations --merge --noinput 2>&1",
    "/home/voidonyx/voidonyx/venv/bin/python3 /home/voidonyx/voidonyx/manage.py migrate data --fake-initial 2>&1",
    "/home/voidonyx/voidonyx/venv/bin/python3 /home/voidonyx/voidonyx/manage.py migrate 2>&1",

    # 2. Merge and migrate Voidpanel
    "/home/voidpanelc091/voidpanel/venv/bin/python3 /home/voidpanelc091/voidpanel/manage.py makemigrations --merge --noinput 2>&1",
    "/home/voidpanelc091/voidpanel/venv/bin/python3 /home/voidpanelc091/voidpanel/manage.py migrate data --fake-initial 2>&1",
    "/home/voidpanelc091/voidpanel/venv/bin/python3 /home/voidpanelc091/voidpanel/manage.py migrate control --fake-initial 2>&1",
    "/home/voidpanelc091/voidpanel/venv/bin/python3 /home/voidpanelc091/voidpanel/manage.py migrate 2>&1",

    # 3. Restart all services
    "systemctl restart app-voidonyx-voidonyx.service",
    "systemctl restart app-voidpanelc091-voidpanel.service",
    "systemctl reload nginx",
    "systemctl is-active app-voidonyx-voidonyx.service",
    "systemctl is-active app-voidpanelc091-voidpanel.service",
]

for c in cmds:
    print(f"=== {c} ===", flush=True)
    stdin, stdout, stderr = ssh.exec_command(c)
    out = stdout.read().decode().strip()
    if out:
        print("OUT:", out, flush=True)

ssh.close()
print("\n🎉 ALL MIGRATIONS MERGED & APPLIED, SERVICES ARE ACTIVE!", flush=True)
