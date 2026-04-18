import pexpect

HOST = "178.18.250.134"
USER = "root"
PASS = "19072002ROHANkumar"

child = pexpect.spawn(f'ssh -o StrictHostKeyChecking=no {USER}@{HOST}', timeout=60, encoding='utf-8')
child.expect('password:')
child.sendline(PASS)
child.expect('# ')

child.sendline('tail -50 /var/log/uwsgi/voidpanel.log 2>/dev/null || tail -50 /var/www/panel/uwsgi.log 2>/dev/null || find /var/log -name "*.log" -newer /tmp -exec grep -l "control" {} \\; 2>/dev/null | head -5')
child.expect('# ', timeout=15)
print(child.before.strip())

child.sendline('cat /var/www/panel/panel.ini')
child.expect('# ', timeout=15)
print(child.before.strip())

child.sendline('exit')
