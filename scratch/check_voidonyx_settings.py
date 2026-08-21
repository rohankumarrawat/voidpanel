import paramiko

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)

stdin, stdout, stderr = ssh.exec_command('cat /home/voidonyx/voidonyx/voidonyx.ini')
print("voidonyx.ini:\n", stdout.read().decode())

stdin, stdout, stderr = ssh.exec_command('cat /home/voidonyx/voidonyx/voidonyx/settings.py | grep -i installed_apps -A 20')
print("installed_apps in voidonyx:\n", stdout.read().decode())

ssh.close()
