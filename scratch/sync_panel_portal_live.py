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

files_to_sync = [
    # templates
    (f"{LOCAL_DIR}/templates/control/social_portal.html", "/var/www/panel/templates/control/social_portal.html"),
    (f"{LOCAL_DIR}/templates/control/social_portal.html", "/home/voidpanelc091/voidpanel/templates/control/social_portal.html"),
    (f"{LOCAL_DIR}/templates/control/social.html", "/var/www/panel/templates/control/social.html"),
    (f"{LOCAL_DIR}/templates/control/social.html", "/home/voidpanelc091/voidpanel/templates/control/social.html"),
    
    # models & views
    (f"{LOCAL_DIR}/control/models.py", "/var/www/panel/control/models.py"),
    (f"{LOCAL_DIR}/control/models.py", "/home/voidpanelc091/voidpanel/control/models.py"),
    (f"{LOCAL_DIR}/control/views.py", "/var/www/panel/control/views.py"),
    (f"{LOCAL_DIR}/control/views.py", "/home/voidpanelc091/voidpanel/control/views.py"),
]

for l, r in files_to_sync:
    print(f"Syncing {os.path.basename(l)} -> {r}", flush=True)
    sftp.put(l, r)

sftp.close()

# Restart all web services
cmds = [
    "systemctl restart voidpanel.service 2>/dev/null || true",
    "systemctl restart app-voidpanelc091-voidpanel.service 2>/dev/null || true",
    "systemctl restart app-voidonyx-voidonyx.service 2>/dev/null || true",
    "systemctl reload nginx",
    "systemctl is-active voidpanel.service app-voidpanelc091-voidpanel.service",
]

for c in cmds:
    print(f"Executing: {c}", flush=True)
    stdin, stdout, stderr = ssh.exec_command(c)
    out = stdout.read().decode().strip()
    if out:
        print(f"  {out}", flush=True)

ssh.close()
print("\n🎉 SOCIAL PORTAL LIVE SYNC COMPLETED SUCCESSFULLY!", flush=True)
