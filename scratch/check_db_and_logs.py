import paramiko

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)

script = """
import sqlite3

for p in ['/var/www/panel/db.sqlite3', '/home/voidpanelc091/voidpanel/db.sqlite3', '/home/voidonyx/voidonyx/db.sqlite3']:
    print('=== DB:', p)
    try:
        conn = sqlite3.connect(p)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%socialaccount%'")
        tbl = cur.fetchall()
        if tbl:
            cur.execute(f"SELECT id, domain, platform, account_id, account_name, is_active FROM {tbl[0][0]}")
            print('  SocialAccount rows:', cur.fetchall())
        conn.close()
    except Exception as e:
        print('  Error:', e)
"""

stdin, stdout, stderr = ssh.exec_command(f"python3 -c \"{script}\"")
print(stdout.read().decode())

# Check journal logs for voidpanel or nginx
stdin, stdout, stderr = ssh.exec_command("journalctl -u voidpanel.service --no-pager -n 30")
print("VoidPanel Service Logs:\n", stdout.read().decode())

ssh.close()
