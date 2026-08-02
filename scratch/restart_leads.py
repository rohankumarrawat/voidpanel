#!/usr/bin/env python3
"""Restart Leads service and verify the new API endpoints are live."""
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
    print("✅ Connected to leads.voidonyx.in\n")

    # Check file was uploaded correctly
    print("── Verify uploaded files ──")
    run(ssh, "grep -n 'api_saas_tenant_create\|api_saas_packages' /home/voidonyx/leads/api/api_v1.py | head -5")
    run(ssh, "grep -n 'saas' /home/voidonyx/leads/api/urls.py")

    # Restart the uWSGI service properly
    print("\n── Restarting app-voidonyx-leads.service ──")
    run(ssh, "systemctl restart app-voidonyx-leads.service")
    run(ssh, "sleep 3")
    run(ssh, "systemctl status app-voidonyx-leads.service | head -15")

    # Test endpoints
    print("\n── Testing /api/v1/saas/packages/ ──")
    out, _ = run(ssh, "curl -s -o /dev/null -w '%{http_code}' https://leads.voidonyx.in/api/v1/saas/packages/")
    print(f"HTTP Status: {out.strip()}")
    
    if out.strip() == '200':
        out, _ = run(ssh, "curl -s https://leads.voidonyx.in/api/v1/saas/packages/ | python3 -m json.tool 2>/dev/null | head -30")
        print(f"Response:\n{out}")
    else:
        # Check logs for errors
        print("\n── Checking error logs ──")
        run(ssh, "journalctl -u app-voidonyx-leads.service --no-pager -n 30")
        run(ssh, "tail -30 /var/log/nginx/leads.voidonyx.in.error.log 2>/dev/null")

    print("\n── Testing /api/v1/saas/tenant/create/ (POST without key → expect 403) ──")
    out, _ = run(ssh, "curl -s -X POST https://leads.voidonyx.in/api/v1/saas/tenant/create/ -H 'Content-Type: application/json' -d '{}'")
    print(f"Response: {out[:200]}")

    ssh.close()
    print("\n✅ Done!")

if __name__ == '__main__':
    main()
