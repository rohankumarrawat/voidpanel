import paramiko

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)

# Check templates in voidpanel settings on live
stdin, stdout, stderr = ssh.exec_command("grep -rn 'TEMPLATES' -A 10 /home/voidpanelc091/voidpanel/voidpanel/settings.py")
print("=== LIVE TEMPLATES CONFIG ===")
print(stdout.read().decode())

# Check nginx config for voidonyx.in to see proxy or root
stdin, stdout, stderr = ssh.exec_command("grep -rn 'server_name.*voidonyx' -A 25 /etc/nginx/ /etc/nginx/sites-enabled/ /etc/nginx/conf.d/ 2>/dev/null")
print("=== NGINX CONFIG FOR VOIDONYX ===")
print(stdout.read().decode())

ssh.close()
