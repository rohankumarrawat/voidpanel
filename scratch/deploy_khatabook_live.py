import os, paramiko

HOST = 'fast.voidpanel.com'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'
REMOTE_BASE = '/home/voidpanelc091/voidpanel'
LOCAL_BASE = '/Users/rohan/Desktop/voidpanel'

print(f"Connecting to {HOST}...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)
    print("Connected successfully!")
    
    # 1. Ensure remote static directory exists
    stdin, stdout, stderr = ssh.exec_command(f"mkdir -p {REMOTE_BASE}/static/khatabook {REMOTE_BASE}/templates/voidonyx")
    print("Remote dir check output:", stdout.read().decode())
    
    sftp = ssh.open_sftp()
    
    # Upload template
    local_tpl = f"{LOCAL_BASE}/voidonyx_server/templates/khatabook_pricing.html"
    remote_tpl_1 = f"{REMOTE_BASE}/templates/khatabook_pricing.html"
    print(f"Uploading {local_tpl} -> {remote_tpl_1}")
    sftp.put(local_tpl, remote_tpl_1)
    
    # Also put in templates/voidonyx/ if needed
    try:
        sftp.put(local_tpl, f"{REMOTE_BASE}/templates/voidonyx/khatabook_pricing.html")
    except Exception as e:
        print("Note on voidonyx subfolder:", e)
        
    # Upload static images
    local_img_dir = f"{LOCAL_BASE}/voidonyx_server/static/khatabook"
    for fname in os.listdir(local_img_dir):
        l_path = os.path.join(local_img_dir, fname)
        if os.path.isfile(l_path):
            r_path = f"{REMOTE_BASE}/static/khatabook/{fname}"
            print(f"Uploading image: {fname} -> {r_path}")
            sftp.put(l_path, r_path)
            
    sftp.close()
    
    # Trigger uWSGI / server reload
    print("Reloading server...")
    stdin, stdout, stderr = ssh.exec_command(f"touch {REMOTE_BASE}/voidpanel/wsgi.py && pkill -HUP -f 'voidpanel.ini' 2>/dev/null || true")
    print(stdout.read().decode())
    
    ssh.close()
    print("DEPLOYMENT SUCCESSFUL!")
except Exception as e:
    print("DEPLOYMENT ERROR:", e)
