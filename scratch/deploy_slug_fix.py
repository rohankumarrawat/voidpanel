import paramiko, os

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'
LOCAL_DIR = '/Users/rohan/Desktop/voidpanel'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)
sftp = ssh.open_sftp()

local_views = f"{LOCAL_DIR}/website/voidpanel/voidpanel/views.py"
remote_views_paths = [
    "/home/voidonyx/voidonyx/voidpanel/views.py",
    "/home/voidpanelc091/voidpanel/voidpanel/views.py",
]

for r in remote_views_paths:
    print(f"Uploading views.py -> {r}", flush=True)
    sftp.put(local_views, r)

sftp.close()

cmds = [
    "systemctl restart app-voidonyx-voidonyx.service",
    "systemctl restart app-voidpanelc091-voidpanel.service",
    "systemctl restart voidpanel.service",
    "systemctl reload nginx",
]

for c in cmds:
    print(f"Running: {c}", flush=True)
    stdin, stdout, stderr = ssh.exec_command(c)
    out = stdout.read().decode().strip()
    if out:
        print(f"  {out}", flush=True)

ssh.close()
print("\n🎉 ALL SERVICES RESTARTED WITH FULL-SLUG REDIRECT LOGIC!", flush=True)
