import os
import re
paths = ['/etc/nginx/sites-available/namanitwork.tech.conf', '/etc/nginx/sites-enabled/namanitwork.tech.conf']
for path in paths:
    if not os.path.exists(path): continue
    with open(path, 'r') as f:
        conf = f.read()
    
    conf = re.sub(r'root\s+/home/[^/]+/[^/]+/frontend/build;', r'root /home/namanit/public_html;', conf)
    conf = re.sub(r'[ \t]*location / \{(?:[^{}]|\{[^{}]*\})*\}\s*', '', conf)
    conf = re.sub(r'[ \t]*location /static/ \{(?:[^{}]|\{[^{}]*\})*\}\s*', '', conf)
    conf = re.sub(r'[ \t]*location /api/ \{(?:[^{}]|\{[^{}]*\})*\}\s*', '', conf)
    
    new_loc = "\n    location / {\n        try_files $uri $uri/ /index.html =404;\n    }\n"
    if 'location ~ /\.ht {' in conf:
        conf = conf.replace('location ~ /\.ht {', new_loc + '    location ~ /\.ht {', 1)
        
    with open(path, 'w') as f:
        f.write(conf)
