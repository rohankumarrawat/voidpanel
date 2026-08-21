import paramiko
HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)

# Update admin_enabled_platforms to include ALL platforms that have auth_modes set to admin
script = r'''
import sqlite3, json

db = sqlite3.connect('/var/www/panel/db.sqlite3')
c = db.cursor()

# Get current auth_modes
c.execute('SELECT auth_modes, admin_enabled_platforms, enabled_platforms FROM control_socialmediaapiconfig LIMIT 1')
row = c.fetchone()
if row:
    auth_modes = json.loads(row[0]) if row[0] else {}
    current_admin = json.loads(row[1]) if row[1] else []
    current_enabled = json.loads(row[2]) if row[2] else []
    
    print(f'Before: admin_enabled={current_admin}, enabled={current_enabled}')
    print(f'Auth modes: {auth_modes}')
    
    # Build new admin_enabled list: all platforms that have auth_mode = admin
    all_plats = ['fb', 'ig', 'tw', 'li', 'pi', 'tt', 'yt', 'th', 'gb']
    new_admin = [p for p in all_plats if auth_modes.get(p) == 'admin']
    new_enabled = list(set(current_enabled + new_admin))
    
    print(f'After: admin_enabled={new_admin}, enabled={new_enabled}')
    
    c.execute('UPDATE control_socialmediaapiconfig SET admin_enabled_platforms=?, enabled_platforms=?',
              (json.dumps(new_admin), json.dumps(new_enabled)))
    db.commit()
    print('Updated successfully!')
else:
    print('No config row found')

db.close()
'''

sftp = ssh.open_sftp()
with sftp.open('/tmp/fix_platforms.py', 'w') as f:
    f.write(script)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('python3 /tmp/fix_platforms.py')
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print('ERR:', err[:500])

# Restart service
stdin2, stdout2, stderr2 = ssh.exec_command('systemctl restart voidpanel && systemctl is-active voidpanel')
print('Service:', stdout2.read().decode().strip())

ssh.close()
