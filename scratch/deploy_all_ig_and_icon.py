import paramiko, os

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'
LOCAL_DIR = '/Users/rohan/Desktop/voidpanel'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)
sftp = ssh.open_sftp()

# 1. Upload files
for rel_path in [
    'templates/control/social_portal.html',
    'control/views.py',
    'control/models.py',
]:
    local_f = os.path.join(LOCAL_DIR, rel_path)
    remote_f = os.path.join('/var/www/panel', rel_path)
    size = os.path.getsize(local_f)
    print(f'Uploading {rel_path} ({size} bytes)...')
    sftp.put(local_f, remote_f)
    print('  -> Uploaded')

sftp.close()

# 2. Update VoidOnyx Super Admin SocialPlatformSettings (disable Instagram)
voidonyx_py = """
from data.models import SocialPlatformSettings
s, _ = SocialPlatformSettings.objects.get_or_create(pk=1)
s.instagram_enabled = False
s.save()
print('VoidOnyx settings updated:')
print('  enabled_platform_list:', s.enabled_platform_list())
print('  admin_enabled_platform_list:', s.admin_enabled_platform_list())
"""
cmd_voidonyx = f'cd /home/voidonyx/voidonyx && /home/voidonyx/voidonyx/venv/bin/python3 manage.py shell -c "{voidonyx_py}" 2>&1'
stdin, stdout, stderr = ssh.exec_command(cmd_voidonyx)
print('VoidOnyx DB output:', stdout.read().decode())

# 3. Update Panel SocialMediaAPIConfig and clean any IG accounts
panel_py = """
from control.models import SocialMediaAPIConfig, SocialAccount
c = SocialMediaAPIConfig.get()
c.enabled_platforms = ['fb']
c.admin_enabled_platforms = ['fb']
c.save()

# Delete any existing Instagram accounts
deleted_ig = SocialAccount.objects.filter(platform='ig').delete()
print('Panel config updated:')
print('  enabled_platforms:', c.enabled_platforms)
print('  admin_enabled_platforms:', c.admin_enabled_platforms)
print('  deleted_ig_accounts:', deleted_ig)
print('  remaining_accounts:', list(SocialAccount.objects.values('id', 'domain', 'platform', 'account_name')))
"""
cmd_panel = f'cd /var/www/panel && /var/www/panel/venv/bin/python3 manage.py shell -c "{panel_py}" 2>&1'
stdin, stdout, stderr = ssh.exec_command(cmd_panel)
print('Panel DB output:', stdout.read().decode())

# 4. Restart services
stdin, stdout, stderr = ssh.exec_command('systemctl restart voidpanel app-voidonyx-voidonyx && sleep 1 && systemctl is-active voidpanel app-voidonyx-voidonyx')
print('Services status:\n' + stdout.read().decode())

ssh.close()
