import paramiko, os

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)
sftp = ssh.open_sftp()

# 1. Upload control/views.py
local_views = '/Users/rohan/Desktop/voidpanel/control/views.py'
remote_views = '/var/www/panel/control/views.py'
print(f'Uploading control/views.py ({os.path.getsize(local_views)} bytes)...')
sftp.put(local_views, remote_views)
print('  -> Uploaded control/views.py')

# 2. Upload relay views.py
local_relay = '/Users/rohan/Desktop/voidpanel/website/voidpanel/voidpanel/views.py'
remote_relay = '/home/voidonyx/voidonyx/voidpanel/views.py'
print(f'Uploading relay views.py ({os.path.getsize(local_relay)} bytes)...')
sftp.put(local_relay, remote_relay)
print('  -> Uploaded relay views.py')

sftp.close()

# 3. Restart services
stdin, stdout, stderr = ssh.exec_command('systemctl restart voidpanel.service app-voidonyx-voidonyx.service')
stdout.read()

stdin, stdout, stderr = ssh.exec_command('systemctl is-active voidpanel.service app-voidonyx-voidonyx.service')
print('Services status:\n', stdout.read().decode())

ssh.close()
