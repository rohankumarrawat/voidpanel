#!/usr/bin/env python3
"""Fix the function.py import error on the live server by force-updating it"""
import paramiko

HOST = '207.180.209.216'
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=22, username='root', password='19072002ROHANkumar!', timeout=15)

def run(cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=60)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    return out, err

# Check if function.py has the missing functions
print("=== Checking function.py on server ===")
out, _ = run("grep -c 'def get_active_zone_file_path' /var/www/panel/function.py || echo 'MISSING'")
print(f"get_active_zone_file_path: {out}")

out, _ = run("grep -c 'def format_dns_data' /var/www/panel/function.py || echo 'MISSING'")
print(f"format_dns_data: {out}")

out, _ = run("grep -c 'def update_soa_serial_in_content' /var/www/panel/function.py || echo 'MISSING'")
print(f"update_soa_serial_in_content: {out}")

out, _ = run("grep -c 'def fix_zone_file_permissions' /var/www/panel/function.py || echo 'MISSING'")
print(f"fix_zone_file_permissions: {out}")

# Check git status of function.py
print("\n=== Git status of function.py ===")
out, _ = run("cd /var/www/panel && git status function.py")
print(out)

# Force checkout function.py from the latest commit
print("\n=== Force updating function.py from git ===")
out, err = run("cd /var/www/panel && git checkout origin/main -- function.py 2>&1")
print(out or err or "OK")

# Verify the fix
print("\n=== Verifying function.py now has the functions ===")
out, _ = run("grep -c 'def get_active_zone_file_path' /var/www/panel/function.py || echo 'STILL MISSING'")
print(f"get_active_zone_file_path: {out}")

# Django check
print("\n=== Django check ===")
out, _ = run("cd /var/www/panel && /var/www/panel/venv/bin/python manage.py check 2>&1 | tail -5")
print(out)

# Restart service
print("\n=== Restarting voidpanel ===")
run("systemctl restart voidpanel")
import time; time.sleep(2)
out, _ = run("systemctl is-active voidpanel")
print(f"Service: {out}")

ssh.close()
print("\n=== Done ===")
