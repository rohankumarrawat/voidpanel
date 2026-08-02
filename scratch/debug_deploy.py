#!/usr/bin/env python3
"""Check what serves port 443 and fix the panel URL"""
import paramiko

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)

def run(cmd, show=True):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=120)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    if show:
        if out.strip(): print(out.strip())
        if err.strip(): print(f"STDERR: {err.strip()}")
    return out, err

print("=== 1. What listens on port 443 ===")
run("ss -tlnp | grep ':443'")

print("\n=== 2. What listens on port 8082 ===")
run("ss -tlnp | grep ':8082'")

print("\n=== 3. What listens on port 8080 ===")
run("ss -tlnp | grep ':8080'")

print("\n=== 4. Test on port 8082 (the real HTTPS panel port) ===")
run('curl -sk -X POST https://127.0.0.1:8082/api/v1/auth/login/ -H "Content-Type: application/json" -d \'{"username":"test","password":"test"}\' 2>&1 | head -5')

print("\n=== 5. Test on port 8080 (HTTP panel port) ===")
run('curl -s -X POST http://127.0.0.1:8080/api/v1/auth/login/ -H "Content-Type: application/json" -d \'{"username":"test","password":"test"}\' 2>&1 | head -5')

print("\n=== 6. Default 443 nginx config ===")
run("grep -rl 'listen.*443' /etc/nginx/sites-enabled/ 2>/dev/null")
run("grep -rl 'listen.*443' /etc/nginx/conf.d/ 2>/dev/null")

ssh.close()
print("\n=== Done ===")
