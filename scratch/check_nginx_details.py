import paramiko

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)

# Check nginx config for 8082 or fast.voidpanel.com
stdin, stdout, stderr = ssh.exec_command('grep -rn "8082" /etc/nginx/ 2>&1')
print('Nginx 8082 search:\n', stdout.read().decode())

stdin, stdout, stderr = ssh.exec_command('cat /etc/nginx/sites-enabled/voidpanel.com.conf 2>&1')
print('voidpanel.com.conf:\n', stdout.read().decode())

ssh.close()
