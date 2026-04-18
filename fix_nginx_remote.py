#!/usr/bin/env python3
import pexpect

HOST = "178.18.250.134"
USER = "root"
PASS = "19072002ROHANkumar"

child = pexpect.spawn(f'ssh -o StrictHostKeyChecking=no {USER}@{HOST}', timeout=60, encoding='utf-8')
child.expect('password:')
child.sendline(PASS)
child.expect('# ')
print("[+] Connected")

# Write the fix script remotely via echo lines to avoid heredoc issues
lines = [
    "import re",
    "p='/etc/nginx/sites-enabled/namanitwork.tech.conf'",
    "c=open(p).read()",
    r"c=re.sub(r'root\s+/home/namanit/public_html;','root /home/namanit/loooopppuuuuu/frontend/build;',c)",
    r"c=re.sub(r'[ \t]*location / [{](?:[^{}]|[{][^{}]*[}])*[}]\s*','',c)",
    r"c=re.sub(r'[ \t]*location /static/ [{](?:[^{}]|[{][^{}]*[}])*[}]\s*','',c)",
    r"c=re.sub(r'[ \t]*location /api/ [{](?:[^{}]|[{][^{}]*[}])*[}]\s*','',c)",
]

# Build new_blocks and replacement using string concat to avoid indentation issues
lines += [
    "nb = '\\n    location / {\\n        try_files $uri /index.html;\\n    }\\n\\n'",
    "nb += '    location /static/ {\\n        alias /home/namanit/loooopppuuuuu/frontend/build/static/;\\n        expires 30d;\\n    }\\n\\n'",
    "nb += '    location /api/ {\\n        proxy_pass http://127.0.0.1:3002;\\n        proxy_http_version 1.1;\\n        proxy_set_header Host $host;\\n    }\\n\\n'",
    r"c=c.replace('location ~ /\\.ht {', nb + '    location ~ /\\.ht {', 1)",
    "open(p,'w').write(c)",
    "print('NGINX_CONFIG_UPDATED')",
]

child.sendline("python3 << 'PYEOF'")
for line in lines:
    child.sendline(line)
child.sendline('PYEOF')

idx = child.expect(['NGINX_CONFIG_UPDATED', 'Error', 'Traceback', pexpect.TIMEOUT], timeout=30)
if idx == 0:
    print("[+] Config updated!")
else:
    print("[-] Script error:", child.before)
    child.sendline('exit')
    exit(1)

child.expect('# ')

child.sendline('nginx -t 2>&1')
child.expect('# ', timeout=15)
print("[nginx -t output]:", child.before.strip())

child.sendline('systemctl reload nginx && echo NGINX_RELOADED')
child.expect('NGINX_RELOADED', timeout=15)
child.expect('# ')
print("[+] Nginx reloaded successfully!")

child.sendline('exit')
child.expect(pexpect.EOF)
print("[+] Done! https://namanitwork.tech should now serve the MERN React app.")
