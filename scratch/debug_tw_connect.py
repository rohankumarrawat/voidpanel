import paramiko

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)

script = """
import urllib.parse
from control.models import DomainSocialAPIConfig, SocialMediaAPIConfig

d_cfg = DomainSocialAPIConfig.get_for_domain('rkrawat1907')
cfg = SocialMediaAPIConfig.get()

app_id = d_cfg.twitter_api_key or cfg.twitter_api_key
print('Twitter app_id used:', app_id)

# Check what redirect_uri is expected
print('d_cfg redirect_uri:', d_cfg.redirect_uri)
"""

cmd = f'cd /var/www/panel && /var/www/panel/venv/bin/python3 manage.py shell -c "{script}" 2>&1'
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())

ssh.close()
