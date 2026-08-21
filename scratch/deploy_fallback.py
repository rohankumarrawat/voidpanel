import paramiko, os

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)
sftp = ssh.open_sftp()

local_views = '/Users/rohan/Desktop/voidpanel/control/views.py'
remote_views = '/var/www/panel/control/views.py'
sftp.put(local_views, remote_views)
print('Uploaded control/views.py')
sftp.close()

# Clear old logs
ssh.exec_command('rm -f /tmp/fb_callback_debug.log /tmp/fb_user_token.txt')

# Restart
stdin, stdout, stderr = ssh.exec_command('systemctl restart voidpanel.service')
stdout.read()
stdin, stdout, stderr = ssh.exec_command('systemctl is-active voidpanel.service')
print('Status:', stdout.read().decode().strip())

ssh.close()
print('Ready - please reconnect Facebook')
