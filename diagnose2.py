import pexpect
child = pexpect.spawn('ssh -o StrictHostKeyChecking=no root@178.18.250.134', timeout=60, encoding='utf-8')
child.expect('password:')
child.sendline('19072002ROHANkumar')
child.expect('# ')

# 1. Dump the namaaaste subdomain nginx config
child.sendline('cat /etc/nginx/sites-available/namaaaste.namanitwork.tech.conf')
child.expect('# ', timeout=30)
print("=== NAMAAASTE NGINX CONFIG ===")
print(child.before.strip())

# 2. List all subdomain names in DB
child.sendline('cd /var/www/panel/website/voidpanel && python3 manage.py shell -c "from control.models import subdomainname; [print(s.subdomain, \'|\', s.name, \'|\', s.domain) for s in subdomainname.objects.all()]"')
child.expect('# ', timeout=30)
print("\n=== DB SUBDOMAINS ===")
print(child.before.strip())

# 3. Check actual python/MERN app processes
child.sendline('ls /home/namanit/public_html/')
child.expect('# ', timeout=30)
print("\n=== HOME DIRS ===")
print(child.before.strip())

child.sendline('exit')
