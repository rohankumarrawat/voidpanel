#!/usr/bin/env python3
"""
VoidOnyx Tools Platform — Production Deployment
Deploys server + client to fast.voidpanel.com

Server state (from analysis):
  - MERN project dir: /home/voidonyx/voidtools/
  - Backend port: 3002
  - PM2 process: voidtools
  - Nginx root: /home/voidonyx/voidtools/frontend/build
  - API proxy: /api/ → 127.0.0.1:3002
  - MongoDB: mongodb://localhost:27017/voidtools_db
"""

import paramiko, os, stat, sys

HOST = 'fast.voidpanel.com'
PORT = 22
USER = 'root'
PASS = os.environ.get('VP_PASS', '')

LOCAL_SERVER_DIST  = '/Users/rohan/Desktop/voidpanel/tools-platform/server/dist'
LOCAL_SERVER_SRC   = '/Users/rohan/Desktop/voidpanel/tools-platform/server/src'
LOCAL_SERVER_PKG   = '/Users/rohan/Desktop/voidpanel/tools-platform/server/package.json'
LOCAL_SERVER_TSCONF = '/Users/rohan/Desktop/voidpanel/tools-platform/server/tsconfig.json'
LOCAL_CLIENT_DIST  = '/Users/rohan/Desktop/voidpanel/tools-platform/client/dist'

REMOTE_BACKEND     = '/home/voidonyx/voidtools/backend'
REMOTE_FRONTEND    = '/home/voidonyx/voidtools/frontend/build'

def connect():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=20)
    return ssh

def run(ssh, cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=60)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    return out, err

def upload_tree(sftp, local_dir, remote_dir):
    """Recursively upload a directory tree"""
    for item in os.listdir(local_dir):
        local_path = os.path.join(local_dir, item)
        remote_path = f"{remote_dir}/{item}"
        
        if os.path.isdir(local_path):
            # Skip node_modules
            if item == 'node_modules' or item == '.git':
                continue
            try:
                sftp.stat(remote_path)
            except FileNotFoundError:
                sftp.mkdir(remote_path)
            upload_tree(sftp, local_path, remote_path)
        else:
            print(f"    ↑ {item}")
            sftp.put(local_path, remote_path)

def upload_file(sftp, local, remote):
    name = os.path.basename(local)
    print(f"    ↑ {name} → {remote}")
    sftp.put(local, remote)


print("=== VoidOnyx Tools Platform — Deployment ===\n")

ssh = connect()
sftp = ssh.open_sftp()
print(f"✓ Connected to {HOST}\n")

# ── Step 1: Stop PM2 process ──────────────────────────────────────────────
print("Step 1/6 — Stopping PM2 voidtools process...")
out, err = run(ssh, "pm2 stop voidtools 2>/dev/null || true")
print(f"  {out}\n")

# ── Step 2: Backup existing backend ──────────────────────────────────────
print("Step 2/6 — Backing up existing backend...")
out, _ = run(ssh, f"cp -r {REMOTE_BACKEND} {REMOTE_BACKEND}.bak.$(date +%s)")
print("  ✓ Backup created\n")

# ── Step 3: Deploy backend (compiled JS) ─────────────────────────────────
print("Step 3/6 — Deploying backend...")

# Create required directories
for d in ['dist', 'dist/config', 'dist/controllers', 'dist/middleware', 'dist/models', 'dist/routes', 'dist/services']:
    remote_d = f"{REMOTE_BACKEND}/{d}"
    try:
        sftp.stat(remote_d)
    except FileNotFoundError:
        sftp.mkdir(remote_d)
        print(f"  Created dir: {d}")

# Upload compiled dist files
print("  Uploading compiled backend (dist/)...")
upload_tree(sftp, LOCAL_SERVER_DIST, f"{REMOTE_BACKEND}/dist")

# Upload package.json (for npm install on server)
upload_file(sftp, LOCAL_SERVER_PKG, f"{REMOTE_BACKEND}/package.json")

# Create .env on server
env_content = """PORT=3002
MONGO_URI=mongodb://localhost:27017/voidtools_db
CORS_ORIGIN=https://tools.voidonyx.in
CACHE_TTL_SECONDS=300
RATE_LIMIT_MAX=30
RATE_LIMIT_WINDOW_MS=60000
IP_SALT=voidtools-production-salt-v1
NODE_ENV=production
"""
with sftp.open(f"{REMOTE_BACKEND}/.env", 'w') as f:
    f.write(env_content)
print("    ↑ .env (production)")

# Create updated ecosystem.config.js
ecosystem_content = """module.exports = {
  apps: [{
    name: "voidtools",
    script: "dist/server.js",
    cwd: "/home/voidonyx/voidtools/backend",
    env: {
      NODE_ENV: "production",
      MONGO_URI: "mongodb://localhost:27017/voidtools_db",
      PORT: 3002,
      CORS_ORIGIN: "https://tools.voidonyx.in",
      CACHE_TTL_SECONDS: 300,
      RATE_LIMIT_MAX: 30,
      RATE_LIMIT_WINDOW_MS: 60000,
      IP_SALT: "voidtools-production-salt-v1"
    }
  }]
};
"""
with sftp.open(f"{REMOTE_BACKEND}/ecosystem.config.js", 'w') as f:
    f.write(ecosystem_content)
print("    ↑ ecosystem.config.js")

# Install backend deps on server
print("  Installing backend npm dependencies...")
out, err = run(ssh, f"cd {REMOTE_BACKEND} && npm install --omit=dev 2>&1 | tail -3")
print(f"  {out}\n")

# ── Step 4: Deploy frontend (Vite build) ─────────────────────────────────
print("Step 4/6 — Deploying frontend...")

# Clear old frontend build
run(ssh, f"rm -rf {REMOTE_FRONTEND}/*")
run(ssh, f"mkdir -p {REMOTE_FRONTEND}/assets")

# Upload new Vite build
print("  Uploading React + Vite build...")
upload_tree(sftp, LOCAL_CLIENT_DIST, REMOTE_FRONTEND)
print("  ✓ Frontend deployed\n")

# ── Step 5: Fix permissions ──────────────────────────────────────────────
print("Step 5/6 — Fixing permissions...")
run(ssh, "chown -R voidonyx:www-data /home/voidonyx/voidtools/")
run(ssh, "chmod -R 750 /home/voidonyx/voidtools/")
print("  ✓ Permissions set (voidonyx:www-data)\n")

# ── Step 6: Restart PM2 ─────────────────────────────────────────────────
print("Step 6/6 — Starting PM2 voidtools process...")
# Delete old process and start fresh with new ecosystem config
out, _ = run(ssh, f"pm2 delete voidtools 2>/dev/null || true")
out, err = run(ssh, f"cd {REMOTE_BACKEND} && pm2 start ecosystem.config.js")
print(f"  {out}")
out, _ = run(ssh, "pm2 save")
print(f"  {out}")

# Wait and verify
import time
time.sleep(2)
print("\n  Verifying process status...")
out, _ = run(ssh, "pm2 list | grep voidtools")
print(f"  {out}")

# Check if port 3002 is listening
out, _ = run(ssh, "ss -tlnp | grep 3002")
print(f"  Port 3002: {out}")

# Quick API test
out, _ = run(ssh, "curl -s http://127.0.0.1:3002/api/ 2>/dev/null | head -1")
print(f"  API test: {out}")

sftp.close()
ssh.close()

print("\n=== DEPLOYMENT COMPLETE ===")
print("Live URL: https://tools.voidonyx.in")
print("API URL:  https://tools.voidonyx.in/api")
