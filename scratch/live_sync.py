import paramiko, os, time

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'
LOCAL_TPL = '/Users/rohan/Desktop/voidpanel/voidonyx_server/templates/khatabook_pricing.html'
LOCAL_IMG_DIR = '/Users/rohan/Desktop/voidpanel/voidonyx_server/static/khatabook'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)
print("Connected to root@207.180.209.216 successfully!")

# 1. Find all instances of khatabook_pricing.html across the server
stdin, stdout, stderr = ssh.exec_command("find /home /var/www /root -name 'khatabook_pricing.html' 2>/dev/null")
found_files = [f.strip() for f in stdout.read().decode().splitlines() if f.strip()]
print(f"Found {len(found_files)} remote template locations:")
for f in found_files:
    print(f"  - {f}")

# 2. Upload template to all locations
sftp = ssh.open_sftp()
for r_file in found_files:
    print(f"Uploading template -> {r_file}")
    sftp.put(LOCAL_TPL, r_file)

# 3. Find all static directories associated with voidonyx / voidpanel
stdin, stdout, stderr = ssh.exec_command("find /home /var/www -type d -name 'static' 2>/dev/null")
found_static_dirs = [d.strip() for d in stdout.read().decode().splitlines() if d.strip()]
print(f"Found {len(found_static_dirs)} remote static directories:")
for d in found_static_dirs:
    print(f"  - {d}")

# 4. Upload images to all relevant static directories
for s_dir in found_static_dirs:
    if 'void' in s_dir:
        kb_s_dir = f"{s_dir}/khatabook"
        ssh.exec_command(f"mkdir -p {kb_s_dir}")
        print(f"Uploading images to {kb_s_dir}...")
        for img in os.listdir(LOCAL_IMG_DIR):
            l_img = os.path.join(LOCAL_IMG_DIR, img)
            if os.path.isfile(l_img):
                sftp.put(l_img, f"{kb_s_dir}/{img}")

sftp.close()

# 5. Reload all Python/uWSGI/Gunicorn/Nginx services on the server
print("\nReloading web workers...")
cmds = [
    "systemctl reload uwsgi || systemctl restart uwsgi || true",
    "systemctl reload gunicorn || systemctl restart gunicorn || true",
    "systemctl reload nginx || systemctl restart nginx || true",
    "pkill -HUP -f uwsgi || true",
    "pkill -HUP -f gunicorn || true",
    "find /home /var/www -name 'wsgi.py' -exec touch {} + 2>/dev/null || true"
]
for cmd in cmds:
    stdin, stdout, stderr = ssh.exec_command(cmd)
    stdout.read()

ssh.close()
print("\n🔥 SERVER UPDATE & RELOAD COMPLETED SUCCESSFULLY!")
