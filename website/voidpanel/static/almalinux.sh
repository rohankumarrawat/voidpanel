#!/bin/bash
set -euo pipefail

# =============================================================================
#  VoidPanel AlmaLinux / Rocky Linux / RHEL 8/9 Installer
#  Equivalent of ubuntu.sh for RHEL-family distributions.
# =============================================================================

# Global Configuration & Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RESET='\033[0m'

# Installation Log
LOG_FILE="/var/log/voidpanel_install.log"
exec > >(tee -i "$LOG_FILE") 2>&1

print_header() {
    clear
    echo -e "${CYAN}=========================================================================="
    echo "      VoidPanel Enterprise Installation Pipeline v1.0 (RHEL/AlmaLinux)"
    echo "=========================================================================="
    echo -e " Time: $(date)"
    echo -e " Logs: $LOG_FILE"
    echo -e "==========================================================================${RESET}"
}

status_msg() { echo -e "${CYAN}[+] $1...${RESET}"; }
success_msg() { echo -e "${GREEN}[✔] $1${RESET}"; }
error_msg() { echo -e "${RED}[!] $1${RESET}"; }

# Variables
PROJECT_NAME="panel"
PHP_VERSION="8.3"
PROJECT_DIR="/var/www/$PROJECT_NAME"
VENV_DIR="$PROJECT_DIR/venv"
NGINX_CONF="/etc/nginx/conf.d/${PROJECT_NAME}.conf"
PUBLIC_IP=$(curl -4 -s --max-time 8 ifconfig.me 2>/dev/null \
         || curl -4 -s --max-time 8 api.ipify.org 2>/dev/null \
         || echo "127.0.0.1")
MYSQL_ROOT_PASS=$(openssl rand -base64 16)
DJANGO_SUPERUSER_PASS=$(openssl rand -base64 16)
HOSTNAME=$(hostname)
INSTALL_START_DIR="$PWD"

# Detect RHEL major version (8 or 9)
RHEL_MAJOR=$(rpm -E %{rhel} 2>/dev/null || echo "9")

print_header

# --- 1. Environment Hardening ---
status_msg "Initializing System Update"
dnf update -y

status_msg "Installing Core Dependencies"
dnf install -y epel-release
dnf install -y curl wget git unzip perl python3 python3-pip python3-devel \
    gcc make openssl openssl-devel libffi-devel

# Enable CRB/PowerTools (needed for some build deps)
if [[ "$RHEL_MAJOR" -ge 9 ]]; then
    dnf config-manager --set-enabled crb 2>/dev/null || true
else
    dnf config-manager --set-enabled powertools 2>/dev/null || true
fi

# =============================================================================
#  WEB SERVER SELECTION — NGINX (default and only engine for this release)
# =============================================================================
VOIDPANEL_STATE_DIR="/etc/voidpanel"
VOIDPANEL_ENGINE_FILE="$VOIDPANEL_STATE_DIR/web_engine"
WEB_ENGINE="nginx"

# Persist the choice so the Django backend knows the engine immediately
mkdir -p "$VOIDPANEL_STATE_DIR"
echo "$WEB_ENGINE" > "$VOIDPANEL_ENGINE_FILE"
chmod 644 "$VOIDPANEL_ENGINE_FILE"

# --- Install NGINX (always required — serves as panel reverse proxy) ---
status_msg "Installing NGINX"
dnf install -y nginx
systemctl enable nginx 2>/dev/null || true
NGINX_CONF_DIR="/etc/nginx/conf.d"
success_msg "NGINX selected as primary web engine"

# Generate Dummy SSL for the active web server
status_msg "Generating Initial Dummy SSL Certificates"
mkdir -p /etc/nginx/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/nginx/dummy.key -out /etc/nginx/dummy.crt \
    -subj "/CN=localhost"


status_msg "Configuring PHP Repositories (Remi)"
dnf install -y https://rpms.remirepo.net/enterprise/remi-release-${RHEL_MAJOR}.rpm 2>/dev/null || true
dnf module reset php -y 2>/dev/null || true
dnf module enable php:remi-${PHP_VERSION} -y 2>/dev/null || true

# --- 2. Package Installation ---
status_msg "Installing Service Stack (LEMP + Mail + DNS)"
dnf install -y \
    php php-fpm php-mysqlnd php-mbstring php-zip php-gd php-curl \
    php-xml php-intl php-bcmath php-json php-opcache \
    mariadb-server certbot python3-certbot-nginx \
    bind bind-utils quota quota-nld \
    opendkim opendkim-tools vsftpd \
    postfix dovecot

# Generate Dummy SSL for Nginx
status_msg "Generating Initial SSL Certificates"
mkdir -p /etc/nginx/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/nginx/dummy.key -out /etc/nginx/dummy.crt \
    -subj "/CN=localhost"

# Start MariaDB early (needed for Roundcube + panel setup)
systemctl enable --now mariadb

# Secure MariaDB — set root password
status_msg "Securing MariaDB"
mysql -u root <<MSQL
ALTER USER 'root'@'localhost' IDENTIFIED BY '$MYSQL_ROOT_PASS';
FLUSH PRIVILEGES;
MSQL
# Store password so subsequent mysql calls work
cat > /root/.my.cnf <<MYCNF
[client]
user=root
password=$MYSQL_ROOT_PASS
MYCNF
chmod 600 /root/.my.cnf

# Write VoidPanel MySQL credential file (read by the panel application)
echo "$MYSQL_ROOT_PASS" > /etc/dontdelete.txt
chmod 644 /etc/dontdelete.txt

# --- 3. Panel Core Setup ---
panelsetup() {
    status_msg "Creating Project Directories"
    mkdir -p "$PROJECT_DIR"
    cd "$PROJECT_DIR"

    status_msg "Initializing Python Virtual Environment"
    python3 -m venv venv
    source venv/bin/activate

    status_msg "Installing Python Workspace Dependencies"
    pip install --upgrade pip --quiet
    if [[ -f "$PROJECT_DIR/requirements.txt" ]]; then
        pip install --quiet -r "$PROJECT_DIR/requirements.txt"
    else
        pip install --quiet django uwsgi psutil pexpect requests mysql-connector-python huggingface_hub djangorestframework django-cors-headers celery redis channels channels_redis daphne geoip2
    fi

    status_msg "Downloading GeoIP Database for Traffic Analytics"
    mkdir -p "$PROJECT_DIR/geoip"
    curl -L -s -o "$PROJECT_DIR/geoip/GeoLite2-Country.mmdb" https://github.com/P3TERX/GeoLite.mmdb/raw/download/GeoLite2-Country.mmdb

    status_msg "Deploying VoidPanel Source Code"
    if [[ -f "$INSTALL_START_DIR/Archive.zip" ]]; then
        success_msg "Local Archive.zip found, copying to project directory."
        cp "$INSTALL_START_DIR/Archive.zip" Archive.zip
    elif ! wget -q https://voidpanel.com/static/voidpanel.zip -O Archive.zip; then
        error_msg "Failed to download voidpanel.zip from voidpanel.com."
        exit 1
    fi
    unzip -o Archive.zip
    rm -f Archive.zip

    status_msg "Configuring Django Environment"
    DJANGO_SETTINGS=$(find . -name "settings.py" | grep -v venv | head -n 1)
    if [[ -z "$DJANGO_SETTINGS" ]]; then
        error_msg "settings.py not found — check Archive.zip contents"
        exit 1
    fi

    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))")
    echo "$SECRET_KEY" > "$PROJECT_DIR/.secret_key"
    chmod 600 "$PROJECT_DIR/.secret_key"
    chown nginx:nginx "$PROJECT_DIR/.secret_key"

    cat > "$PROJECT_DIR/.env" <<ENVFILE
