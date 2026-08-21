import paramiko

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'
LOCAL_DIR = '/Users/rohan/Desktop/voidpanel'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)
print("Connected!")

# Find the VoidOnyx views.py location
stdin, stdout, stderr = ssh.exec_command("find /home/voidonyx -name 'views.py' -path '*/voidpanel/*' 2>/dev/null")
paths = stdout.read().decode().strip().split('\n')
print(f"Found VoidOnyx views.py at: {paths}")

sftp = ssh.open_sftp()

# Upload views.py to VoidOnyx
local_views = f"{LOCAL_DIR}/voidonyx_server/voidpanel/views.py"
for rp in paths:
    rp = rp.strip()
    if rp and 'voidpanel' in rp:
        import os
        size = os.path.getsize(local_views)
        print(f"Uploading VoidOnyx views.py ({size} bytes) -> {rp}")
        sftp.put(local_views, rp)
        print("  -> Done")

sftp.close()

# Restart VoidOnyx
print("\nRestarting VoidOnyx...")
stdin, stdout, stderr = ssh.exec_command(
    "touch /home/voidonyx/voidonyx/voidpanel/wsgi.py 2>/dev/null; "
    "systemctl restart uwsgi 2>/dev/null; "
    "sleep 2; "
    "curl -s -o /dev/null -w '%{http_code}' https://voidonyx.in/ 2>/dev/null || echo 'curl failed'"
)
result = stdout.read().decode().strip()
print(f"VoidOnyx status check: {result}")

ssh.close()
print("\n✅ VoidOnyx deployment complete!")
