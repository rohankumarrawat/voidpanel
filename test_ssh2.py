import pexpect

child = pexpect.spawn('ssh -o StrictHostKeyChecking=no root@178.18.250.134', timeout=60, encoding='utf-8')
child.expect('password:')
child.sendline('19072002ROHANkumar')
child.expect('# ')

cmds = [
    "journalctl -u voidpanel --since '30 min ago' --no-pager | grep -iE 'error|traceback|exception' -A 10 -B 2"
]

for cmd in cmds:
    print(f">>> {cmd}")
    child.sendline(cmd)
    child.expect('# ', timeout=60)
    print(child.before.strip())

child.sendline('exit')
