import paramiko

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)

# Verify public endpoint
stdin, stdout, stderr = ssh.exec_command("curl -s http://127.0.0.1:8000/api/social/platform-config/ 2>/dev/null || curl -s https://voidonyx.in/api/social/platform-config/ || curl -s https://voidpanel.com/api/social/platform-config/")
print("Platform Config API Response:\n", stdout.read().decode())

ssh.close()
