import paramiko

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)

stdin, stdout, stderr = ssh.exec_command('grep -rn "server_name.*fast.voidpanel" /etc/nginx/ 2>&1')
print("=== Nginx server blocks for fast.voidpanel ===")
print(stdout.read().decode())

stdin, stdout, stderr = ssh.exec_command('netstat -tlpn | grep nginx 2>&1 || ss -tlpn | grep nginx 2>&1')
print("=== Nginx listening ports ===")
print(stdout.read().decode())

ssh.close()
