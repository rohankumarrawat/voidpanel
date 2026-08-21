import paramiko

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)

python_fix_script = """
import sqlite3, os

db_paths = [
    '/home/voidonyx/voidonyx/db.sqlite3',
    '/home/voidpanelc091/voidpanel/db.sqlite3',
    '/var/www/panel/db.sqlite3',
]

columns_social_platform = [
    ("facebook_auth_mode", "varchar(10) NOT NULL DEFAULT 'admin'"),
    ("instagram_auth_mode", "varchar(10) NOT NULL DEFAULT 'admin'"),
    ("twitter_auth_mode", "varchar(10) NOT NULL DEFAULT 'admin'"),
    ("linkedin_auth_mode", "varchar(10) NOT NULL DEFAULT 'admin'"),
    ("youtube_auth_mode", "varchar(10) NOT NULL DEFAULT 'admin'"),
    ("tiktok_auth_mode", "varchar(10) NOT NULL DEFAULT 'admin'"),
    ("pinterest_auth_mode", "varchar(10) NOT NULL DEFAULT 'admin'"),
    ("threads_auth_mode", "varchar(10) NOT NULL DEFAULT 'admin'"),
    ("gbusiness_auth_mode", "varchar(10) NOT NULL DEFAULT 'admin'"),
]

columns_control_social = [
    ("admin_enabled_platforms", "text NOT NULL DEFAULT '[]'"),
    ("auth_modes", "text NOT NULL DEFAULT '{}'"),
]

for db in db_paths:
    if not os.path.exists(db):
        continue
    print(f"Patching database: {db}")
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    
    # 1. Patch data_socialplatformsettings if it exists
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='data_socialplatformsettings'")
    if cur.fetchone():
        for col_name, col_type in columns_social_platform:
            try:
                cur.execute(f"ALTER TABLE data_socialplatformsettings ADD COLUMN {col_name} {col_type}")
                print(f"  + Added data_socialplatformsettings.{col_name}")
            except sqlite3.OperationalError as e:
                print(f"  . Column {col_name} already exists or: {e}")
                
    # 2. Patch control_socialmediaapiconfig if it exists
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='control_socialmediaapiconfig'")
    if cur.fetchone():
        for col_name, col_type in columns_control_social:
            try:
                cur.execute(f"ALTER TABLE control_socialmediaapiconfig ADD COLUMN {col_name} {col_type}")
                print(f"  + Added control_socialmediaapiconfig.{col_name}")
            except sqlite3.OperationalError as e:
                print(f"  . Column {col_name} already exists or: {e}")

    conn.commit()
    conn.close()

print("DATABASE SCHEMA PATCH COMPLETE!")
"""

stdin, stdout, stderr = ssh.exec_command(f"python3 -c \"{python_fix_script}\"")
print(stdout.read().decode())
print(stderr.read().decode())

# Restart services
ssh.exec_command("systemctl restart app-voidonyx-voidonyx.service app-voidpanelc091-voidpanel.service")
ssh.close()
