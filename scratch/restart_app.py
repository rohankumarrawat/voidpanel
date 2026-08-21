import paramiko

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)

stdin, stdout, stderr = ssh.exec_command("systemctl restart app-voidonyx-voidonyx.service && systemctl restart app-voidpanelc091-voidpanel.service && systemctl status app-voidonyx-voidonyx.service")
print("=== SERVICE RESTART STATUS ===")
print(stdout.read().decode())

ssh.close()
