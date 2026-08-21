import paramiko

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)
sftp = ssh.open_sftp()

script_content = """
import os, sys, sqlite3, glob

print("=== Checking all DBs on server for Social Accounts ===")
dbs = ['/var/www/panel/db.sqlite3', '/home/voidpanelc091/voidpanel/db.sqlite3', '/home/voidonyx/voidonyx/db.sqlite3']

for db in dbs:
    if not os.path.exists(db):
        continue
    print(f"\\n--- Database: {db} ---")
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='control_socialaccount'")
    if cur.fetchone():
        cur.execute("SELECT id, domain, username, platform, account_name, account_username FROM control_socialaccount")
        rows = cur.fetchall()
        print(f"Total Social Accounts in {db}: {len(rows)}")
        for r in rows:
            print(f"  Account ID: {r[0]} | Domain: {r[1]} | Username: {r[2]} | Platform: {r[3]} | Name: {r[4]} | @{r[5]}")
            
        cur.execute("DELETE FROM control_socialaccount WHERE username LIKE '%rkrawat%' OR domain LIKE '%rkrawat%' OR domain='fast.voidpanel.com' OR username='rkrawat1907'")
        deleted_count = cur.rowcount
        conn.commit()
        print(f"Deleted {deleted_count} accounts from {db}.")
        
        # Also cleanup any orphaned social posts or messages for rkrawat
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='control_socialpost'")
        if cur.fetchone():
            cur.execute("DELETE FROM control_socialpost WHERE domain LIKE '%rkrawat%' OR domain='fast.voidpanel.com'")
            print(f"Deleted {cur.rowcount} associated social posts.")
            
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='control_socialmessage'")
        if cur.fetchone():
            cur.execute("DELETE FROM control_socialmessage WHERE domain LIKE '%rkrawat%' OR domain='fast.voidpanel.com'")
            print(f"Deleted {cur.rowcount} associated social messages.")
            
        conn.commit()
    else:
        print("Table control_socialaccount not found in this DB.")
    conn.close()

print("\\n✅ ALL CONNECTED SOCIAL ACCOUNTS FOR rkrawat1907 REMOVED SUCCESSFULLY!")
"""

with sftp.file('/tmp/clean_accounts.py', 'w') as f:
    f.write(script_content)

sftp.close()

stdin, stdout, stderr = ssh.exec_command("python3 /tmp/clean_accounts.py")
print("OUTPUT:\n", stdout.read().decode())
print("ERRORS:\n", stderr.read().decode())

# Restart panel services
ssh.exec_command("systemctl restart voidpanel.service app-voidpanelc091-voidpanel.service")
print("Panel services restarted.")

ssh.close()
