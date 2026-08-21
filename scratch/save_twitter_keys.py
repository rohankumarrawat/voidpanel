import paramiko

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

CLIENT_ID = 'TTBUa2RhLUNDbExOcFNMNmRUSkE6MTpjaQ'
CLIENT_SECRET = 'oleQtxlxDlb1jZSkzm7rOLGiv-fKsEVULMO7sa71GvCbKW4mOK'
CONSUMER_KEY = 'mIK2w7GXUAYRTY7HoAMj6fe6U'
CONSUMER_SECRET = 'eKD2sZlreHPCSVyQrMs5pmodJk5CSrKE1irsCnpBQi7GIR8OHO'
BEARER_TOKEN = 'AAAAAAAAAAAAAAAAAAAAABKZ%2FAEAAAAARzTXlNPWNzgdzzv41W%2FbtAgYFdU%3DXWlO7itbfS1fb5jL8LAWZoKyBXun7IZrJy9GkCgHUHrFxOFfpI'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)

# 1. Update DomainSocialAPIConfig for rkrawat1907
cmd1 = f'''cd /var/www/panel && /var/www/panel/venv/bin/python3 manage.py shell -c "
from control.models import DomainSocialAPIConfig
cfg, _ = DomainSocialAPIConfig.objects.get_or_create(domain='rkrawat1907', defaults={{'username':'rkrawat1907'}})
cfg.twitter_api_key = '{CLIENT_ID}'
cfg.twitter_api_secret = '{CLIENT_SECRET}'
cfg.twitter_bearer_token = '{BEARER_TOKEN}'
cfg.save()
print('DomainSocialAPIConfig for rkrawat1907 saved successfully:')
print('  configured_platforms:', cfg.configured_platforms)
" 2>&1'''
stdin, stdout, stderr = ssh.exec_command(cmd1)
print(stdout.read().decode())

# 2. Also update Super Admin master SocialPlatformSettings in voidonyx so 1-Click works if enabled
cmd2 = f'''cd /home/voidonyx/voidonyx && /home/voidonyx/voidonyx/venv/bin/python3 manage.py shell -c "
from data.models import SocialPlatformSettings
s, _ = SocialPlatformSettings.objects.get_or_create(pk=1)
s.twitter_enabled = True
s.twitter_api_key = '{CLIENT_ID}'
s.twitter_api_secret = '{CLIENT_SECRET}'
s.twitter_bearer_token = '{BEARER_TOKEN}'
s.save()
print('VoidOnyx SocialPlatformSettings saved successfully:')
print('  enabled_platforms:', s.enabled_platform_list())
" 2>&1'''
stdin, stdout, stderr = ssh.exec_command(cmd2)
print(stdout.read().decode())

# 3. Update SocialMediaAPIConfig on panel
cmd3 = f'''cd /var/www/panel && /var/www/panel/venv/bin/python3 manage.py shell -c "
from control.models import SocialMediaAPIConfig
c = SocialMediaAPIConfig.get()
c.twitter_api_key = '{CLIENT_ID}'
c.twitter_api_secret = '{CLIENT_SECRET}'
c.twitter_bearer_token = '{BEARER_TOKEN}'
if 'tw' not in (c.enabled_platforms or []):
    c.enabled_platforms = (c.enabled_platforms or []) + ['tw']
if 'tw' not in (c.admin_enabled_platforms or []):
    c.admin_enabled_platforms = (c.admin_enabled_platforms or []) + ['tw']
c.save()
print('Panel SocialMediaAPIConfig saved:')
print('  enabled_platforms:', c.enabled_platforms)
print('  admin_enabled_platforms:', c.admin_enabled_platforms)
" 2>&1'''
stdin, stdout, stderr = ssh.exec_command(cmd3)
print(stdout.read().decode())

ssh.close()
