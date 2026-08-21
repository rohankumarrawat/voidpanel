import paramiko

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)

stdin, stdout, stderr = ssh.exec_command("curl -k -H 'Host: voidonyx.in' https://127.0.0.1/khatabook/ | head -n 45")
print("=== LIVE SERVER RESPONSE ===")
print(stdout.read().decode())

ssh.close()
