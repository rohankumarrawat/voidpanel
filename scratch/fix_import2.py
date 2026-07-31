#!/usr/bin/env python3
"""Pull function.py fix and restart"""
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

print("=== Pulling latest (with function.py) ===")
out, err = run("cd /var/www/panel && git pull origin main 2>&1")
print(out or err)

print("\n=== Verifying function.py ===")
out, _ = run("grep -c 'def get_active_zone_file_path' /var/www/panel/function.py")
print(f"get_active_zone_file_path found: {out}")

print("\n=== Django check ===")
out, _ = run("cd /var/www/panel && /var/www/panel/venv/bin/python manage.py check 2>&1 | tail -3")
print(out)

print("\n=== Restarting voidpanel ===")
run("systemctl restart voidpanel")
time.sleep(2)
out, _ = run("systemctl is-active voidpanel")
print(f"Service: {out}")

# Quick curl test
out, _ = run("curl -s -o /dev/null -w '%{http_code}' http://localhost:8080/ 2>/dev/null || echo 'no local test'")
print(f"HTTP status: {out}")

ssh.close()
print("\n=== Done ===")
