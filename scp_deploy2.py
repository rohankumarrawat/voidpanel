import pexpect
import sys

child = pexpect.spawn('scp -o StrictHostKeyChecking=no control/views.py root@178.18.250.134:/var/www/panel/control/views.py', timeout=60, encoding='utf-8')
child.expect('password:')
child.sendline('19072002ROHANkumar')
child.expect(pexpect.EOF)
print(child.before.strip())

child = pexpect.spawn('ssh -o StrictHostKeyChecking=no root@178.18.250.134', timeout=60, encoding='utf-8')
child.expect('password:')
child.sendline('19072002ROHANkumar')
child.expect('# ')

cmds = [
    "systemctl restart voidpanel voidpanel-daphne voidpanel-celery",
]

for cmd in cmds:
    print(f">>> {cmd}")
    child.sendline(cmd)
    child.expect('# ', timeout=60)
    print(child.before.strip())

child.sendline('exit')
