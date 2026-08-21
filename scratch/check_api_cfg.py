import paramiko

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)

script = """
import os, django
os.environ['DJANGO_SETTINGS_MODULE'] = 'panel.settings'
django.setup()

from control.models import SocialMediaAPIConfig, DomainSocialAPIConfig
cfg = SocialMediaAPIConfig.get()
print('Panel FB App ID:', cfg.facebook_app_id)
print('Panel FB App Secret exists:', bool(cfg.facebook_app_secret))

# Check domain cfg
d_cfg = DomainSocialAPIConfig.get_for_domain('ranjaka.com')
print('Domain ranjaka.com FB App ID:', d_cfg.facebook_app_id)
"""

stdin, stdout, stderr = ssh.exec_command(f'cd /var/www/panel && /var/www/panel/venv/bin/python3 -c "{script}"')
print(stdout.read().decode())

ssh.close()
