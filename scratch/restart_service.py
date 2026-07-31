#!/usr/bin/env python3
"""Restart the voidpanel service on the live server"""
import paramiko, time

HOST = '207.180.209.216'
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=22, username='root', password='19072002ROHANkumar!', timeout=15)

def run(cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=30)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    return out.strip(), err.strip()

print("=== Restarting voidpanel service ===")
out, err = run("systemctl restart voidpanel 2>&1")
print(out or err or "OK")
time.sleep(2)

print("\n=== Checking service status ===")
out, _ = run("systemctl is-active voidpanel")
print(f"voidpanel: {out}")

out, _ = run("systemctl status voidpanel 2>&1 | tail -10")
print(out)

ssh.close()
print("\n=== Done ===")
