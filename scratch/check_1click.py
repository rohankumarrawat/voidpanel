import paramiko
HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)

script = r'''
import sqlite3
db = sqlite3.connect('/var/www/panel/db.sqlite3')
c = db.cursor()

c.execute("SELECT name FROM sqlite_master WHERE type='table' AND (name LIKE '%social%' OR name LIKE '%api%' OR name LIKE '%config%')")
print('Tables:', [r[0] for r in c.fetchall()])

try:
    c.execute('SELECT admin_enabled_platforms, enabled_platforms, auth_modes FROM control_socialmediaapiconfig LIMIT 1')
    row = c.fetchone()
    if row:
        print('admin_enabled_platforms:', row[0])
        print('enabled_platforms:', row[1])
        print('auth_modes:', row[2])
    else:
        print('No config row found')
except Exception as e:
    print('Config error:', e)

try:
    c.execute("SELECT id, platform, account_name, page_name, page_id, is_active, domain FROM control_socialaccount WHERE domain='rkrawat1907'")
    for r in c.fetchall():
        print('Account: id=%s platform=%s name=%s page_name=%s page_id=%s active=%s' % (r[0], r[1], r[2], r[3], r[4], r[5]))
except Exception as e:
    print('Accounts error:', e)

try:
    q = "SELECT facebook_app_id, twitter_api_key, linkedin_client_id, tiktok_client_key, pinterest_app_id, google_client_id FROM control_socialmediaapiconfig LIMIT 1"
    c.execute(q)
    row = c.fetchone()
    if row:
        labels = ['FB', 'TW', 'LI', 'TT', 'PI', 'YT']
        for i, l in enumerate(labels):
            print('%s has key: %s' % (l, 'YES' if row[i] else 'NO'))
except Exception as e:
    print('Keys error:', e)

db.close()
'''

# Write script to server and run it
sftp = ssh.open_sftp()
with sftp.open('/tmp/check_cfg.py', 'w') as f:
    f.write(script)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('python3 /tmp/check_cfg.py')
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print('ERR:', err[:500])
ssh.close()
