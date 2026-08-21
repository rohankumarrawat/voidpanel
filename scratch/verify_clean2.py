import paramiko

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)

stdin, stdout, stderr = ssh.exec_command("sqlite3 /var/www/panel/db.sqlite3 \"SELECT id, domain, username, platform, account_name FROM control_socialaccount WHERE username LIKE '%rkrawat%' OR domain LIKE '%rkrawat%';\"")
print("Accounts in DB for rkrawat:\n", stdout.read().decode())

ssh.close()
