#!/usr/bin/env python3
"""Check get_user_dashboard_context and requests call"""
import paramiko

HOST = '207.180.209.216'
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=22, username='root', password='19072002ROHANkumar!', timeout=15)

def run(cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=30)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    return out, err

print("=== Test get_user_dashboard_context ===")
out, _ = run("""cd /var/www/panel && /var/www/panel/venv/bin/python manage.py shell -c "
import traceback
try:
    from control.views import get_user_dashboard_context
    result = get_user_dashboard_context('voidonyx', '')
    print(f'get_user_dashboard_context OK, keys: {list(result.keys())}')
except Exception as e:
    print(f'ERROR in get_user_dashboard_context: {e}')
    traceback.print_exc()
" 2>&1""")
print(out)

print("\n=== Test docs API call ===")
out, _ = run("""cd /var/www/panel && /var/www/panel/venv/bin/python manage.py shell -c "
import traceback, requests
from django.conf import settings
try:
    url = getattr(settings, 'VOIDPANEL_WEBSITE_URL', 'https://voidpanel.com') + '/clientdocs/'
    print(f'Fetching: {url}')
    response = requests.get(url, timeout=2)
    print(f'Status: {response.status_code}')
    if response.status_code == 200:
        data = response.json()
        print(f'Docs count: {len(data)}')
except Exception as e:
    print(f'ERROR: {e}')
    traceback.print_exc()
" 2>&1""")
print(out)

# Also check the uwsgi error log for the actual traceback
print("\n=== Recent uWSGI errors ===")
out, _ = run("grep -A 10 'Traceback\|Error\|Exception' /var/log/voidpanel_uwsgi.log 2>/dev/null | tail -30")
print(out)

ssh.close()
