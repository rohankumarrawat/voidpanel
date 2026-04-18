import pexpect
child = pexpect.spawn('ssh -o StrictHostKeyChecking=no root@178.18.250.134', timeout=60, encoding='utf-8')
child.expect('password:')
child.sendline('19072002ROHANkumar')
child.expect('# ')

cmds = [
    "cd /var/www/panel/website/voidpanel && git pull origin v2.0",
    "systemctl restart voidpanel voidpanel-daphne voidpanel-celery",
]

for cmd in cmds:
    print(f">>> {cmd}")
    child.sendline(cmd)
    child.expect('# ', timeout=60)
    print(child.before.strip())

child.sendline('exit')
