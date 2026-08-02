#!/usr/bin/env python3
"""Force deploy: clean untracked conflicts and force pull"""
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

# Remove conflicting untracked files
print("=== Removing conflicting untracked files ===")
run("cd /var/www/panel && rm -f run_release_via_paramiko.py run_via_paramiko.py")
run("cd /var/www/panel && rm -f scratch/check_reseller_license.py scratch/check_tarball.py scratch/check_uwsgi_status.py scratch/check_version_files.py")

# Force reset to origin/main
print("=== Force resetting to origin/main ===")
out, err = run("cd /var/www/panel && git fetch origin main && git reset --hard origin/main 2>&1")
print(out or err)

# Verify critical files
print("\n=== Verifying critical imports ===")
out, _ = run("grep -c 'def get_web_user' /var/www/panel/voidplatform/config.py")
print(f"get_web_user in config.py: {out}")

out, _ = run("grep -c 'SessionNameFallbackMiddleware' /var/www/panel/panel/middleware.py")
print(f"SessionNameFallbackMiddleware in middleware.py: {out}")

out, _ = run("grep -c 'def get_active_zone_file_path' /var/www/panel/function.py")
print(f"get_active_zone_file_path in function.py: {out}")

# Django check
print("\n=== Django check ===")
out, _ = run("cd /var/www/panel && /var/www/panel/venv/bin/python manage.py check 2>&1 | tail -5")
print(out)

# Restart
print("\n=== Restarting voidpanel ===")
run("systemctl restart voidpanel")
time.sleep(3)
out, _ = run("systemctl is-active voidpanel")
print(f"Service: {out}")

# Check uwsgi log
print("\n=== Recent uWSGI log ===")
out, _ = run("tail -10 /var/log/voidpanel_uwsgi.log")
print(out)

ssh.close()
print("\n=== Done ===")
