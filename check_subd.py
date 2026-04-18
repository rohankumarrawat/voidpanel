import pexpect
child = pexpect.spawn('ssh -o StrictHostKeyChecking=no root@178.18.250.134', timeout=60, encoding='utf-8')
child.expect('password:')
child.sendline('19072002ROHANkumar')
child.expect('# ')

# Check Nginx config for namanitwork.tech
child.sendline('cat /etc/nginx/sites-available/namanitwork.tech.conf')
child.expect('# ', timeout=30)
with open('/Users/rohan/Downloads/voidpanel-main/nginx_namanitwork.txt', 'w') as f:
    f.write(child.before.strip())

# Check Nginx configs for all subdomains
child.sendline('cat /etc/nginx/sites-available/*.namanitwork.tech.conf')
child.expect('# ', timeout=30)
with open('/Users/rohan/Downloads/voidpanel-main/nginx_subdomains.txt', 'w') as f:
    f.write(child.before.strip())

# Check recent API logs for toggle
child.sendline('tail -n 100 /var/log/voidpanel_uwsgi.log | grep "/api/nginx-cache/"')
child.expect('# ', timeout=30)
print("=== NGINX CACHE API LOGS ===")
print(child.before.strip())

child.sendline('exit')
