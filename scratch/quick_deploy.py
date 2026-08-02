#!/usr/bin/env python3
"""Deploy resilient subdomain fix"""
import paramiko, time

HOST = '207.180.209.216'
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=22, username='root', password='19072002ROHANkumar!', timeout=15)

def run(cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=60)
    return stdout.read().decode('utf-8', errors='replace').strip()

print("=== Pull ===")
print(run("cd /var/www/panel && git pull origin main 2>&1"))

print("\n=== Django check ===")
print(run("cd /var/www/panel && /var/www/panel/venv/bin/python manage.py check 2>&1 | tail -3"))

print("\n=== Restart ===")
run("systemctl restart voidpanel")
time.sleep(3)
print(f"Service: {run('systemctl is-active voidpanel')}")
print(run("tail -3 /var/log/voidpanel_uwsgi.log"))

ssh.close()
print("\n=== Done ===")
