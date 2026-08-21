import paramiko

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)

verify_script = """
import sqlite3
conn = sqlite3.connect('/var/www/panel/db.sqlite3')
cur = conn.cursor()
cur.execute("SELECT id, domain, username, platform, account_name FROM control_socialaccount WHERE username LIKE '%rkrawat%' OR domain LIKE '%rkrawat%'")
rows = cur.fetchall()
print('Remaining accounts for rkrawat:', rows)
conn.close()
"""

stdin, stdout, stderr = ssh.exec_command(f"python3 -c \"{verify_script}\"")
print(stdout.read().decode())
ssh.close()
