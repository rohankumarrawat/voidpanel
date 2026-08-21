import paramiko

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)

# Find all python binaries in venvs
stdin, stdout, stderr = ssh.exec_command("find /home /var/www /root -name 'python3' -path '*/bin/python3' 2>/dev/null")
venvs = [l.strip() for l in stdout.read().decode().splitlines() if l.strip()]
print("Found Python virtual environments:\n", "\n".join(venvs))

# Check uwsgi processes to see which python/virtualenv they use
stdin, stdout, stderr = ssh.exec_command("ps aux | grep -E 'uwsgi|gunicorn' | grep -v grep")
print("\nRunning uwsgi/gunicorn processes:\n", stdout.read().decode())

ssh.close()
