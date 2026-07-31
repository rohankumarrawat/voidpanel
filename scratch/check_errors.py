#!/usr/bin/env python3
import paramiko

HOST = '207.180.209.216'
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=22, username='root', password='19072002ROHANkumar!', timeout=15)

def run(cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=30)
    return stdout.read().decode('utf-8', errors='replace').strip()

# Check uWSGI logs
print("=== UWSGI ERROR LOG (last 50 lines) ===")
print(run("tail -50 /var/log/uwsgi/panel.log 2>/dev/null || tail -50 /var/www/panel/uwsgi.log 2>/dev/null || echo 'No uwsgi log found'"))

print("\n=== CHECKING OTHER LOG LOCATIONS ===")
print(run("ls -la /var/log/uwsgi/ 2>/dev/null; ls -la /var/www/panel/*.log 2>/dev/null"))

print("\n=== NGINX ERROR LOG (last 20 lines) ===")
print(run("tail -20 /var/log/nginx/error.log 2>/dev/null"))

print("\n=== JOURNAL LOG (last 30 lines) ===")
print(run("journalctl -u voidpanel --no-pager -n 30 2>/dev/null"))

print("\n=== GIT STATUS ===")
print(run("cd /var/www/panel && git log --oneline -3"))

print("\n=== PYTHON SYNTAX CHECK ===")
print(run("cd /var/www/panel && /var/www/panel/venv/bin/python -c 'import control.views' 2>&1"))

ssh.close()
