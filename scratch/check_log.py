#!/usr/bin/env python3
"""Check uwsgi log for the subdomain error traceback"""
import paramiko

HOST = '207.180.209.216'
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=22, username='root', password='19072002ROHANkumar!', timeout=15)

def run(cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=30)
    return stdout.read().decode('utf-8', errors='replace').strip()

# Check the uwsgi log for any traceback or subdomain error
print("=== Full uWSGI log ===")
print(run("cat /var/log/voidpanel_uwsgi.log 2>/dev/null | tail -60"))

print("\n=== Grep for subdomain error ===")
print(run("grep -i 'subdomain\\|traceback\\|error' /var/log/voidpanel_uwsgi.log 2>/dev/null | tail -20"))

ssh.close()
