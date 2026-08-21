import paramiko, os

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'
LOCAL_DIR = '/Users/rohan/Desktop/voidpanel'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)
print("Connected to root@207.180.209.216!")

# Check directory structure of /home/voidonyx/voidonyx/
stdin, stdout, stderr = ssh.exec_command("ls -la /home/voidonyx/voidonyx/ /home/voidonyx/voidonyx/templates/")
print("=== /home/voidonyx/voidonyx contents ===")
print(stdout.read().decode())

# Ensure static/khatabook and templates exist
ssh.exec_command("mkdir -p /home/voidonyx/voidonyx/static/khatabook /home/voidonyx/voidonyx/templates/voidonyx")

sftp = ssh.open_sftp()

# 1. Upload khatabook_pricing.html to /home/voidonyx/voidonyx/templates/
local_tpl = f"{LOCAL_DIR}/voidonyx_server/templates/khatabook_pricing.html"
remote_tpl_1 = "/home/voidonyx/voidonyx/templates/khatabook_pricing.html"
remote_tpl_2 = "/home/voidonyx/voidonyx/templates/voidonyx/khatabook_pricing.html"

print(f"Uploading {local_tpl} -> {remote_tpl_1}")
sftp.put(local_tpl, remote_tpl_1)
try:
    sftp.put(local_tpl, remote_tpl_2)
except Exception as e:
    print("voidonyx subfolder:", e)

# 2. Upload images to /home/voidonyx/voidonyx/static/khatabook/
local_img_dir = f"{LOCAL_DIR}/voidonyx_server/static/khatabook"
for img in os.listdir(local_img_dir):
    l_img = os.path.join(local_img_dir, img)
    if os.path.isfile(l_img):
        r_img = f"/home/voidonyx/voidonyx/static/khatabook/{img}"
        print(f"Uploading image {img} -> {r_img}")
        sftp.put(l_img, r_img)

sftp.close()

# 3. Reload uwsgi and nginx
print("\nReloading voidonyx uwsgi & nginx...")
stdin, stdout, stderr = ssh.exec_command("touch /home/voidonyx/voidonyx/wsgi.py /home/voidonyx/voidonyx/voidpanel/wsgi.py /home/voidonyx/voidonyx/voidonyx/wsgi.py 2>/dev/null; pkill -HUP -f 'voidonyx.sock' 2>/dev/null; systemctl reload nginx 2>/dev/null; systemctl restart uwsgi 2>/dev/null || true")
print(stdout.read().decode())

ssh.close()
print("\n🎉 VOIDONYX.IN LIVE DEPLOYMENT COMPLETE!")
