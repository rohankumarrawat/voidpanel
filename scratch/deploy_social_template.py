import paramiko, os

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)
sftp = ssh.open_sftp()

local_tmpl = '/Users/rohan/Desktop/voidpanel/templates/control/social_portal.html'
remote_tmpl = '/var/www/panel/templates/control/social_portal.html'

print(f'Uploading social_portal.html ({os.path.getsize(local_tmpl)} bytes)...')
sftp.put(local_tmpl, remote_tmpl)
print('  -> Uploaded successfully.')

sftp.close()

stdin, stdout, stderr = ssh.exec_command('systemctl restart voidpanel.service')
stdout.read()

stdin, stdout, stderr = ssh.exec_command('systemctl is-active voidpanel.service')
print('voidpanel.service status:', stdout.read().decode().strip())

ssh.close()
