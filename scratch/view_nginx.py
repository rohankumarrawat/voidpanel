import paramiko

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)

stdin, stdout, stderr = ssh.exec_command("cat /etc/nginx/sites-available/voidonyx.in.conf")
print(stdout.read().decode())

ssh.close()
