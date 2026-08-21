import paramiko, os

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)

# Check common paths
paths_to_check = [
    '/home/voidonyx/voidonyx/website/voidpanel/voidpanel/views.py',
    '/home/voidonyx/website/voidpanel/voidpanel/views.py',
    '/home/voidonyx/voidpanel/website/voidpanel/voidpanel/views.py',
    '/var/www/voidonyx/website/voidpanel/voidpanel/views.py',
]

for p in paths_to_check:
    stdin, stdout, stderr = ssh.exec_command(f'ls -la {p} 2>&1')
    out = stdout.read().decode().strip()
    print(f'{p}: {out}')

# Also check the service config
stdin, stdout, stderr = ssh.exec_command('systemctl show app-voidonyx-voidonyx.service -p WorkingDirectory,ExecStart 2>/dev/null')
print('\nService config:', stdout.read().decode().strip())

# List home/voidonyx top-level
stdin, stdout, stderr = ssh.exec_command('ls -la /home/voidonyx/ 2>&1 | head -20')
print('\n/home/voidonyx/:', stdout.read().decode().strip())

ssh.close()
