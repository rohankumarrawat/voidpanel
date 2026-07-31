#!/usr/bin/env python3
import paramiko

HOST = '207.180.209.216'
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=22, username='root', password='19072002ROHANkumar!', timeout=15)

def run(cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=30)
    return stdout.read().decode('utf-8', errors='replace').strip()

# Find the uwsgi ini config to see where logs go
print("=== UWSGI CONFIG ===")
print(run("cat /var/www/panel/panel.ini"))

print("\n=== FIND LOG FILES ===")
print(run("find /var/www/panel -name '*.log' -mmin -30 2>/dev/null | head -10"))
print(run("find /var/log -name '*uwsgi*' -o -name '*panel*' 2>/dev/null | head -10"))

# Check if there's a daemonize log
print("\n=== UWSGI DAEMONIZE LOG ===")
ini = run("grep -i 'daemonize\|logto\|log-to' /var/www/panel/panel.ini 2>/dev/null")
print(ini if ini else "No log directive found in panel.ini")

# Try to find the actual error via Django manage.py check
print("\n=== DJANGO CHECK ===")
print(run("cd /var/www/panel && /var/www/panel/venv/bin/python manage.py check 2>&1 | tail -20"))

# Try to reproduce the error
print("\n=== DJANGO SHELL TEST ===")
print(run("cd /var/www/panel && /var/www/panel/venv/bin/python manage.py shell -c \"from control.views import subdomain; print('OK')\" 2>&1"))

ssh.close()
