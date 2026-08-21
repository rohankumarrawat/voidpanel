import paramiko

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)

# Check ALL social accounts
script = r"""
import os, django, json
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'panel.settings')
django.setup()

from control.models import SocialAccount
print('=== ALL SocialAccounts ===')
for a in SocialAccount.objects.all():
    print(f'  ID={a.id} domain="{a.domain}" username="{a.username}" platform="{a.platform}" name="{a.account_name}" active={a.is_active} page_id="{a.page_id}" page_name="{a.page_name}"')

# Check suite_user session domain
from control.models import DomainSettings
for d in DomainSettings.objects.all()[:5]:
    print(f'  DomainSettings: domain="{d.domain}"')
"""

stdin, stdout, stderr = ssh.exec_command(f'cd /var/www/panel && /var/www/panel/venv/bin/python3 -c """{script}"""')
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print("STDERR:", err)

# Also check the c091 panel
script2 = r"""
import os, django, json
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'panel.settings')
django.setup()

from control.models import SocialAccount
print('=== c091 ALL SocialAccounts ===')
for a in SocialAccount.objects.all():
    print(f'  ID={a.id} domain="{a.domain}" username="{a.username}" platform="{a.platform}" name="{a.account_name}" active={a.is_active}')
"""

stdin, stdout, stderr = ssh.exec_command(f'cd /home/voidpanelc091/voidpanel && /home/voidpanelc091/voidpanel/venv/bin/python3 -c """{script2}"""')
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print("STDERR:", err)

ssh.close()
