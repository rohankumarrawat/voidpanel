import paramiko
HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)

stdin, stdout, stderr = ssh.exec_command('grep -n "IG AUTO-DISCOVER\|instagram_business_account\|Auto-discover Instagram" /var/www/panel/control/views.py')
print('IG auto-discovery in views.py:')
print(stdout.read().decode())

stdin2, stdout2, stderr2 = ssh.exec_command('grep -n "ADMIN_1CLICK_PLATFORMS\|admin_1click_platforms" /var/www/panel/templates/control/social_portal.html | head -5')
print('1-Click references in template:')
print(stdout2.read().decode())

# Also verify admin_enabled_platforms DB state
script = '''
import sqlite3, json
db = sqlite3.connect('/var/www/panel/db.sqlite3')
c = db.cursor()
c.execute('SELECT admin_enabled_platforms, enabled_platforms FROM control_socialmediaapiconfig LIMIT 1')
row = c.fetchone()
if row:
    print('admin_enabled:', row[0])
    print('enabled:', row[1])
db.close()
'''
sftp = ssh.open_sftp()
with sftp.open('/tmp/verify_cfg.py', 'w') as f:
    f.write(script)
sftp.close()

stdin3, stdout3, stderr3 = ssh.exec_command('python3 /tmp/verify_cfg.py')
print('DB Config:')
print(stdout3.read().decode())

ssh.close()
