import pexpect
child = pexpect.spawn('ssh -o StrictHostKeyChecking=no root@178.18.250.134', timeout=60, encoding='utf-8')
child.expect('password:')
child.sendline('19072002ROHANkumar')
child.expect('# ')

# 1. List all nginx site configs
child.sendline('ls -la /etc/nginx/sites-available/ && echo "=====ENABLED=====" && ls -la /etc/nginx/sites-enabled/')
child.expect('# ', timeout=30)
print("=== AVAILABLE SITES ===")
print(child.before.strip())

# 2. Show all subdomain configs
child.sendline('cat /etc/nginx/sites-available/*.namanitwork.tech.conf 2>/dev/null || echo "NO SUBDOMAIN CONFIGS FOUND"')
child.expect('# ', timeout=30)
with open('/tmp/nginx_subdomains.txt', 'w') as f:
    f.write(child.before.strip())
print("\n=== SUBDOMAIN NGINX CONFIGS ===")
print(child.before.strip())

# 3. Check DB subdomains
child.sendline('cd /var/www/panel/website/voidpanel && python3 manage.py shell -c "from control.models import subdomainname; [print(s.subdomain, s.name, s.domain) for s in subdomainname.objects.all()]"')
child.expect('# ', timeout=30)
print("\n=== DB SUBDOMAINS ===")
print(child.before.strip())

child.sendline('exit')
