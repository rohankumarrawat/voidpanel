import paramiko, os

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)
sftp = ssh.open_sftp()

# Upload social_portal.html template
local_tmpl = '/Users/rohan/Desktop/voidpanel/templates/control/social_portal.html'
remote_tmpl = '/var/www/panel/templates/control/social_portal.html'
print('Uploading social_portal.html (%d bytes)...' % os.path.getsize(local_tmpl))
sftp.put(local_tmpl, remote_tmpl)
print('  -> Done')

sftp.close()

# Restart service
stdin, stdout, stderr = ssh.exec_command('systemctl restart voidpanel && systemctl is-active voidpanel')
status = stdout.read().decode().strip()
print('Status:', status)
print('Ready — please refresh the portal')
ssh.close()
