import pexpect
child = pexpect.spawn('ssh -o StrictHostKeyChecking=no root@178.18.250.134', timeout=60, encoding='utf-8')
child.expect('password:')
child.sendline('19072002ROHANkumar')
child.expect('# ')
child.sendline('tail -80 /var/log/voidpanel_uwsgi.log | grep -i -A2 "subdomain\\|error\\|traceback\\|exception"')
child.expect('# ', timeout=15)
print(child.before.strip())
child.sendline('exit')
