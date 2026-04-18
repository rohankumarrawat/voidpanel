import pexpect

HOST = "178.18.250.134"
USER = "root"
PASS = "19072002ROHANkumar"

child = pexpect.spawn(f'ssh -o StrictHostKeyChecking=no {USER}@{HOST}', timeout=60, encoding='utf-8')
child.expect('password:')
child.sendline(PASS)
child.expect('# ')

lines = [
    "import re, sys",
    "p='/etc/nginx/sites-enabled/namanitwork.tech.conf'",
    "try:",
    "    c = open(p).read()",
    "except FileNotFoundError:",
    "    sys.exit(1)",
    "c = re.sub(r'[ \t]*location / \\{(?:[^{}]|\\{[^{}]*\\})*\\}\\s*', '', c)",
    "c = re.sub(r'[ \t]*location /static/ \\{(?:[^{}]|\\{[^{}]*\\})*\\}\\s*', '', c)",
    "c = re.sub(r'[ \t]*location /api/ \\{(?:[^{}]|\\{[^{}]*\\})*\\}\\s*', '', c)",
    "c = re.sub(r'root\\s+/home/[^/]+/[^/]+/frontend/build;', 'root /home/namanit/yamaha/frontend/build;', c)",
    "nb = '\\n    location / {\\n        try_files $uri /index.html =404;\\n    }\\n\\n'",
    "nb += '    location /static/ {\\n        alias /home/namanit/yamaha/frontend/build/static/;\\n        expires 30d;\\n        add_header Cache-Control \"public, no-transform\";\\n    }\\n\\n'",
    "nb += '    location /api/ {\\n        proxy_pass http://127.0.0.1:3002;\\n        proxy_http_version 1.1;\\n        proxy_set_header Upgrade $http_upgrade;\\n        proxy_set_header Connection \\\'upgrade\\\';\\n        proxy_set_header Host $host;\\n        proxy_cache_bypass $http_upgrade;\\n    }\\n\\n'",
    "c = c.replace('location ~ /\\\\.ht {', nb + '    location ~ /\\\\.ht {', 1)",
    "open(p, 'w').write(c)",
    "print('DONE')"
]

child.sendline("python3 << 'EOF'")
for line in lines:
    child.sendline(line)
child.sendline("EOF")

idx = child.expect(['DONE', pexpect.TIMEOUT], timeout=15)
child.expect('# ')

child.sendline('nginx -t 2>&1')
child.expect('# ')
print("Nginx Test:", child.before.strip())

child.sendline('systemctl reload nginx')
child.expect('# ')

child.sendline('exit')
child.expect(pexpect.EOF)
print("Config fixed completely.")