DJANGO_SECRET_KEY=${SECRET_KEY}
DJANGO_ALLOWED_HOSTS=*
DJANGO_CSRF_ORIGINS=http://${PUBLIC_IP}:8080,https://${PUBLIC_IP}:8082,http://${PUBLIC_IP},https://${PUBLIC_IP}
DJANGO_DEBUG=false
ENVFILE
    chmod 640 "$PROJECT_DIR/.env"
    chown nginx:nginx "$PROJECT_DIR/.env"

    cat >> "$DJANGO_SETTINGS" <<PYEOF

# ── Production CSRF & Host config injected by installer ──────────────────────
_PANEL_IP = '${PUBLIC_IP}'
_PANEL_HOST = '${HOSTNAME}'
CSRF_TRUSTED_ORIGINS = [
    f'http://{_PANEL_IP}',
    f'http://{_PANEL_IP}:8080',
    f'https://{_PANEL_IP}',
    f'https://{_PANEL_IP}:8082',
    f'http://{_PANEL_HOST}',
    f'http://{_PANEL_HOST}:8080',
    f'https://{_PANEL_HOST}',
    f'https://{_PANEL_HOST}:8082',
]
ALLOWED_HOSTS = ['*', _PANEL_IP, _PANEL_HOST, 'localhost', '127.0.0.1']

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
PYEOF

    status_msg "Running Django migrations"
    python manage.py makemigrations --no-input 2>/dev/null || true
    python manage.py migrate --noinput
    python manage.py collectstatic --noinput --clear 2>/dev/null || true

    # ── Inject VoidPanel website URL into .env for SSO token validation ───────
    status_msg "Configuring SSO website URL"
    if ! grep -q "VOIDPANEL_WEBSITE_URL" "$PROJECT_DIR/.env" 2>/dev/null; then
        echo "VOIDPANEL_WEBSITE_URL=https://voidpanel.com" >> "$PROJECT_DIR/.env"
    fi

    # ── Inject VOIDPANEL_WEBSITE_URL into Django settings ─────────────────────
    if ! grep -q "VOIDPANEL_WEBSITE_URL" "$DJANGO_SETTINGS" 2>/dev/null; then
        cat >> "$DJANGO_SETTINGS" <<PYEOF

# SSO — URL of the voidpanel.com website (used to validate one-time SSO tokens)
import os as _os
VOIDPANEL_WEBSITE_URL = _os.environ.get('VOIDPANEL_WEBSITE_URL', 'https://voidpanel.com')
PYEOF
    fi

    status_msg "Running first-run setup (license placeholder)"
    python manage.py first_run_setup 2>/dev/null || {
        python manage.py shell <<PYEOF
import secrets, socket
from control.models import PanelLicense
if not PanelLicense.objects.exists():
    PanelLicense.objects.create(
        key='PENDING-' + secrets.token_hex(16),
        email='',
        status='pending_activation',
        hostname=socket.getfqdn(),
    )
    print("Placeholder license created.")
else:
    print("License already exists, skipping.")
PYEOF
    }

    status_msg "Creating admin superuser"
    python manage.py shell <<PYEOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@voidpanel.com', '${DJANGO_SUPERUSER_PASS}')
    print("Superuser created.")
else:
    print("Superuser already exists.")
PYEOF

    status_msg "Configuring uWSGI Engine"
    cat << EOF > "$PROJECT_DIR/panel.ini"
[uwsgi]
chdir = $PROJECT_DIR
module = panel.wsgi:application
home = $VENV_DIR
master = true
processes = 4
socket = $PROJECT_DIR/panel.sock
chmod-socket = 660
uid = nginx
gid = nginx
vacuum = true
die-on-term = true
logto = /var/log/voidpanel/uwsgi.log
EOF

    mkdir -p /var/log/voidpanel
    touch /var/log/voidpanel/uwsgi.log /var/log/voidpanel/panel.log /var/log/voidpanel/celery.log /var/log/voidpanel/celery-beat.log
    chown -R nginx:nginx /var/log/voidpanel
    chmod 750 /var/log/voidpanel

    cat << EOF > /etc/systemd/system/uwsgi.service
[Unit]
Description=uWSGI service for VoidPanel
After=network.target mariadb.service redis.service
Wants=mariadb.service redis.service

[Service]
Type=simple
User=nginx
Group=nginx
WorkingDirectory=$PROJECT_DIR
EnvironmentFile=$PROJECT_DIR/.env
ExecStart=$VENV_DIR/bin/uwsgi --ini $PROJECT_DIR/panel.ini
Restart=on-failure
RestartSec=5s
KillSignal=SIGQUIT
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
EOF

    cat > /etc/systemd/system/voidpanel-daphne.service <<SVC
[Unit]
Description=VoidPanel Daphne ASGI Application Server
After=network.target redis-server.service
Wants=redis-server.service

[Service]
Type=simple
User=nginx
Group=nginx
WorkingDirectory=${PROJECT_DIR}
EnvironmentFile=${PROJECT_DIR}/.env
ExecStart=${VENV_DIR}/bin/daphne -b 127.0.0.1 -p 8001 panel.asgi:application
Restart=on-failure
RestartSec=5s
LimitNOFILE=65535

[Install]
WantedBy=multi-user.target
SVC

    cat > /etc/systemd/system/voidpanel-backup.service <<SVC
[Unit]
Description=VoidPanel Backup Dashboard (Always-On Port 8081)
After=network.target redis-server.service mysql.service
Wants=redis-server.service mysql.service

[Service]
Type=simple
User=root
WorkingDirectory=${PROJECT_DIR}
EnvironmentFile=${PROJECT_DIR}/.env
Environment=PYTHONPATH=${PROJECT_DIR}
Environment=DJANGO_SETTINGS_MODULE=panel.settings
ExecStart=${VENV_DIR}/bin/daphne -b 0.0.0.0 -p 8081 panel.asgi:application
Restart=always
RestartSec=5s

[Install]
WantedBy=multi-user.target
SVC

    status_msg "Installing Celery services"
    mkdir -p /var/run/celery
    chown nginx:nginx /var/run/celery
    cat > /etc/systemd/system/voidpanel-celery.service <<SVC
[Unit]
Description=VoidPanel Celery Worker
After=network.target redis-server.service mariadb.service
Wants=redis-server.service mariadb.service

