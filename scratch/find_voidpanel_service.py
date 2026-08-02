#!/usr/bin/env python3
"""Find and restart the VoidPanel website service."""
import paramiko

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
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=120)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    if show:
        if out.strip(): print(out.strip())
        if err.strip(): print(f"  STDERR: {err.strip()}")
    return out, err

def main():
    ssh = connect()
    print("Connected\n")

    # Find all services
    print("── All voidpanel-related services ──")
    run(ssh, "systemctl list-units --type=service --all | grep -i 'panel\\|voidpanel'")
    
    print("\n── All uwsgi/gunicorn processes ──")
    run(ssh, "ps aux | grep -E 'uwsgi|gunicorn' | grep -v grep")
    
    print("\n── Service files ──")
    run(ssh, "ls /etc/systemd/system/*voidpanel* /etc/systemd/system/*panel* 2>/dev/null")
    run(ssh, "ls /etc/systemd/system/app-voidpanel* 2>/dev/null")
    
    print("\n── Checking uwsgi ini for voidpanel ──")
    run(ssh, "find /home/voidpanelc091 -name '*.ini' -o -name '*.sock' 2>/dev/null | head -10")
    run(ssh, "cat /home/voidpanelc091/voidpanel/voidpanel.ini 2>/dev/null || cat /home/voidpanelc091/voidpanel/*.ini 2>/dev/null | head -20")
    
    # Try to find the right service
    print("\n── Checking nginx config for voidpanel.com ──")
    run(ssh, "grep -l 'voidpanel' /etc/nginx/sites-available/*.conf /etc/nginx/sites-enabled/* 2>/dev/null | head -5")
    out, _ = run(ssh, "grep -l 'voidpanel' /etc/nginx/sites-available/*.conf 2>/dev/null | head -1")
    if out.strip():
        run(ssh, f"grep -E 'uwsgi_pass|proxy_pass|sock' {out.strip()}")

    ssh.close()

if __name__ == '__main__':
    main()
