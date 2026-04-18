import pexpect

files = [
    ('control/urls.py', '/var/www/panel/control/urls.py'),
    ('control/views.py', '/var/www/panel/control/views.py'),
    ('function.py', '/var/www/panel/function.py'),
    ('templates/control/backup.html', '/var/www/panel/templates/control/backup.html')
]

for src, dest in files:
    child = pexpect.spawn(f'scp -o StrictHostKeyChecking=no {src} root@178.18.250.134:{dest}', timeout=60, encoding='utf-8')
    index = child.expect(['(?i)password:', pexpect.EOF, pexpect.TIMEOUT])
    if index == 0:
        child.sendline('19072002ROHANkumar')
        child.expect(pexpect.EOF)
        print(f"Uploaded {src} (auth)")
    elif index == 1:
        print(f"Uploaded {src} (no auth / key)")
    else:
        print(f"Timeout on {src}")
        print("Before:", child.before)

child = pexpect.spawn('ssh -o StrictHostKeyChecking=no root@178.18.250.134', timeout=60, encoding='utf-8')
index = child.expect(['(?i)password:', '# ', pexpect.EOF, pexpect.TIMEOUT])
if index == 0:
    child.sendline('19072002ROHANkumar')
    child.expect('# ', timeout=30)
elif index == 1:
    pass

cmds = [
    "systemctl restart voidpanel voidpanel-daphne voidpanel-celery",
]

for cmd in cmds:
    print(f">>> {cmd}")
    child.sendline(cmd)
    child.expect('# ', timeout=60)
    print(child.before.strip())

child.sendline('exit')
