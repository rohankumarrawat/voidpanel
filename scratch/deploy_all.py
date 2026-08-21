import paramiko, os

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'
LOCAL_DIR = '/Users/rohan/Desktop/voidpanel'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
import time
connected = False
for attempt in range(5):
    try:
        ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=20)
        connected = True
        break
    except Exception as e:
        print(f"Connection attempt {attempt+1} failed: {e}. Retrying in 2s...")
        time.sleep(2)

if not connected:
    raise RuntimeError("Could not connect to SSH after 5 attempts")

sftp = ssh.open_sftp()

# Deploy social_portal.html
local_template = os.path.join(LOCAL_DIR, 'templates/control/social_portal.html')
size = os.path.getsize(local_template)
print(f'Uploading social_portal.html ({size} bytes)...')
for remote_template in [
    '/var/www/panel/templates/control/social_portal.html',
    '/var/www/panel/templates/control/social.html',
    '/var/www/panel/control/templates/control/social_portal.html',
    '/var/www/panel/control/templates/control/social.html',
    '/var/www/panel/website/voidpanel/templates/control/social_portal.html',
    '/var/www/panel/website/voidpanel/templates/control/social.html',
]:
    try:
        sftp.put(local_template, remote_template)
    except Exception as e:
        pass
print('  -> Done')

# Deploy views.py
local_views = os.path.join(LOCAL_DIR, 'control/views.py')
remote_views = '/var/www/panel/control/views.py'
size = os.path.getsize(local_views)
print(f'Uploading views.py ({size} bytes)...')
sftp.put(local_views, remote_views)
print('  -> Done')

# Deploy models.py
local_models = os.path.join(LOCAL_DIR, 'control/models.py')
remote_models = '/var/www/panel/control/models.py'
size = os.path.getsize(local_models)
print(f'Uploading models.py ({size} bytes)...')
sftp.put(local_models, remote_models)
print('  -> Done')

# Deploy urls.py
local_urls = os.path.join(LOCAL_DIR, 'control/urls.py')
remote_urls = '/var/www/panel/control/urls.py'
size = os.path.getsize(local_urls)
print(f'Uploading urls.py ({size} bytes)...')
sftp.put(local_urls, remote_urls)
print('  -> Done')

sftp.close()

# Restart service
stdin, stdout, stderr = ssh.exec_command('systemctl restart voidpanel && sleep 1 && systemctl is-active voidpanel')
status = stdout.read().decode().strip()
print(f'Status: {status}')
if status == 'active':
    print('Ready — please refresh the portal')
else:
    err = stderr.read().decode()
    print(f'Error: {err[:500]}')

ssh.close()
