import paramiko

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)

# Check recent nginx / uwsgi access logs
stdin, stdout, stderr = ssh.exec_command('tail -n 30 /var/log/nginx/access.log 2>/dev/null || tail -n 30 /var/log/nginx/voidpanel.access.log 2>/dev/null')
print("Nginx access logs:\n", stdout.read().decode())

# Check journalctl for voidpanel
stdin, stdout, stderr = ssh.exec_command('journalctl -u voidpanel.service -n 25 --no-pager')
print("Voidpanel journal logs:\n", stdout.read().decode())

ssh.close()
