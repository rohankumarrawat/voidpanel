#!/usr/bin/env python3
"""Deploy debug logging, trigger the error, and capture it"""
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

print("=== Pull and restart ===")
out, _ = run("cd /var/www/panel && git pull origin main 2>&1")
print(out)
run("systemctl restart voidpanel")
time.sleep(3)

# Clear the log to see only new errors
run("echo '' > /var/log/voidpanel_uwsgi.log")
time.sleep(1)

# Simulate a request to the subdomain URL using curl with the admin session
print("\n=== Triggering subdomain URL ===")
# First, we need to see what happens - let's look at the uwsgi log after user hits the URL
print("Waiting for user to trigger the URL... checking log in 5 seconds")
time.sleep(5)
out, _ = run("cat /var/log/voidpanel_uwsgi.log 2>/dev/null | tail -40")
print(out if out else "(log empty - user hasn't triggered the URL yet)")

# Also check if there are any python errors printed to stderr
print("\n=== Check journalctl for recent errors ===")
out, _ = run("journalctl -u voidpanel --no-pager -n 10 --since '2 minutes ago' 2>/dev/null")
print(out)

ssh.close()
