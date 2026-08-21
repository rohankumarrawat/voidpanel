import paramiko, os

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)
sftp = ssh.open_sftp()

# 1. Upload templates/control/social_portal.html
local_tmpl = '/Users/rohan/Desktop/voidpanel/templates/control/social_portal.html'
remote_tmpl = '/var/www/panel/templates/control/social_portal.html'
print('Uploading social_portal.html (' + str(os.path.getsize(local_tmpl)) + ' bytes)...')
sftp.put(local_tmpl, remote_tmpl)
print('  -> Uploaded social_portal.html')

# 2. Upload control/views.py
local_views = '/Users/rohan/Desktop/voidpanel/control/views.py'
remote_views = '/var/www/panel/control/views.py'
print('Uploading control/views.py (' + str(os.path.getsize(local_views)) + ' bytes)...')
sftp.put(local_views, remote_views)
print('  -> Uploaded control/views.py')

# 3. Upload relay views.py
local_relay = '/Users/rohan/Desktop/voidpanel/website/voidpanel/voidpanel/views.py'
remote_relay = '/home/voidonyx/voidonyx/voidpanel/views.py'
print('Uploading relay views.py (' + str(os.path.getsize(local_relay)) + ' bytes)...')
sftp.put(local_relay, remote_relay)
print('  -> Uploaded relay views.py')

sftp.close()

# 4. Restart services
stdin, stdout, stderr = ssh.exec_command('systemctl restart voidpanel.service app-voidonyx-voidonyx.service')
stdout.read()

stdin, stdout, stderr = ssh.exec_command('systemctl is-active voidpanel.service app-voidonyx-voidonyx.service')
print('Services status:\n' + stdout.read().decode())

ssh.close()
