import paramiko
HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)

sftp = ssh.open_sftp()
sftp.get('/var/www/panel/control/views.py', '/Users/rohan/Desktop/voidpanel/control/views.py')
sftp.close()
print('Downloaded views.py from server')
ssh.close()
