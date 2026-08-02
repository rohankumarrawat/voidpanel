#!/usr/bin/env python3
"""Deploy subdomain fix to live server"""
import paramiko, time

HOST = '207.180.209.216'
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=22, username='root', password='19072002ROHANkumar!', timeout=15)

def run(cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=60)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    return out, err

print("=== Pull latest ===")
out, err = run("cd /var/www/panel && git pull origin main 2>&1")
print(out or err)

print("\n=== Django check ===")
out, _ = run("cd /var/www/panel && /var/www/panel/venv/bin/python manage.py check 2>&1 | tail -3")
print(out)

print("\n=== Restart ===")
run("systemctl restart voidpanel")
time.sleep(3)
out, _ = run("systemctl is-active voidpanel")
print(f"Service: {out}")

print("\n=== uWSGI app loaded? ===")
out, _ = run("tail -5 /var/log/voidpanel_uwsgi.log")
print(out)

ssh.close()
print("\n=== Done ===")
