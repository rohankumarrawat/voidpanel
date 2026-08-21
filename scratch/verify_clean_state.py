import paramiko
HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)

# Check portal context render
cmd = """cd /var/www/panel && /var/www/panel/venv/bin/python3 manage.py shell -c "
from control.models import SocialMediaAPIConfig
c = SocialMediaAPIConfig.get()
print('admin_enabled_platforms:', c.admin_enabled_platforms)
print('enabled_platforms:', c.enabled_platforms)
for p in ['fb','ig','tw','li','pi','tt','yt','th']:
    print(f'  {p}: is_admin_1click={c.is_admin_1click(p)}')
" 2>&1"""
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())

ssh.close()
