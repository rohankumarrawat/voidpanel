import paramiko

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)

# Check both debug log files
print('=== PANEL DEBUG LOG ===')
stdin, stdout, stderr = ssh.exec_command('cat /tmp/fb_callback_debug.log 2>/dev/null || echo "(no file)"')
print(stdout.read().decode())

print('=== RELAY DEBUG LOG ===')
stdin, stdout, stderr = ssh.exec_command('cat /tmp/fb_relay_callback_debug.log 2>/dev/null || echo "(no file)"')
print(stdout.read().decode())

ssh.close()
