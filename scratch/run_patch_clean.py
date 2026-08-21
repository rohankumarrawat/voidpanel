import paramiko

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)
sftp = ssh.open_sftp()

remote_script_content = """import sqlite3, os

db_paths = [
    '/home/voidonyx/voidonyx/db.sqlite3',
    '/home/voidpanelc091/voidpanel/db.sqlite3',
    '/var/www/panel/db.sqlite3',
]

columns_social_platform = [
    ('facebook_auth_mode', "varchar(10) NOT NULL DEFAULT 'admin'"),
    ('instagram_auth_mode', "varchar(10) NOT NULL DEFAULT 'admin'"),
    ('twitter_auth_mode', "varchar(10) NOT NULL DEFAULT 'admin'"),
    ('linkedin_auth_mode', "varchar(10) NOT NULL DEFAULT 'admin'"),
    ('youtube_auth_mode', "varchar(10) NOT NULL DEFAULT 'admin'"),
    ('tiktok_auth_mode', "varchar(10) NOT NULL DEFAULT 'admin'"),
    ('pinterest_auth_mode', "varchar(10) NOT NULL DEFAULT 'admin'"),
    ('threads_auth_mode', "varchar(10) NOT NULL DEFAULT 'admin'"),
    ('gbusiness_auth_mode', "varchar(10) NOT NULL DEFAULT 'admin'"),
]

columns_control_social = [
    ('admin_enabled_platforms', "text NOT NULL DEFAULT '[]'"),
    ('auth_modes', "text NOT NULL DEFAULT '{}'"),
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

with sftp.file('/tmp/patch_db.py', 'w') as f:
    f.write(remote_script_content)

sftp.close()

stdin, stdout, stderr = ssh.exec_command("python3 /tmp/patch_db.py")
print("STDOUT:\n", stdout.read().decode())
print("STDERR:\n", stderr.read().decode())

# Restart services
ssh.exec_command("systemctl restart app-voidonyx-voidonyx.service app-voidpanelc091-voidpanel.service")

# Test live model access
stdin, stdout, stderr = ssh.exec_command("cd /home/voidonyx/voidonyx && /home/voidonyx/voidonyx/venv/bin/python3 -c \"import os, django; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'voidpanel.settings'); django.setup(); from data.models import SocialPlatformSettings; cfg = SocialPlatformSettings.get(); print('LIVE VOIDONYX AUTH MODE:', cfg.facebook_auth_mode)\"")
print("TEST LIVE VOIDONYX:\n", stdout.read().decode(), stderr.read().decode())

ssh.close()
