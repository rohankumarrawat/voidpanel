import paramiko

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

SCRIPT = '''
import os, sys, django
sys.path.insert(0, '/var/www/panel')
os.environ['DJANGO_SETTINGS_MODULE'] = 'panel.settings'
django.setup()

from control.models import SocialAccount, DomainSocialAPIConfig, SocialMediaAPIConfig

print("=== DomainSocialAPIConfig ===")
d = DomainSocialAPIConfig.get_for_domain('rkrawat1907')
print("  pinterest_app_id:", repr(d.pinterest_app_id))
print("  pinterest_app_secret len:", len(d.pinterest_app_secret) if d.pinterest_app_secret else 0)

print()
print("=== Global SocialMediaAPIConfig ===")
g = SocialMediaAPIConfig.get()
print("  pinterest_app_id:", repr(g.pinterest_app_id))
print("  pinterest_app_secret len:", len(g.pinterest_app_secret) if g.pinterest_app_secret else 0)

print()
print("=== All Pinterest SocialAccount records ===")
pi_accs = SocialAccount.objects.filter(platform='pi')
print("Count:", pi_accs.count())
for a in pi_accs:
    print(f"  id={a.id} name={a.account_name} domain={a.domain} active={a.is_active}")
'''

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)

sftp = ssh.open_sftp()
with sftp.open('/var/www/panel/diag_pi_config.py', 'w') as f:
    f.write(SCRIPT)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('/var/www/panel/venv/bin/python3 /var/www/panel/diag_pi_config.py 2>&1')
print(stdout.read().decode())

ssh.exec_command('rm /var/www/panel/diag_pi_config.py')
ssh.close()
