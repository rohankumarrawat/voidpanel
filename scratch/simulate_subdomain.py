#!/usr/bin/env python3
"""Simulate the subdomain view logic step by step"""
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

print("=== Simulating subdomain view for voidonyx.in ===")
out, _ = run("""cd /var/www/panel && /var/www/panel/venv/bin/python manage.py shell -c "
import traceback
from control.models import domain, user, subdomainname, package

data = 'voidonyx.in'
current = 'voidonyx'  # This is what the superuser resolves to

try:
    # Step 1: get domain
    lold = domain.objects.get(domain=data)
    print(f'Step 1 OK: domain={lold.domain}, dir={lold.dir}')
    
    # Step 2: get user
    u = user.objects.get(username=current)
    print(f'Step 2 OK: user={u.username}, hosting_package={u.hosting_package}')
    
    # Step 3: get package
    pkg = package.objects.filter(name=u.hosting_package).first()
    print(f'Step 3: package={pkg}')
    if pkg:
        print(f'  subdomain limit={pkg.subdomain}')
        print(f'  databases_allowed={pkg.databases_allowed}')
    else:
        print('  WARNING: Package not found!')
        # Try safe_get_package
        from control.views import safe_get_package
        spkg = safe_get_package(u.hosting_package)
        print(f'  safe_get_package result: {spkg}')
        print(f'  subdomain attr: {spkg.subdomain}')
        print(f'  databases_allowed attr: {spkg.databases_allowed}')
    
    # Step 4: get subdomains
    subs = subdomainname.objects.filter(domain=data)
    print(f'Step 4 OK: {len(subs)} subdomains found')
    
    # Step 5: totaldb check
    from control.views import safe_get_package
    spkg = safe_get_package(u.hosting_package)
    totaldb = int(spkg.databases_allowed)
    print(f'Step 5 OK: totaldb={totaldb}')
    
except Exception as e:
    print(f'ERROR: {e}')
    traceback.print_exc()
" 2>&1""")
print(out)

ssh.close()