[Service]
Type=simple
User=nginx
Group=nginx
WorkingDirectory=${PROJECT_DIR}
EnvironmentFile=${PROJECT_DIR}/.env
Environment=PYTHONPATH=${PROJECT_DIR}
Environment=DJANGO_SETTINGS_MODULE=panel.settings
ExecStart=${VENV_DIR}/bin/celery -A panel worker \\
    --loglevel=info \\
    --concurrency=4 \\
    --logfile=/var/log/voidpanel/celery.log
Restart=on-failure
RestartSec=10s
KillSignal=SIGTERM
TimeoutStopSec=60

[Install]
WantedBy=multi-user.target
SVC

    cat > /etc/systemd/system/voidpanel-celery-beat.service <<SVC
[Unit]
Description=VoidPanel Celery Beat Scheduler
After=network.target redis-server.service mariadb.service voidpanel-celery.service
Wants=redis-server.service mariadb.service voidpanel-celery.service

[Service]
Type=simple
User=nginx
Group=nginx
WorkingDirectory=${PROJECT_DIR}
EnvironmentFile=${PROJECT_DIR}/.env
Environment=PYTHONPATH=${PROJECT_DIR}
Environment=DJANGO_SETTINGS_MODULE=panel.settings
ExecStart=${VENV_DIR}/bin/celery -A panel beat \\
    --loglevel=info \\
    --logfile=/var/log/voidpanel/celery-beat.log \\
    --scheduler django_celery_beat.schedulers:DatabaseScheduler
Restart=on-failure
RestartSec=10s
KillSignal=SIGTERM

[Install]
WantedBy=multi-user.target
SVC

    echo "nginx ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/voidpanel
    chmod 440 /etc/sudoers.d/voidpanel

    status_msg "Configuring Nginx High-Performance Bridge"
    cat << EOF > "$NGINX_CONF"
server {
    listen 8080;
    server_name $PUBLIC_IP localhost;
    client_max_body_size 0;

    # /voidpanel shortcut — redirect any domain/voidpanel hit to HTTPS panel
    location = /voidpanel {
        return 301 https://$HOSTNAME:8082;
    }

    location /static/ {
        alias $PROJECT_DIR/staticfiles/;
        expires 30d;
        add_header Cache-Control "public";
    }

    location /ws/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
    }

    location / {
        include uwsgi_params;
        uwsgi_pass unix:$PROJECT_DIR/panel.sock;
        uwsgi_read_timeout 3600s;
        uwsgi_send_timeout 3600s;
    }
}

server {
    listen 8082 ssl;
    server_name $PUBLIC_IP $HOSTNAME;

    ssl_certificate /etc/nginx/dummy.crt;
    ssl_certificate_key /etc/nginx/dummy.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    client_max_body_size 0;

    # /voidpanel shortcut on HTTPS — already on panel, just go to root
    location = /voidpanel {
        return 301 /;
    }

    location /ws/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
    }

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }
}
EOF

    if [[ -f /etc/nginx/conf.d/default.conf ]]; then
        mv /etc/nginx/conf.d/default.conf /etc/nginx/conf.d/default.conf.disabled
    fi

    # ── Permissions & Media Setup ─────────────────────────────────────────────
    status_msg "Creating Media Directories"
    mkdir -p "$PROJECT_DIR/media/wa_campaigns" "$PROJECT_DIR/media/wa_broadcasts"

    status_msg "Applying Permission Hardening"
    chown -R nginx:nginx "$PROJECT_DIR"
    chmod -R 750 "$PROJECT_DIR"
    chmod -R 775 "$PROJECT_DIR/media"
    chmod 711 /home

    if command -v setsebool &>/dev/null; then
        status_msg "Configuring SELinux policies"
        setsebool -P httpd_can_network_connect 1 2>/dev/null || true
        setsebool -P httpd_read_user_content 1 2>/dev/null || true
        setsebool -P httpd_enable_homedirs 1 2>/dev/null || true
        chcon -R -t httpd_sys_rw_content_t "$PROJECT_DIR" 2>/dev/null || true
    fi

    # ── WhatsApp Web Microservice (Baileys — Self-Hosted, Zero Third-Party) ─────
    status_msg "Setting up WhatsApp Web microservice (Baileys)"
    WA_DIR="$PROJECT_DIR/wa_service"

    NODE_BIN=""
    for candidate in /usr/local/bin/node /usr/bin/node; do
        if [[ -x "$candidate" ]]; then
            NODE_VER=$("$candidate" -e "console.log(parseInt(process.versions.node.split('.')[0]))" 2>/dev/null)
            if [[ "$NODE_VER" -ge 18 ]]; then
                NODE_BIN="$candidate"
                break
            fi
        fi
    done

    if [[ -z "$NODE_BIN" ]]; then
        status_msg "Installing Node.js 20 LTS"
        dnf module reset nodejs -y 2>/dev/null || true
        dnf module enable nodejs:20 -y 2>/dev/null || true
        dnf install -y nodejs
        NODE_BIN="/usr/bin/node"
    fi

    # Install npm dependencies
    if [[ -d "$WA_DIR" ]]; then
        cd "$WA_DIR"
        npm install --omit=dev --prefer-offline >/dev/null 2>&1
        cd "$PROJECT_DIR"

        # Write systemd service with correct node path
        cat > /etc/systemd/system/voidpanel-wa.service <<EOF
[Unit]
Description=VoidPanel WhatsApp Web Microservice (Baileys)
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$WA_DIR
ExecStart=$NODE_BIN $WA_DIR/server.js
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=voidpanel-wa
Environment=NODE_ENV=production
Environment=PATH=/usr/local/bin:/usr/bin:/bin
Environment=HOST=127.0.0.1
Environment=PORT=3001

[Install]
WantedBy=multi-user.target
EOF

        systemctl daemon-reload
        systemctl enable voidpanel-wa
        systemctl start  voidpanel-wa
        sleep 2
        if systemctl is-active --quiet voidpanel-wa; then
            success_msg "WhatsApp Web microservice is running"
        else
            echo "[WARN] voidpanel-wa service failed to start"
        fi
    else
        echo "[WARN] wa_service directory not found at $WA_DIR — skipping WhatsApp setup"
    fi

    systemctl daemon-reload
    systemctl enable uwsgi voidpanel-daphne voidpanel-backup voidpanel-celery voidpanel-celery-beat voidpanel-wa
    systemctl start uwsgi voidpanel-daphne voidpanel-backup voidpanel-celery voidpanel-celery-beat voidpanel-wa
    success_msg "Panel Core Setup Complete"
}

# --- 4. DNS (BIND/named) Configuration ---
bindsetup() {
    status_msg "Configuring Authoritative DNS (BIND/named)"
    cp /etc/named.conf /etc/named.conf.backup 2>/dev/null || true

    cat << EOF > /etc/named.conf
options {
    listen-on port 53 { any; };
    listen-on-v6 port 53 { any; };
    directory "/var/named";
    dump-file "/var/named/data/cache_dump.db";
    statistics-file "/var/named/data/named_stats.txt";
    allow-query { any; };
    recursion yes;
    forwarders { 8.8.8.8; 8.8.4.4; 1.1.1.1; };
    dnssec-validation auto;
};

logging {
    channel default_debug {
        file "data/named.run";
        severity dynamic;
    };
};

zone "." IN {
    type hint;
    file "named.ca";
};

include "/etc/named.rfc1912.zones";
include "/etc/named.root.key";
include "/etc/named.conf.local";
EOF

    # Create named.conf.local if missing (VoidPanel adds zones here)
    touch /etc/named.conf.local

    systemctl enable --now named
    systemctl restart named
    success_msg "DNS Service Configured"
}

