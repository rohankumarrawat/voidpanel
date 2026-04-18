import pexpect

child = pexpect.spawn('ssh -o StrictHostKeyChecking=no root@178.18.250.134', timeout=60, encoding='utf-8')
child.expect('password:')
child.sendline('19072002ROHANkumar')
child.expect('# ')

script = """
cat /home/namanit/.backup_progress
"""

for line in script.strip().split('\n'):
    child.sendline(line)

child.expect('# ', timeout=30)
print(child.before.strip())
child.sendline('exit')
