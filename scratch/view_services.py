import paramiko

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)

commands = [
    "systemctl cat app-voidonyx-voidonyx.service",
    "systemctl cat app-voidpanelc091-voidpanel.service",
]

for c in commands:
    print(f"=== {c} ===")
    stdin, stdout, stderr = ssh.exec_command(c)
    print(stdout.read().decode().strip())

ssh.close()