# --- 5. Storage Quota Setup ---
quotasetup() {
    status_msg "Initializing Filesystem Quotas"
    # RHEL/AlmaLinux: XFS uses xfs_quota (project quotas), ext4 uses standard quota
    ROOT_FS_TYPE=$(df -T / | awk 'NR==2{print $2}')
    if [[ "$ROOT_FS_TYPE" == "xfs" ]]; then
        # XFS — enable user quota via mount option
        if ! grep -q "uquota" /etc/fstab; then
            sed -i 's/defaults/defaults,uquota,gquota/' /etc/fstab
            status_msg "Quota mount options added — reboot may be required for XFS quotas"
        fi
    else
        # ext4 fallback
        if ! grep -q "usrquota" /etc/fstab; then
            sed -i "s/defaults/defaults,usrquota,grpquota/g" /etc/fstab
            mount -o remount / 2>/dev/null || true
        fi
        quotacheck -ugm / > /dev/null 2>&1 || true
        quotaon -v / > /dev/null 2>&1 || true
    fi
    success_msg "Quotas Configured"
}

# --- 6. Roundcube Webmail Setup ---
roundcubesetup() {
    status_msg "Preparing Roundcube Database"
    DB_NAME="roundcube"
    DB_USER="roundcube"
    DB_PASS=$(openssl rand -base64 16)

    mysql <<RSQL
CREATE DATABASE IF NOT EXISTS $DB_NAME;
DROP USER IF EXISTS '$DB_USER'@'localhost';
CREATE USER '$DB_USER'@'localhost' IDENTIFIED BY '$DB_PASS';
GRANT ALL PRIVILEGES ON $DB_NAME.* TO '$DB_USER'@'localhost';
FLUSH PRIVILEGES;
RSQL

    status_msg "Downloading Roundcube Webmail"
    mkdir -p /var/www/roundcube
    cd /var/www/
    wget -q https://github.com/roundcube/roundcubemail/releases/download/1.6.9/roundcubemail-1.6.9-complete.tar.gz
    tar -xzf roundcubemail-1.6.9-complete.tar.gz
    mv roundcubemail-1.6.9/* roundcube/
    rm -rf roundcubemail-1.6.9*

    status_msg "Configuring Roundcube"
    cd roundcube
    cp config/config.inc.php.sample config/config.inc.php
    sed -i "s|.*db_dsnw.*|\$config['db_dsnw'] = 'mysql://$DB_USER:$DB_PASS@localhost/$DB_NAME';|" config/config.inc.php

    # ── Write IMAP + SMTP settings ────────────────────────────────────────────
    cat >> config/config.inc.php << 'RCCONF'

// ── VoidPanel: IMAP ────────────────────────────────────────────────────────
$config['imap_host'] = 'ssl://localhost:993';
$config['imap_auth_type'] = 'LOGIN';
$config['imap_conn_options'] = array(
    'ssl' => array(
        'verify_peer'       => false,
        'verify_peer_name'  => false,
        'allow_self_signed' => true,
    ),
);

// ── VoidPanel: SMTP ────────────────────────────────────────────────────────
$config['smtp_host'] = 'tls://localhost:587';
$config['smtp_port'] = 587;
$config['smtp_user'] = '%u';
$config['smtp_pass'] = '%p';
$config['smtp_auth_type'] = 'LOGIN';
$config['smtp_conn_options'] = array(
    'ssl' => array(
        'verify_peer'       => false,
        'verify_peer_name'  => false,
        'allow_self_signed' => true,
    ),
);

// ── VoidPanel: General ─────────────────────────────────────────────────────
$config['product_name']     = 'VoidPanel Webmail';
$config['session_lifetime'] = 60;
$config['default_charset']  = 'UTF-8';
$config['enable_installer'] = false;
$config['login_lc']         = 2;
RCCONF

    # Determine PHP-FPM socket path (RHEL uses /var/run/php-fpm/www.sock or /run/php-fpm/www.sock)
    PHP_FPM_SOCK="/run/php-fpm/www.sock"

    status_msg "Configuring Roundcube Nginx"
    cat << EOF > /etc/nginx/conf.d/roundcube.conf
server {
    listen 9000;
    server_name $PUBLIC_IP;
    root /var/www/roundcube;
    index index.php;

    location / { try_files \$uri \$uri/ /index.php; }
    location ~ \.php\$ {
        fastcgi_pass unix:$PHP_FPM_SOCK;
        fastcgi_index index.php;
        fastcgi_param SCRIPT_FILENAME \$document_root\$fastcgi_script_name;
        include fastcgi_params;
    }
}

server {
    listen 9002 ssl http2;
    server_name $PUBLIC_IP $HOSTNAME;
    ssl_certificate /etc/nginx/dummy.crt;
    ssl_certificate_key /etc/nginx/dummy.key;
    root /var/www/roundcube;
    index index.php;

    location / { try_files \$uri \$uri/ /index.php; }
    location ~ \.php\$ {
        fastcgi_pass unix:$PHP_FPM_SOCK;
        fastcgi_index index.php;
        fastcgi_param SCRIPT_FILENAME \$document_root\$fastcgi_script_name;
        include fastcgi_params;
    }
}
EOF

    chown -R nginx:nginx /var/www/roundcube
    if command -v chcon &>/dev/null; then
        chcon -R -t httpd_sys_rw_content_t /var/www/roundcube 2>/dev/null || true
    fi
    success_msg "Roundcube Webmail Stack Integrated"
}

# --- 7. FTP (vsftpd) Setup ---
ftpsetup() {
    status_msg "Configuring vsftpd Server"
    cp /etc/vsftpd/vsftpd.conf /etc/vsftpd/vsftpd.conf.bak 2>/dev/null || true

    cat << EOF > /etc/vsftpd/vsftpd.conf
listen=YES
listen_ipv6=NO
anonymous_enable=NO
local_enable=YES
write_enable=YES
local_umask=022
dirmessage_enable=YES
use_localtime=YES
xferlog_enable=YES
connect_from_port_20=YES
chroot_local_user=YES
allow_writeable_chroot=YES
pam_service_name=vsftpd
userlist_enable=YES
pasv_min_port=40000
pasv_max_port=50000
EOF

    systemctl enable --now vsftpd
    systemctl restart vsftpd
    success_msg "FTP Service Hardened"
}

# --- 8. phpMyAdmin Setup ---
phpmyadminsetup() {
    status_msg "Integrating phpMyAdmin"
    # phpMyAdmin is not in default RHEL repos — download manually
    PMA_VERSION="5.2.1"
    mkdir -p /usr/share/phpmyadmin
    cd /usr/share/
    wget -q "https://files.phpmyadmin.net/phpMyAdmin/${PMA_VERSION}/phpMyAdmin-${PMA_VERSION}-all-languages.tar.gz"
    tar -xzf "phpMyAdmin-${PMA_VERSION}-all-languages.tar.gz"
    mv "phpMyAdmin-${PMA_VERSION}-all-languages/"* phpmyadmin/
    rm -rf "phpMyAdmin-${PMA_VERSION}-all-languages"*

    # Create config
    cp /usr/share/phpmyadmin/config.sample.inc.php /usr/share/phpmyadmin/config.inc.php
    PMA_SECRET=$(openssl rand -base64 24 | head -c 32)
    sed -i "s|\$cfg\['blowfish_secret'\] = ''|\$cfg['blowfish_secret'] = '$PMA_SECRET'|" /usr/share/phpmyadmin/config.inc.php

    # Create tmp dir for phpMyAdmin
    mkdir -p /usr/share/phpmyadmin/tmp
    chown -R nginx:nginx /usr/share/phpmyadmin

    PHP_FPM_SOCK="/run/php-fpm/www.sock"

    status_msg "Configuring phpMyAdmin Nginx"
    cat << EOF > /etc/nginx/conf.d/phpmyadmin.conf
server {
    listen 8090;
    client_max_body_size 256M;
    server_name $PUBLIC_IP;
    root /usr/share/phpmyadmin;
    index index.php;

    location / { try_files \$uri \$uri/ =404; }
    location ~ \.php\$ {
        fastcgi_pass unix:$PHP_FPM_SOCK;
        fastcgi_index index.php;
        fastcgi_param SCRIPT_FILENAME \$document_root\$fastcgi_script_name;
        fastcgi_read_timeout 600;
        fastcgi_send_timeout 600;
        include fastcgi_params;
    }
    location ~ /\.(ht|svn|git) { deny all; }
}

server {
    listen 8092 ssl http2;
    client_max_body_size 256M;
    server_name $PUBLIC_IP $HOSTNAME;
    ssl_certificate /etc/nginx/dummy.crt;
    ssl_certificate_key /etc/nginx/dummy.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    root /usr/share/phpmyadmin;
    index index.php;

    location / { try_files \$uri \$uri/ =404; }
    location ~ \.php\$ {
        fastcgi_pass unix:$PHP_FPM_SOCK;
        fastcgi_index index.php;
        fastcgi_param SCRIPT_FILENAME \$document_root\$fastcgi_script_name;
        fastcgi_read_timeout 600;
        fastcgi_send_timeout 600;
        include fastcgi_params;
    }
    location ~ /\.(ht|svn|git) { deny all; }
}
EOF

    if command -v chcon &>/dev/null; then
        chcon -R -t httpd_sys_rw_content_t /usr/share/phpmyadmin 2>/dev/null || true
    fi

    # ── Tune PHP-FPM ini for large DB imports via phpMyAdmin ──────────────────
    status_msg "Tuning PHP-FPM limits for phpMyAdmin imports"
    # AlmaLinux/RHEL PHP-FPM ini is typically in /etc/php.ini or /etc/php.d/
    for PHP_FPM_INI in /etc/php.ini /etc/php/php.ini /etc/php81/php.ini /etc/php80/php.ini; do
        if [[ -f "$PHP_FPM_INI" ]]; then
            sed -i 's/^upload_max_filesize = .*/upload_max_filesize = 256M/'  "$PHP_FPM_INI"
            sed -i 's/^post_max_size = .*/post_max_size = 256M/'              "$PHP_FPM_INI"
            sed -i 's/^max_execution_time = .*/max_execution_time = 600/'     "$PHP_FPM_INI"
            sed -i 's/^max_input_time = .*/max_input_time = 600/'             "$PHP_FPM_INI"
            CURRENT_MEM=$(grep '^memory_limit' "$PHP_FPM_INI" | grep -oP '\d+' | head -1)
            if [[ -z "$CURRENT_MEM" || "$CURRENT_MEM" -lt 512 ]]; then
                sed -i 's/^memory_limit = .*/memory_limit = 512M/' "$PHP_FPM_INI"
            fi
            ok "PHP ini tuned at $PHP_FPM_INI: upload=256M post=256M exec=600s"
            break
        fi
    done
    # Also write a php-fpm drop-in for www pool if /etc/php-fpm.d/www.conf exists
    if [[ -f /etc/php-fpm.d/www.conf ]]; then
        PHP_FPM_POOL=/etc/php-fpm.d/www.conf
        grep -q '^php_admin_value\[upload_max_filesize\]' "$PHP_FPM_POOL" || \
            echo 'php_admin_value[upload_max_filesize] = 256M'  >> "$PHP_FPM_POOL"
        grep -q '^php_admin_value\[post_max_size\]' "$PHP_FPM_POOL" || \
            echo 'php_admin_value[post_max_size] = 256M'        >> "$PHP_FPM_POOL"
        grep -q '^php_admin_value\[max_execution_time\]' "$PHP_FPM_POOL" || \
            echo 'php_admin_value[max_execution_time] = 600'    >> "$PHP_FPM_POOL"
        grep -q '^php_admin_value\[memory_limit\]' "$PHP_FPM_POOL" || \
            echo 'php_admin_value[memory_limit] = 512M'         >> "$PHP_FPM_POOL"
        ok "PHP-FPM www pool tuned"
    fi

    # ── Deploy VoidPanel SSO gateway for phpMyAdmin ───────────────────────────
    status_msg "Deploying phpMyAdmin SSO gateway"
    cat > /usr/share/phpmyadmin/vp_sso.php << 'PMASSOEOF'
<?php
/**
 * VoidPanel phpMyAdmin Single Sign-On gateway
 * Called via cross-origin form POST from the VoidPanel dashboard.
 * Sets the PMA signon session then redirects to phpMyAdmin index.
 */
session_name('phpMyAdmin');
$port = (int)$_SERVER['SERVER_PORT'];
$secure = ($port === 8092);  // HTTPS port
ini_set('session.cookie_samesite', 'None');
if ($secure) { ini_set('session.cookie_secure', '1'); }
ini_set('session.cookie_httponly', '0');
session_start();
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(200);
    echo '<!DOCTYPE html><html><head><title>VoidPanel Database Access</title>';
    echo '<meta http-equiv="refresh" content="0;url=index.php">';
    echo '</head><body><p>Redirecting to phpMyAdmin...</p>';
    echo '<script>window.location.href="index.php";</script></body></html>';
    exit;
}
$user     = isset($_POST['temp_user'])     ? trim($_POST['temp_user'])     : '';
$password = isset($_POST['temp_password']) ? trim($_POST['temp_password']) : '';
if (empty($user) || empty($password)) { http_response_code(400); die('Missing credentials.'); }
if (!preg_match('/^vp_temp_[a-z0-9]+$/', $user)) { http_response_code(403); die('Forbidden.'); }
$_SESSION['PMA_single_signon_user']     = $user;
$_SESSION['PMA_single_signon_password'] = $password;
$_SESSION['PMA_single_signon_host']     = 'localhost';
$_SESSION['PMA_single_signon_port']     = '3306';
session_write_close();
header('Location: index.php');
exit;
PMASSOEOF
    chown nginx:nginx /usr/share/phpmyadmin/vp_sso.php
    chmod 640 /usr/share/phpmyadmin/vp_sso.php
    if command -v chcon &>/dev/null; then
        chcon -t httpd_sys_content_t /usr/share/phpmyadmin/vp_sso.php 2>/dev/null || true
    fi

    # ── Configure phpMyAdmin SSO auth ────────────────────────────────────────
    PMA_CONF="/usr/share/phpmyadmin/config.inc.php"
    if [[ -f "$PMA_CONF" ]]; then
        if ! grep -q "PMA_single_signon" "$PMA_CONF" 2>/dev/null; then
            cat >> "$PMA_CONF" << 'PMACONF'
