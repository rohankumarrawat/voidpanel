#!/usr/bin/env python3
"""
VoidOnyx Tools Platform — Detailed MERN project analysis
"""
import paramiko, os

HOST = 'fast.voidpanel.com'
PORT = 22
USER = 'root'
PASS = os.environ.get('VP_PASS', '')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=20)

def run(cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=15)
    return stdout.read().decode('utf-8', errors='replace').strip()

print("=== MERN Project Details ===\n")

# 1. Full directory listing
print("── Directory structure ──")
print(run("ls -la /home/voidonyx/voidtools/"))
print()
print(run("ls -la /home/voidonyx/voidtools/backend/"))

# 2. Backend .env
print("\n── backend/.env ──")
print(run("cat /home/voidonyx/voidtools/backend/.env 2>/dev/null || echo 'NOT FOUND'"))

# 3. Backend ecosystem config
print("\n── ecosystem.config.js ──")
print(run("cat /home/voidonyx/voidtools/backend/ecosystem.config.js 2>/dev/null || echo 'NOT FOUND'"))

# 4. PM2 full info
print("\n── PM2 voidtools info ──")
print(run("pm2 show voidtools 2>/dev/null | head -30"))

# 5. Nginx config for tools.voidonyx.in
print("\n── Nginx vhost config ──")
print(run("cat /etc/nginx/sites-available/tools.voidonyx.in.conf 2>/dev/null || echo 'NOT FOUND'"))

# 6. What's in public_html/tools
print("\n── /home/voidonyx/public_html/tools/ ──")
print(run("ls -la /home/voidonyx/public_html/tools/ 2>/dev/null | head -15"))

# 7. Check what port the MERN backend is on
print("\n── Listening ports for voidtools process ──")
print(run("pm2 pid voidtools 2>/dev/null"))
pid = run("pm2 pid voidtools 2>/dev/null").strip()
if pid:
    print(run(f"ss -tlnp | grep {pid} 2>/dev/null || echo 'No port found for PID {pid}'"))

# 8. Check frontend/build existence
print("\n── Frontend build ──")
print(run("ls -la /home/voidonyx/voidtools/frontend/build/ 2>/dev/null | head -5 || echo 'NOT FOUND'"))

ssh.close()
print("\n=== DONE ===")
