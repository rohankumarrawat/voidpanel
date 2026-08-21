import paramiko, os

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)
sftp = ssh.open_sftp()

# 1. control/views.py already uploaded. Verify.
stdin, stdout, stderr = ssh.exec_command('ls -la /var/www/panel/control/views.py')
print('Panel views.py:', stdout.read().decode().strip())

# 2. Upload relay views.py
local_relay = '/Users/rohan/Desktop/voidpanel/website/voidpanel/voidpanel/views.py'
remote_relay = '/home/voidonyx/voidonyx/voidpanel/views.py'
print('Uploading relay views.py (%d bytes) to %s...' % (os.path.getsize(local_relay), remote_relay))
sftp.put(local_relay, remote_relay)
print('  -> Done')

sftp.close()

# 3. Restart both services
import time

print('\nRestarting voidpanel.service...')
stdin, stdout, stderr = ssh.exec_command('systemctl restart voidpanel.service')
stdout.read()
err = stderr.read().decode()
if err:
    print('  STDERR:', err[:200])
else:
    print('  OK')

print('Restarting app-voidonyx-voidonyx.service...')
stdin, stdout, stderr = ssh.exec_command('systemctl restart app-voidonyx-voidonyx.service')
stdout.read()
err = stderr.read().decode()
if err:
    print('  STDERR:', err[:200])
else:
    print('  OK')

time.sleep(3)

# 4. Verify services
stdin, stdout, stderr = ssh.exec_command('systemctl is-active voidpanel.service app-voidonyx-voidonyx.service')
statuses = stdout.read().decode().strip().split('\n')
print('\nService statuses:')
services = ['voidpanel.service', 'app-voidonyx-voidonyx.service']
for svc, status in zip(services, statuses):
    icon = 'OK' if status.strip() == 'active' else 'FAIL'
    print('  %s: %s [%s]' % (svc, status.strip(), icon))

# 5. Quick verify: check the fix is deployed
stdin, stdout, stderr = ssh.exec_command('grep -c "sub.hosting_domain.*subscription" /var/www/panel/control/views.py')
has_fix1 = stdout.read().decode().strip()
stdin, stdout, stderr = ssh.exec_command('grep -c "pages_show_list" /home/voidonyx/voidonyx/voidpanel/views.py')
has_fix5 = stdout.read().decode().strip()
stdin, stdout, stderr = ssh.exec_command('grep -c "social_src.*suite" /var/www/panel/control/views.py')
has_fix3 = stdout.read().decode().strip()

print('\nFix verification:')
print('  Fix 1 (domain priority): %s matches' % has_fix1)
print('  Fix 3 (disconnect redirect): %s matches' % has_fix3)
print('  Fix 5 (FB scopes): %s matches' % has_fix5)

all_ok = all(s.strip() == 'active' for s in statuses) and int(has_fix1 or '0') > 0 and int(has_fix5 or '0') > 0
print('\n%s All fixes deployed!' % ('✅' if all_ok else '❌ Some checks failed.'))

ssh.close()
