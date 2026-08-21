import paramiko

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)

# Check all systemd services related to voidonyx or uwsgi
stdin, stdout, stderr = ssh.exec_command("systemctl list-units --type=service | grep -E 'void|uwsgi|nginx'")
print("=== SYSTEM SERVICES ===")
print(stdout.read().decode())

# Check where khatabook_pricing.html is on the filesystem
stdin, stdout, stderr = ssh.exec_command("find /home /var/www -name 'khatabook_pricing.html' -exec ls -la {} + 2>/dev/null")
print("=== KHATABOOK PRICING TEMPLATES ON SERVER ===")
print(stdout.read().decode())

# Restart all uwsgi Emperor or specific uwsgi services
stdin, stdout, stderr = ssh.exec_command("systemctl restart uwsgi 2>/dev/null || pkill -9 -f uwsgi; sleep 1; systemctl restart nginx")
print(stdout.read().decode())

ssh.close()
