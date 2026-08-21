import paramiko, requests

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)

# Check what the database has on voidonyx vs voidpanel
cmds = [
    # 1. Check data_socialplatformsettings in /home/voidonyx/voidonyx/db.sqlite3
    "python3 -c \"import sqlite3; conn = sqlite3.connect('/home/voidonyx/voidonyx/db.sqlite3'); cur = conn.cursor(); cur.execute('SELECT facebook_enabled, facebook_auth_mode, updated_at FROM data_socialplatformsettings'); print('Voidonyx DB:', cur.fetchall())\"",
    
    # 2. Check data_socialplatformsettings in /home/voidpanelc091/voidpanel/db.sqlite3
    "python3 -c \"import sqlite3; conn = sqlite3.connect('/home/voidpanelc091/voidpanel/db.sqlite3'); cur = conn.cursor(); cur.execute('SELECT facebook_enabled, facebook_auth_mode, updated_at FROM data_socialplatformsettings'); print('Voidpanel DB:', cur.fetchall())\"",

    # 3. Check what curl https://voidpanel.com/api/social/platform-config/ returns
    "curl -s https://voidpanel.com/api/social/platform-config/ || true",
    "curl -s https://voidonyx.in/api/social/platform-config/ || true",

    # 4. Check panel database: control_socialmediaapiconfig in /var/www/panel/db.sqlite3 or /home/voidpanelc091/voidpanel/db.sqlite3
    "python3 -c \"import sqlite3; conn = sqlite3.connect('/home/voidpanelc091/voidpanel/db.sqlite3'); cur = conn.cursor(); cur.execute('SELECT enabled_platforms, admin_enabled_platforms, auth_modes FROM control_socialmediaapiconfig'); print('Control SocialMediaAPIConfig in voidpanelc091:', cur.fetchall())\"",
    "python3 -c \"import sqlite3; conn = sqlite3.connect('/var/www/panel/db.sqlite3'); cur = conn.cursor(); cur.execute('SELECT enabled_platforms, admin_enabled_platforms, auth_modes FROM control_socialmediaapiconfig'); print('Control SocialMediaAPIConfig in /var/www/panel:', cur.fetchall())\"",
]

for c in cmds:
    print(f"=== {c} ===")
    stdin, stdout, stderr = ssh.exec_command(c)
    print("STDOUT:", stdout.read().decode().strip())
    print("STDERR:", stderr.read().decode().strip())

ssh.close()
