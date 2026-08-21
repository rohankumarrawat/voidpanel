import paramiko

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)

# Check recent Pinterest callback hits
stdin, stdout, stderr = ssh.exec_command('grep -i "pinterest\\|callback.*pi" /var/log/nginx/access.log | tail -20')
print("=== Nginx access log (Pinterest) ===")
print(stdout.read().decode())

# Check uwsgi / django error logs
stdin, stdout, stderr = ssh.exec_command('find /var/www/panel -name "*.log" -newer /var/www/panel/panel.sock 2>/dev/null | head -5')
print("=== Recent log files ===")
print(stdout.read().decode())

stdin, stdout, stderr = ssh.exec_command('journalctl -u uwsgi -n 50 --no-pager 2>&1 | tail -30')
print("=== uwsgi journal ===")
print(stdout.read().decode())

# Check for django error logs
stdin, stdout, stderr = ssh.exec_command('find /var/www/panel -name "django*.log" -o -name "error*.log" 2>/dev/null')
print("=== Django log files ===")
print(stdout.read().decode())

stdin, stdout, stderr = ssh.exec_command('ls -la /var/www/panel/logs/ 2>/dev/null || echo "no logs dir"')
print("=== Panel logs dir ===")
print(stdout.read().decode())

# Check settings for LOG config
stdin, stdout, stderr = ssh.exec_command('grep -r "LOGGING" /var/www/panel/panel/settings.py 2>/dev/null | head -5')
print("=== LOGGING in settings ===")
print(stdout.read().decode())

ssh.close()
