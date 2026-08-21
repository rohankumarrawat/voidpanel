import paramiko
HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)

cmd = """cd /home/voidonyx/voidonyx && /home/voidonyx/voidonyx/venv/bin/python3 manage.py shell -c "
from data.models import SocialPlatformSettings
s, _ = SocialPlatformSettings.objects.get_or_create(pk=1)
print('--- SocialPlatformSettings in voidonyx ---')
print('facebook_enabled:', s.facebook_enabled, 'mode:', s.facebook_auth_mode)
print('instagram_enabled:', s.instagram_enabled, 'mode:', s.instagram_auth_mode)
print('twitter_enabled:', s.twitter_enabled, 'mode:', s.twitter_auth_mode)
print('linkedin_enabled:', s.linkedin_enabled, 'mode:', s.linkedin_auth_mode)
print('youtube_enabled:', s.youtube_enabled, 'mode:', s.youtube_auth_mode)
print('tiktok_enabled:', s.tiktok_enabled, 'mode:', s.tiktok_auth_mode)
print('pinterest_enabled:', s.pinterest_enabled, 'mode:', s.pinterest_auth_mode)
print('threads_enabled:', s.threads_enabled, 'mode:', s.threads_auth_mode)
print('enabled_platform_list:', s.enabled_platform_list())
print('admin_enabled_platform_list:', s.admin_enabled_platform_list())
" 2>&1"""
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())

ssh.close()
