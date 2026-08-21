import paramiko

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)

# Check voidpanel logs for the Facebook callback debug output
stdin, stdout, stderr = ssh.exec_command('journalctl -u voidpanel.service --since "5 minutes ago" --no-pager | grep -i "Facebook\\|accounts\\|page\\|Callback\\|graph.facebook" | tail -30')
out = stdout.read().decode()
print('=== VOIDPANEL LOGS ===')
print(out if out else '(no matches)')

# Check voidonyx relay logs too
stdin, stdout, stderr = ssh.exec_command('journalctl -u app-voidonyx-voidonyx.service --since "5 minutes ago" --no-pager | grep -i "Facebook\\|accounts\\|page\\|Callback\\|Relay\\|graph" | tail -30')
out2 = stdout.read().decode()
print('=== RELAY LOGS ===')
print(out2 if out2 else '(no matches)')

# Also check the actual current token from DB and query graph API
script = """import os, django, requests, json
os.environ['DJANGO_SETTINGS_MODULE'] = 'panel.settings'
django.setup()
from control.models import SocialAccount

for a in SocialAccount.objects.filter(platform='fb'):
    print('Account:', a.account_name, 'page_id:', a.page_id)
    r = requests.get('https://graph.facebook.com/v19.0/me/accounts?fields=id,name,access_token,category&limit=100&access_token=' + a.access_token, timeout=10)
    print('  Status:', r.status_code)
    data = r.json()
    if 'data' in data:
        for p in data['data']:
            print('  PAGE:', p.get('id'), p.get('name'), p.get('category'))
    else:
        print('  Response:', json.dumps(data, indent=2))
    break
"""

stdin, stdout, stderr = ssh.exec_command('cd /var/www/panel && /var/www/panel/venv/bin/python3 -c "' + script + '"')
print('=== GRAPH API CHECK ===')
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print('STDERR:', err)

ssh.close()
