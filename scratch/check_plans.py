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

from control.models import SuitePlan, SuiteSubscription, DomainSocialAPIConfig

# Check plans and limits
print("=== Suite Plans for social ===")
for sp in SuitePlan.objects.filter(suite='social'):
    print(f"Plan: {sp.slug} ({sp.name}) -> limits: {sp.limits}")

sub = SuiteSubscription.objects.filter(hosting_domain='rkrawat1907', suite='social').first()
if sub:
    print(f"Subscription: plan={sub.plan.slug if sub.plan else None} active={sub.is_active}")
else:
    print("No SuiteSubscription for rkrawat1907")

d_cfg = DomainSocialAPIConfig.get_for_domain('rkrawat1907')
print(f"Pinterest credentials in DB: app_id={d_cfg.pinterest_app_id}, secret len={len(d_cfg.pinterest_app_secret) if d_cfg.pinterest_app_secret else 0}")
'''

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)

sftp = ssh.open_sftp()
with sftp.open('/var/www/panel/diag_plans.py', 'w') as f:
    f.write(SCRIPT)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('/var/www/panel/venv/bin/python3 /var/www/panel/diag_plans.py 2>&1')
print(stdout.read().decode())

ssh.exec_command('rm /var/www/panel/diag_plans.py')
ssh.close()
