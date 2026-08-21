import os, paramiko

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'
LOCAL_DIR = '/Users/rohan/Desktop/voidpanel'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)
sftp = ssh.open_sftp()

# Upload all data migrations
local_data_mig_dir = f"{LOCAL_DIR}/website/voidpanel/data/migrations"
for mig_file in os.listdir(local_data_mig_dir):
    if mig_file.endswith('.py'):
        l_f = os.path.join(local_data_mig_dir, mig_file)
        r_f1 = f"/home/voidonyx/voidonyx/data/migrations/{mig_file}"
        r_f2 = f"/home/voidpanelc091/voidpanel/data/migrations/{mig_file}"
        print(f"Uploading migration {mig_file}...", flush=True)
        sftp.put(l_f, r_f1)
        sftp.put(l_f, r_f2)

# Upload all control migrations
local_ctrl_mig_dir = f"{LOCAL_DIR}/control/migrations"
for mig_file in os.listdir(local_ctrl_mig_dir):
    if mig_file.endswith('.py'):
        l_f = os.path.join(local_ctrl_mig_dir, mig_file)
        r_f2 = f"/home/voidpanelc091/voidpanel/control/migrations/{mig_file}"
        sftp.put(l_f, r_f2)

sftp.close()

# Now run migrations and restart
cmds = [
    "/home/voidonyx/voidonyx/venv/bin/python3 /home/voidonyx/voidonyx/manage.py migrate data --fake-initial 2>&1",
    "/home/voidonyx/voidonyx/venv/bin/python3 /home/voidonyx/voidonyx/manage.py migrate 2>&1",
    "/home/voidpanelc091/voidpanel/venv/bin/python3 /home/voidpanelc091/voidpanel/manage.py migrate data --fake-initial 2>&1",
    "/home/voidpanelc091/voidpanel/venv/bin/python3 /home/voidpanelc091/voidpanel/manage.py migrate control 0070 --fake 2>&1",
    "/home/voidpanelc091/voidpanel/venv/bin/python3 /home/voidpanelc091/voidpanel/manage.py migrate 2>&1",
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
print("\n🎉 ALL MIGRATIONS APPLIED & SERVICES RESTARTED SUCCESSFULLY!", flush=True)
