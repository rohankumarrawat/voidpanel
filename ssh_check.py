import pexpect
import sys

child = pexpect.spawn('ssh -o StrictHostKeyChecking=no root@178.18.250.134', timeout=60, encoding='utf-8')
child.expect('password:')
child.sendline('19072002ROHANkumar')
child.expect('# ')

child.sendline('find / -name "views.py" | grep control')
child.expect('# ', timeout=60)
print(child.before.strip())

child.sendline('exit')
