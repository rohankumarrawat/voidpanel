import os, paramiko, sys

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'
LOCAL_DIR = '/Users/rohan/Desktop/voidpanel'

print(f"Connecting to {HOST}:{PORT} as {USER}...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    ssh.connect(
        HOST,
        port=PORT,
        username=USER,
        password=PASS,
        timeout=15,
        look_for_keys=False,
        allow_agent=False,
        auth_timeout=15,
        banner_timeout=15
    )
    print("SSH Authentication SUCCESSFUL!")

    # Find the remote voidpanel web directory
    stdin, stdout, stderr = ssh.exec_command("find /home -maxdepth 3 -name 'khatabook_pricing.html' 2>/dev/null")
    found_templates = [line.strip() for line in stdout.read().decode().splitlines() if line.strip()]
    print("Found remote templates:", found_templates)

    stdin, stdout, stderr = ssh.exec_command("find /var/www /home -maxdepth 3 -name 'voidpanel' -type d 2>/dev/null")
    found_dirs = [line.strip() for line in stdout.read().decode().splitlines() if line.strip()]
    print("Found remote voidpanel dirs:", found_dirs)

    sftp = ssh.open_sftp()

    # Upload updated template to all found remote locations (and default paths)
    local_tpl = f"{LOCAL_DIR}/voidonyx_server/templates/khatabook_pricing.html"
    target_tpl_paths = set(found_templates)
    target_tpl_paths.add('/home/voidpanelc091/voidpanel/templates/khatabook_pricing.html')
    target_tpl_paths.add('/home/voidpanelc091/voidpanel/templates/voidonyx/khatabook_pricing.html')

    for r_tpl in target_tpl_paths:
        parent = os.path.dirname(r_tpl)
        ssh.exec_command(f"mkdir -p {parent}")
        print(f"Uploading template: {r_tpl}")
        sftp.put(local_tpl, r_tpl)

    # Upload all images from local static/khatabook/
    local_img_dir = f"{LOCAL_DIR}/voidonyx_server/static/khatabook"
    remote_img_dirs = [
        '/home/voidpanelc091/voidpanel/static/khatabook',
        '/home/voidpanelc091/voidpanel/staticfiles/khatabook'
    ]

    for r_img_dir in remote_img_dirs:
        ssh.exec_command(f"mkdir -p {r_img_dir}")
        for img_name in os.listdir(local_img_dir):
            l_img_path = os.path.join(local_img_dir, img_name)
            if os.path.isfile(l_img_path):
                r_img_path = f"{r_img_dir}/{img_name}"
                print(f"Uploading asset: {img_name} -> {r_img_path}")
                sftp.put(l_img_path, r_img_path)

    sftp.close()

    # Reload application server (uWSGI / systemctl / python reload)
    print("\nReloading web services on server...")
    reload_cmds = [
        "touch /home/voidpanelc091/voidpanel/voidpanel/wsgi.py 2>/dev/null || true",
        "systemctl reload uwsgi 2>/dev/null || systemctl restart uwsgi 2>/dev/null || true",
        "pkill -HUP -f 'voidpanel' 2>/dev/null || true",
        "systemctl reload nginx 2>/dev/null || true"
    ]
    for cmd in reload_cmds:
        stdin, stdout, stderr = ssh.exec_command(cmd)
        stdout.read()

    print("\n==========================================")
    print("🎉 DEPLOYMENT TO LIVE SERVER COMPLETED!")
    print("==========================================")
    ssh.close()

except Exception as e:
    print(f"DEPLOYMENT ERROR: {e}")
    sys.exit(1)
