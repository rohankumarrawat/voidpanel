import paramiko

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'
LOCAL_TPL = '/Users/rohan/Desktop/voidpanel/voidonyx_server/templates/khatabook_pricing.html'
LOCAL_IMG_DIR = '/Users/rohan/Desktop/voidpanel/voidonyx_server/static/khatabook'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)

# Check nginx configs
stdin, stdout, stderr = ssh.exec_command("grep -rn 'voidonyx.in' /etc/nginx/ /etc/uwsgi/ /etc/supervisor/ /etc/systemd/system/ 2>/dev/null")
print("=== NGINX & SERVICE CONFIGS FOR VOIDONYX.IN ===")
print(stdout.read().decode())

# Check running uwsgi/gunicorn/python processes
stdin, stdout, stderr = ssh.exec_command("ps aux | grep -E 'python|uwsgi|gunicorn|django' | grep -v 'grep'")
print("=== RUNNING PYTHON PROCESSES ===")
print(stdout.read().decode())

ssh.close()
