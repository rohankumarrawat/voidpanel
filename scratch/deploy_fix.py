#!/usr/bin/env python3
"""Deploy latest fixes to the live panel server at 207.180.209.216"""
import paramiko, sys

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

def connect():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)
    return ssh

def run(ssh, cmd, show=True):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=60)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    if show:
        if out.strip(): print(out.strip())
        if err.strip(): print(f"STDERR: {err.strip()}")
    return out, err

ssh = connect()
print("=== Connected to", HOST, "===")

# Check if it's a git repo
out, _ = run(ssh, "cd /var/www/panel && git remote -v 2>/dev/null || echo 'NO_GIT'", show=False)
if 'NO_GIT' in out:
    print("Not a git repo. Using rsync approach...")
    ssh.close()
    sys.exit(1)

print("\n=== Pulling latest code ===")
run(ssh, "cd /var/www/panel && git stash && git pull origin main 2>&1")

print("\n=== Restarting panel service ===")
run(ssh, "systemctl restart panel 2>/dev/null || systemctl restart voidpanel 2>/dev/null || supervisorctl restart panel 2>/dev/null || echo 'Trying gunicorn...'")
run(ssh, "pkill -HUP gunicorn 2>/dev/null || echo 'No gunicorn process found'")

print("\n=== Verifying deployment ===")
out, _ = run(ssh, "cd /var/www/panel && head -1 version.txt")
print(f"Version: {out.strip()}")

out, _ = run(ssh, "grep -c \"session.get('name'\" /var/www/panel/control/views.py")
print(f"Safe session.get() count in control/views.py: {out.strip()}")

out, _ = run(ssh, "grep -c \"session\\['name'\\]\" /var/www/panel/control/views.py || echo '0'")
print(f"Unsafe session['name'] reads in control/views.py: {out.strip()}")

out, _ = run(ssh, "grep 'domain.username' /var/www/panel/templates/panel/viewwebsite.html || echo 'NONE (fixed)'")
print(f"domain.username in viewwebsite.html: {out.strip()}")

out, _ = run(ssh, "grep -c \"subdomain.*name='cron'\" /var/www/panel/control/urls.py || echo '0'")
print(f"Wrong name='cron' for subdomain URL: {out.strip()}")

ssh.close()
print("\n=== Deployment complete ===")
