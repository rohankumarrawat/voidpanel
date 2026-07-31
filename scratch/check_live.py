#!/usr/bin/env python3
"""Check the remaining unsafe session access on the live server"""
import paramiko

HOST = '207.180.209.216'
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=22, username='root', password='19072002ROHANkumar!', timeout=15)

stdin, stdout, stderr = ssh.exec_command("grep -n \"session\\['name'\\]\" /var/www/panel/control/views.py")
out = stdout.read().decode()
print("Remaining unsafe session reads in control/views.py:")
print(out if out.strip() else "NONE")

stdin, stdout, stderr = ssh.exec_command("grep -n \"session\\['name'\\]\" /var/www/panel/panel/views.py | head -20")
out = stdout.read().decode()
print("\nRemaining session reads in panel/views.py:")
print(out if out.strip() else "NONE")

# Check the panel service status
stdin, stdout, stderr = ssh.exec_command("systemctl is-active panel 2>/dev/null || systemctl is-active voidpanel 2>/dev/null || echo 'checking gunicorn'; pgrep -a gunicorn | head -3")
out = stdout.read().decode()
print("\nService status:")
print(out.strip())

ssh.close()
