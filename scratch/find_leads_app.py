#!/usr/bin/env python3
"""Deploy Lead Generator API changes to the live server at 207.180.209.216"""
import paramiko, sys, os

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

LOCAL_BASE = '/Users/rohan/Desktop/LEads'

def connect():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)
    return ssh

def run(ssh, cmd, show=True):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=120)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    if show:
        if out.strip(): print(out.strip())
        if err.strip(): print(f"STDERR: {err.strip()}")
    return out, err

def main():
    ssh = connect()
    print("✅ Connected to server")
    
    # Find the Leads app directory
    out, _ = run(ssh, "find / -name 'manage.py' -path '*/voidonyx*' 2>/dev/null | head -5")
    if not out.strip():
        out, _ = run(ssh, "find /var/www /home /opt -name 'manage.py' 2>/dev/null | head -10")
    print(f"\nmanage.py locations:\n{out}")
    
    # Check for leads-related dirs
    out, _ = run(ssh, "find / -maxdepth 4 -type d -name 'leads' 2>/dev/null | head -10")
    print(f"\nleads directories:\n{out}")
    
    # Check nginx configs for leads
    out, _ = run(ssh, "grep -rl 'leads' /etc/nginx/ 2>/dev/null | head -5")
    print(f"\nnginx configs with 'leads':\n{out}")
    
    if out.strip():
        for conf in out.strip().split('\n'):
            if conf.strip():
                print(f"\n--- {conf} ---")
                o, _ = run(ssh, f"cat {conf.strip()}")
    
    ssh.close()

if __name__ == '__main__':
    main()
