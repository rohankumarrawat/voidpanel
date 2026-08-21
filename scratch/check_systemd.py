import paramiko

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)

commands = [
    "systemctl list-unit-files | grep -E 'void|uwsgi|gunicorn'",
    "systemctl cat voidonyx 2>/dev/null || true",
    "systemctl cat voidpanel 2>/dev/null || true",
    "ls -d /home/*/venv /home/*/.venv 2>/dev/null || true",
]

for c in commands:
    print(f"=== {c} ===")
    stdin, stdout, stderr = ssh.exec_command(c)
    print(stdout.read().decode().strip())

ssh.close()
