#!/usr/bin/env python3
"""Debug the subdomain view for voidonyx.in"""
import paramiko

HOST = '207.180.209.216'
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=22, username='root', password='19072002ROHANkumar!', timeout=15)

def run(cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=30)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    return out, err

# Check if voidonyx.in exists in the domain table
print("=== Check domain table for voidonyx.in ===")
out, _ = run("""cd /var/www/panel && /var/www/panel/venv/bin/python manage.py shell -c "
from control.models import domain, user, subdomainname
# Check domain
d = domain.objects.filter(domain='voidonyx.in').first()
if d:
    print(f'Domain found: {d.domain}, dir={d.dir}, status={d.status}')
else:
    print('Domain NOT FOUND in domain table')

# Check all domains
print()
print('All domains:')
for dd in domain.objects.all():
    print(f'  {dd.domain} -> dir={dd.dir}')

# Check user table
print()
print('All users:')
for u in user.objects.all():
    print(f'  username={u.username}, domain={u.domain}')
" 2>&1""")
print(out)

ssh.close()