$cfg['Servers'][1]['auth_type']       = 'signon';
$cfg['Servers'][1]['SignonSession']   = 'phpMyAdmin';
$cfg['Servers'][1]['SignonURL']       = '/vp_sso.php';
$cfg['Servers'][1]['LogoutURL']       = '/vp_sso.php';
PMACONF
        fi
    fi

    success_msg "Database Management Stack Integrated"
}

# --- 9. Email (Postfix & Dovecot) Setup ---
emailsetup() {
    status_msg "Configuring Enterprise Mail Stack (Postfix/Dovecot)"

    # Mail user (owns all mailboxes)
    groupadd -g 5000 vmail 2>/dev/null || true
    useradd -s /sbin/nologin -u 5000 -g 5000 -d /home/vmail vmail 2>/dev/null || true
    usermod -aG nginx vmail 2>/dev/null || true
    mkdir -p /home/vmail/mail
    chown -R vmail:vmail /home/vmail

    # ── Postfix main.cf ─────────────────────────────────────────────────────────
    cat << EOF > /etc/postfix/main.cf
myhostname = $HOSTNAME
myorigin = \$myhostname
smtpd_banner = \$myhostname ESMTP VoidPanel
biff = no
append_dot_mydomain = no
readme_directory = no

# TLS parameters
smtpd_tls_cert_file=/etc/nginx/dummy.crt
smtpd_tls_key_file=/etc/nginx/dummy.key
smtpd_use_tls=yes
smtpd_tls_auth_only = yes
smtpd_tls_security_level = may
smtpd_tls_protocols = !SSLv2, !SSLv3
smtp_tls_security_level = may

# SASL
smtpd_sasl_type = dovecot
smtpd_sasl_path = private/auth
smtpd_sasl_auth_enable = yes

# Virtual Mailbox Settings — delivery handled by Dovecot LMTP
virtual_mailbox_domains = /etc/postfix/virtual_domains
virtual_mailbox_maps = hash:/etc/postfix/vmailbox
virtual_alias_maps = hash:/etc/postfix/virtual_alias
virtual_transport = lmtp:unix:private/dovecot-lmtp
inet_protocols = ipv4

# Milter configuration
milter_protocol = 6
milter_default_action = accept
smtpd_milters = inet:127.0.0.1:8891
non_smtpd_milters = inet:127.0.0.1:8891

# Standard SMTP Restrictions
smtpd_recipient_restrictions = check_recipient_access hash:/etc/postfix/vp_suspended_incoming, check_policy_service unix:private/voidpanel-mail-policy, permit_sasl_authenticated, permit_mynetworks, reject_unauth_destination
smtpd_sender_restrictions = check_sender_access hash:/etc/postfix/vp_suspended_outgoing, permit_sasl_authenticated, permit_mynetworks, reject_unauth_destination
EOF

    # Initialize empty suspension maps
    touch /etc/postfix/vp_suspended_incoming /etc/postfix/vp_suspended_outgoing
    postmap /etc/postfix/vp_suspended_incoming /etc/postfix/vp_suspended_outgoing

    # ── Postfix master.cf — ports 25, 587 (submission), 465 (smtps) ─────────────
    cat > /etc/postfix/master.cf <<'EOF'
# ==========================================================================
# service type  private unpriv  chroot  wakeup  maxproc command + args
# ==========================================================================
smtp       inet  n       -       n       -       -       smtpd
0.0.0.0:587    inet  n       -       n       -       -       smtpd
  -o syslog_name=postfix/submission
  -o smtpd_tls_security_level=encrypt
  -o smtpd_sasl_auth_enable=yes
  -o smtpd_sasl_type=dovecot
  -o smtpd_sasl_path=private/auth
  -o smtpd_relay_restrictions=permit_sasl_authenticated,reject
  -o smtpd_recipient_restrictions=check_policy_service,unix:private/voidpanel-mail-policy,permit_sasl_authenticated,reject
  -o milter_macro_daemon_name=ORIGINATING
0.0.0.0:465    inet  n       -       n       -       -       smtpd
  -o syslog_name=postfix/smtps
  -o smtpd_tls_wrappermode=yes
  -o smtpd_sasl_auth_enable=yes
  -o smtpd_sasl_type=dovecot
  -o smtpd_sasl_path=private/auth
  -o smtpd_relay_restrictions=permit_sasl_authenticated,reject
  -o smtpd_recipient_restrictions=check_policy_service,unix:private/voidpanel-mail-policy,permit_sasl_authenticated,reject
  -o milter_macro_daemon_name=ORIGINATING
pickup     unix  n       -       n       60      1       pickup
cleanup    unix  n       -       n       -       0       cleanup
qmgr       unix  n       -       n       300     1       qmgr
tlsmgr     unix  -       -       n       1000?   1       tlsmgr
rewrite    unix  -       -       n       -       -       trivial-rewrite
bounce     unix  -       -       n       -       0       bounce
defer      unix  -       -       n       -       0       bounce
trace      unix  -       -       n       -       0       bounce
verify     unix  -       -       n       -       1       verify
flush      unix  n       -       n       1000?   0       flush
proxymap   unix  -       -       n       -       -       proxymap
proxywrite unix  -       -       n       -       1       proxymap
smtp       unix  -       -       n       -       -       smtp
relay      unix  -       -       n       -       -       smtp
showq      unix  n       -       n       -       -       showq
error      unix  -       -       n       -       -       error
retry      unix  -       -       n       -       -       error
discard    unix  -       -       n       -       -       discard
local      unix  -       n       n       -       -       local
virtual    unix  -       n       n       -       -       virtual
lmtp       unix  -       -       n       -       -       lmtp
anvil      unix  -       -       n       -       1       anvil
scache     unix  -       -       n       -       1       scache
EOF

    touch /etc/postfix/virtual_domains /etc/postfix/vmailbox /etc/postfix/virtual_alias
    postmap /etc/postfix/virtual_alias /etc/postfix/vmailbox

    # ── Dovecot core config ──────────────────────────────────────────────────────
    cat << EOF > /etc/dovecot/dovecot.conf
protocols = imap pop3 lmtp
listen = *, ::
!include conf.d/*.conf
!include_try /usr/share/dovecot/protocols.d/*.conf
EOF

    # ── Dovecot master service — IMAP/POP3 port listeners + auth + LMTP ─────────
    cat << EOF > /etc/dovecot/conf.d/10-master.conf
service imap-login {
  inet_listener imap {
    port = 143
  }
  inet_listener imaps {
    port = 993
    ssl = yes
  }
}
service pop3-login {
  inet_listener pop3 {
    port = 110
  }
  inet_listener pop3s {
    port = 995
    ssl = yes
  }
}
service auth {
  unix_listener /var/spool/postfix/private/auth {
    mode = 0660
    user = postfix
    group = postfix
  }
}

service lmtp {
  unix_listener /var/spool/postfix/private/dovecot-lmtp {
    mode = 0600
    user = postfix
    group = postfix
  }
}
EOF

    # ── Dovecot SSL config ───────────────────────────────────────────────────────
    cat << EOF > /etc/dovecot/conf.d/10-ssl.conf
ssl = yes
ssl_cert = </etc/nginx/dummy.crt
ssl_key  = </etc/nginx/dummy.key
ssl_min_protocol = TLSv1.2
ssl_prefer_server_ciphers = yes
EOF

    cat << EOF > /etc/dovecot/conf.d/10-auth.conf
disable_plaintext_auth = yes
auth_mechanisms = plain login
# Virtual users from /etc/dovecot/users (passwd-file format)
passdb {
  driver = passwd-file
  args = /etc/dovecot/users
}
userdb {
  driver = passwd-file
  args = /etc/dovecot/users
  default_fields = uid=vmail gid=vmail
}
EOF

    # Mail location: use the home path from userdb for each account
    cat << EOF > /etc/dovecot/conf.d/10-mail.conf
mail_location = maildir:%h/Maildir
namespace inbox {
  inbox = yes
}
mail_uid = vmail
mail_gid = vmail
EOF

    # Initialize the user registry
    touch /etc/dovecot/users
    chown vmail:vmail /etc/dovecot/users
    chmod 660 /etc/dovecot/users

    # ── OpenDKIM configuration ─────────────────────────────────────────────────
    status_msg "Configuring OpenDKIM"
    mkdir -p /etc/opendkim/keys
    cat > /etc/opendkim.conf <<'EOF'
Syslog                  yes
RequiredHeaders         yes
UMask                   007
Mode                    sv
Socket                  inet:8891@127.0.0.1
PidFile                 /run/opendkim/opendkim.pid
OversignHeaders         From
TrustAnchorFile         /usr/share/dns/root.key

KeyTable                /etc/opendkim/KeyTable
SigningTable            refile:/etc/opendkim/SigningTable
TrustedHosts            /etc/opendkim/TrustedHosts
EOF

    # Create empty OpenDKIM tables if they don't exist
    touch /etc/opendkim/KeyTable /etc/opendkim/SigningTable /etc/opendkim/TrustedHosts
    echo "127.0.0.1" > /etc/opendkim/TrustedHosts
    echo "localhost" >> /etc/opendkim/TrustedHosts

    # Set proper ownership and permissions
    chown -R opendkim:opendkim /etc/opendkim
    chmod -R 700 /etc/opendkim

    # Create voidemail wrapper script for API v2
    cat > /usr/bin/voidemail <<'EOF'
#!/bin/bash
action=$1
email=$2
password=$3

if [ "$action" = "add" ]; then
    bash /var/www/panel/emailadd.sh "$email" "$password"
elif [ "$action" = "del" ]; then
    sed -i "/^${email}:/d" /etc/dovecot/users
    systemctl reload dovecot || true
elif [ "$action" = "chpass" ]; then
    HASH=$(doveadm pw -s SHA512-CRYPT -p "$password")
    sed -i "s|^${email}:[^:]*|${email}:${HASH}|" /etc/dovecot/users
    systemctl reload dovecot || true
fi
EOF
    chmod +x /usr/bin/voidemail

    # ── VoidPanel Mail Rate Limit Policy Daemon ───────────────────────────────
    status_msg "Configuring Mail Rate Limit Policy Daemon"
    
    cat > /usr/local/bin/voidpanel-mail-policy <<'DAEMONEOF'
#!/usr/bin/env python3
import os, time, sqlite3, socket, threading

POLICY_SOCKET = '/var/spool/postfix/private/voidpanel-mail-policy'
DB_PATH       = '/var/lib/voidpanel-mail-policy/rate.db'
CONFIG_PATH   = '/etc/voidpanel-mail-policy.conf'
WHITELIST_PATH = '/etc/voidpanel-mail-policy-whitelist.conf'
DEFAULT_LIMIT = 100

def get_global_limit():
    try:
        with open(CONFIG_PATH) as f:
            for line in f:
                if line.startswith('hourly_limit='):
                    return int(line.strip().split('=', 1)[1])
    except Exception:
        pass
    return DEFAULT_LIMIT

def get_whitelisted_domains():
    try:
        if os.path.exists(WHITELIST_PATH):
            with open(WHITELIST_PATH) as f:
                content = f.read()
            return {d.strip().lower() for d in content.replace('\n', ',').split(',') if d.strip()}
    except Exception:
        pass
    return set()

def get_user_limit(sasl_username):
    try:
        conn = sqlite3.connect(DB_PATH, timeout=1)
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_limits'")
        if c.fetchone():
            c.execute('SELECT limit_val FROM user_limits WHERE username=?', (sasl_username.lower(),))
            row = c.fetchone()
            if row and row[0] > 0:
                conn.close()
                return row[0]
        conn.close()
    except Exception:
        pass
    return None

def check_and_record(sasl_username, limit):
    now          = int(time.time())
    window_start = now - 3600
    conn = sqlite3.connect(DB_PATH, timeout=5)
    try:
        c = conn.cursor()
        c.execute('CREATE TABLE IF NOT EXISTS sends (username TEXT NOT NULL, ts INTEGER NOT NULL)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_user_ts ON sends(username, ts)')
        c.execute('DELETE FROM sends WHERE ts < ?', (window_start,))
        c.execute('SELECT COUNT(*) FROM sends WHERE username=? AND ts>=?', (sasl_username, window_start))
        count = c.fetchone()[0]
        if count >= limit:
            conn.commit()
            return False
        c.execute('INSERT INTO sends (username, ts) VALUES (?, ?)', (sasl_username, now))
        conn.commit()
        return True
    finally:
        conn.close()

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute('CREATE TABLE IF NOT EXISTS sends (username TEXT NOT NULL, ts INTEGER NOT NULL)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_user_ts ON sends(username, ts)')
    conn.execute('CREATE TABLE IF NOT EXISTS user_limits (username TEXT PRIMARY KEY, limit_val INTEGER, timespan INTEGER)')
    conn.commit()
    conn.close()
    os.chmod(os.path.dirname(DB_PATH), 0o755)
    if os.path.exists(DB_PATH):
        os.chmod(DB_PATH, 0o666)

def handle_client(conn):
    data = {}
    buf = ''
    try:
        while True:
            chunk = conn.recv(4096).decode('utf-8', errors='ignore')
            if not chunk:
                break
            buf += chunk
            if '\n\n' in buf:
                break
        for line in buf.strip().split('\n'):
            line = line.strip()
            if '=' in line:
                k, v = line.split('=', 1)
                data[k.strip()] = v.strip()
        sasl_username = data.get('sasl_username', '').strip()
        if not sasl_username:
            conn.sendall(b'action=DUNNO\n\n')
            return
        domain = sasl_username.split('@')[-1].lower() if '@' in sasl_username else ''
        whitelisted = get_whitelisted_domains()
        if domain and domain in whitelisted:
            conn.sendall(b'action=DUNNO\n\n')
            return
        user_limit = get_user_limit(sasl_username)
        limit = user_limit if user_limit is not None else get_global_limit()
        if check_and_record(sasl_username, limit):
            conn.sendall(b'action=DUNNO\n\n')
        else:
            msg = 'action=REJECT Rate limit exceeded: maximum {} emails per hour allowed\n\n'.format(limit)
            conn.sendall(msg.encode())
    except Exception:
        try:
            conn.sendall(b'action=DUNNO\n\n')
        except Exception:
            pass
    finally:
        try:
            conn.close()
        except Exception:
            pass

def main():
    init_db()
    if os.path.exists(POLICY_SOCKET):
        os.unlink(POLICY_SOCKET)
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(POLICY_SOCKET)
    os.chmod(POLICY_SOCKET, 0o666)
    server.listen(50)
    while True:
        try:
            conn, _ = server.accept()
            t = threading.Thread(target=handle_client, args=(conn,), daemon=True)
            t.start()
        except Exception:
            pass

if __name__ == '__main__':
    main()
DAEMONEOF

    chmod +x /usr/local/bin/voidpanel-mail-policy

    # Write systemd service file
    cat > /etc/systemd/system/voidpanel-mail-policy.service <<'SVCEOF'
[Unit]
Description=VoidPanel Mail Rate Limit Policy Daemon
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /usr/local/bin/voidpanel-mail-policy
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
SVCEOF

    systemctl daemon-reload
    systemctl enable --now voidpanel-mail-policy

    status_msg "Configuring Mail Services Enablement"
    systemctl enable --now opendkim voidpanel-mail-policy postfix dovecot
    systemctl restart opendkim voidpanel-mail-policy postfix dovecot
    success_msg "Mail Stack Online — ports 25, 465, 587 (SMTP) | 143, 993 (IMAP) | 110, 995 (POP3)"
}

# --- 9.5 Docker Engine Setup ---
dockersetup() {
    status_msg "Installing Docker CE Engine"
    dnf install -y dnf-plugins-core
    dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo 2>/dev/null || true
    dnf install -y docker-ce docker-ce-cli containerd.io
    systemctl enable --now docker
    success_msg "Docker CE Engine Online"
}

# --- 10. Service Orchestration ---
final_restart() {
    status_msg "Synchronizing System Services"
    systemctl restart nginx uwsgi php-fpm mariadb named vsftpd postfix dovecot docker voidpanel-wa 2>/dev/null || true
    systemctl enable nginx uwsgi php-fpm mariadb named vsftpd postfix dovecot docker voidpanel-wa 2>/dev/null || true
    success_msg "All Services Synchronized"
}

# --- 11. Security (CSF Firewall) ---
firewallsetup() {
    status_msg "Installing ConfigServer Security & Firewall (CSF)"
    dnf install -y perl perl-libwww-perl perl-LWP-Protocol-https unzip iptables-services

    # Disable firewalld in favour of CSF/iptables
    systemctl stop firewalld 2>/dev/null || true
    systemctl disable firewalld 2>/dev/null || true
    systemctl mask firewalld 2>/dev/null || true

    cd /usr/src
    wget -q https://download.configserver.com/csf.tgz
    tar -xzf csf.tgz
    cd csf
    sh install.sh

    # Configure CSF Ports
    TCP_IN="20,21,22,25,53,80,110,143,443,465,587,953,993,995,3306,8080,8081,8082,8090,8092,9000,9002,33060"
    UDP_IN="53,953"

    sed -i "s/^TCP_IN = .*/TCP_IN = \"$TCP_IN\"/" /etc/csf/csf.conf
    sed -i "s/^UDP_IN = .*/UDP_IN = \"$UDP_IN\"/" /etc/csf/csf.conf
    sed -i "s/^TESTING = .*/TESTING = \"0\"/" /etc/csf/csf.conf

    csf -r
    success_msg "Firewall Profile Active"
}

