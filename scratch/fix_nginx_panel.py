import paramiko

HOST = '207.180.209.216'
PORT = 22
USER = 'root'
PASS = '19072002ROHANkumar!'

PANEL_NGINX = '''server {
    listen 8080;
    server_name 207.180.209.216 localhost;
    client_max_body_size 0;

    # /voidpanel shortcut — redirect any domain/voidpanel hit to HTTPS panel
    location = /voidpanel {
        return 301 https://fast.voidpanel.com.contaboserver.net:8082;
    }

    location /static/ {
        alias /var/www/panel/staticfiles/;
        expires 30d;
        add_header Cache-Control "public";
    }

    location /ws/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
    }

    location / {
        include         uwsgi_params;
        uwsgi_pass      unix:/var/www/panel/panel.sock;
        uwsgi_read_timeout  3600s;
        uwsgi_send_timeout  3600s;
    }
}

server {
    listen 8082 ssl;
    server_name _ fast.voidpanel.com fast.voidpanel.com.contaboserver.net 207.180.209.216;
    ssl_certificate /etc/letsencrypt/live/fast.voidpanel.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/fast.voidpanel.com/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;
    client_max_body_size 0;

    location = /voidpanel {
        return 301 /;
    }

    location /ws/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
    }

    location / {
        proxy_pass         http://127.0.0.1:8080;
        proxy_set_header   Host $http_host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }
}

# Also handle fast.voidpanel.com on port 443 for OAuth callbacks and standard redirects
server {
    listen 443 ssl;
    server_name fast.voidpanel.com;
    ssl_certificate /etc/letsencrypt/live/fast.voidpanel.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/fast.voidpanel.com/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;
    client_max_body_size 0;

    # Pass OAuth callbacks directly to panel
    location /control/social/ {
        proxy_pass         http://127.0.0.1:8080;
        proxy_set_header   Host $http_host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto https;
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }

    # Redirect all other requests to port 8082
    location / {
        return 301 https://$host:8082$request_uri;
    }
}
'''

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)

sftp = ssh.open_sftp()
with sftp.open('/etc/nginx/sites-available/panel', 'w') as f:
    f.write(PANEL_NGINX)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('nginx -t 2>&1')
test_output = stdout.read().decode()
print("=== nginx -t ===")
print(test_output)

if 'successful' in test_output:
    stdin, stdout, stderr = ssh.exec_command('systemctl reload nginx')
    print("Nginx reloaded successfully!")
else:
    print("Nginx syntax error!")

ssh.close()
