import paramiko
HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)

cmd = '''cd /var/www/panel && source venv/bin/activate && python manage.py shell -c "
from control.models import SocialMediaAPIConfig
c = SocialMediaAPIConfig.get()
print('admin_enabled_platforms:', c.admin_enabled_platforms)
print('enabled_platforms:', c.enabled_platforms)
print('auth_modes:', c.auth_modes)
print()
for p in ['fb','ig','tw','li','pi','tt','yt','th','gb']:
    print(f'{p}: is_admin_1click={c.is_admin_1click(p)}')
print()
print('FB app_id:', repr(c.facebook_app_id[:20] if c.facebook_app_id else ''))
print('TW api_key:', repr(c.twitter_api_key[:20] if c.twitter_api_key else ''))
print('LI client_id:', repr(c.linkedin_client_id[:20] if c.linkedin_client_id else ''))
print('PI app_id:', repr(c.pinterest_app_id[:20] if c.pinterest_app_id else ''))
print('TT client_key:', repr(c.tiktok_client_key[:20] if c.tiktok_client_key else ''))
print('YT client_id:', repr(c.google_client_id[:20] if c.google_client_id else ''))

# Also check DomainSocialAPIConfig for rkrawat1907
from control.models import DomainSocialAPIConfig
try:
    dc = DomainSocialAPIConfig.objects.get(domain='rkrawat1907')
    print()
    print('--- Domain config for rkrawat1907 ---')
    print('tw_api_key:', repr(dc.twitter_api_key[:20] if dc.twitter_api_key else ''))
    print('li_client_id:', repr(dc.linkedin_client_id[:20] if dc.linkedin_client_id else ''))
except:
    print('No DomainSocialAPIConfig for rkrawat1907')
"
'''
stdin, stdout, stderr = ssh.exec_command(cmd)
print('STDOUT:', stdout.read().decode())
err = stderr.read().decode()
if 'Error' in err or 'error' in err.lower():
    print('STDERR:', err[-500:])
ssh.close()