# --- 12. PHP-FPM config tweaks ---
configure_php_fpm() {
    status_msg "Configuring PHP-FPM for Nginx"
    # Ensure PHP-FPM listens on unix socket and runs as nginx user
    PHP_FPM_CONF="/etc/php-fpm.d/www.conf"
    if [[ -f "$PHP_FPM_CONF" ]]; then
        sed -i 's/^user = .*/user = nginx/' "$PHP_FPM_CONF"
        sed -i 's/^group = .*/group = nginx/' "$PHP_FPM_CONF"
        sed -i 's|^listen = .*|listen = /run/php-fpm/www.sock|' "$PHP_FPM_CONF"
        sed -i 's/^listen.owner = .*/listen.owner = nginx/' "$PHP_FPM_CONF"
        sed -i 's/^listen.group = .*/listen.group = nginx/' "$PHP_FPM_CONF"
        sed -i 's/^;listen.owner = .*/listen.owner = nginx/' "$PHP_FPM_CONF"
        sed -i 's/^;listen.group = .*/listen.group = nginx/' "$PHP_FPM_CONF"
    fi
    systemctl enable --now php-fpm
    systemctl restart php-fpm
    success_msg "PHP-FPM Configured"
}

# --- 13. Finalization & Credentials ---
save_credentials() {
    cat << EOF > /root/voidpanel_access.txt
==========================================================
    VoidPanel Installation Access Credentials
==========================================================
Admin URL:     https://$PUBLIC_IP:8082
Username:      admin
Password:      $DJANGO_SUPERUSER_PASS
----------------------------------------------------------
MySQL Root:    $MYSQL_ROOT_PASS
----------------------------------------------------------
Location:      /root/voidpanel_access.txt
==========================================================
EOF
    chmod 600 /root/voidpanel_access.txt
    cat /root/voidpanel_access.txt
}

install_main_system() {
    status_msg "VoidPanel Enterprise Pipeline Starting (AlmaLinux/RHEL)"

    configure_php_fpm
    panelsetup
    bindsetup
    quotasetup
    emailsetup
    roundcubesetup
    ftpsetup
    phpmyadminsetup
    dockersetup
    firewallsetup

    # Final adjustments
    final_restart
    save_credentials

    echo -e "${GREEN}==========================================================${RESET}"
    echo -e "${GREEN}    VoidPanel Enterprise Installation Successful!         ${RESET}"
    echo -e "${GREEN}    (AlmaLinux / Rocky Linux / RHEL)                      ${RESET}"
    echo -e "${GREEN}==========================================================${RESET}"
}

# Run the installer
install_main_system
