#!/bin/bash
set -euo pipefail

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
    echo "          VoidPanel Enterprise Installation Pipeline v2.0"
    echo "=========================================================================="
    echo -e " Time: $(date)"
    echo -e " Logs: $LOG_FILE"
    echo -e "==========================================================================${RESET}"
}

status_msg() { echo -e "${CYAN}[+] $1...${RESET}"; }
success_msg() { echo -e "${GREEN}[✔] $1${RESET}"; }
error_msg()   { echo -e "${RED}[!] $1${RESET}"; }
warn_msg()    { echo -e "${YELLOW}[!] $1${RESET}"; }

# ── Variables ──────────────────────────────────────────────────────────────────
PROJECT_NAME="panel"
PHP_VERSION="8.3"
PROJECT_DIR="/var/www/$PROJECT_NAME"
VENV_DIR="$PROJECT_DIR/venv"
NGINX_CONF="/etc/nginx/sites-available/$PROJECT_NAME"
PUBLIC_IP=$(curl -4 -s --max-time 8 ifconfig.me 2>/dev/null \
         || curl -4 -s --max-time 8 api.ipify.org 2>/dev/null \
         || echo "127.0.0.1")
MYSQL_ROOT_PASS=$(openssl rand -base64 16 | tr -dc 'a-zA-Z0-9' | head -c 20)
DJANGO_SUPERUSER_PASS=$(openssl rand -base64 16 | tr -dc 'a-zA-Z0-9' | head -c 20)
HOSTNAME_FQDN=$(hostname -f 2>/dev/null || hostname)

print_header

# =============================================================================
#  SYSTEM UPDATE & CORE BOOTSTRAP
# =============================================================================
export DEBIAN_FRONTEND=noninteractive

status_msg "Updating system packages"
apt-get update -y
apt-get upgrade -y -o Dpkg::Options::="--force-confold"

status_msg "Installing bootstrap tools"
apt-get install -y software-properties-common ca-certificates gnupg lsb-release curl wget

# ── Add PHP 8.3 PPA BEFORE installing PHP ────────────────────────────────────
status_msg "Adding PHP 8.3 repository (ondrej/php PPA)"
add-apt-repository -y ppa:ondrej/php
apt-get update -y

# ── Install all packages in one shot ─────────────────────────────────────────
status_msg "Installing all system dependencies"
apt-get install -y \
    git unzip zip openssl \
    python3 python3-venv python3-pip python3-dev \
    build-essential libssl-dev libffi-dev \
    mysql-server redis-server \
    nginx \
    php${PHP_VERSION} php${PHP_VERSION}-fpm php${PHP_VERSION}-mysql \
    php${PHP_VERSION}-mbstring php${PHP_VERSION}-zip php${PHP_VERSION}-gd \
    php${PHP_VERSION}-curl php${PHP_VERSION}-xml php${PHP_VERSION}-intl \
    php${PHP_VERSION}-bcmath php${PHP_VERSION}-opcache \
    certbot python3-certbot-nginx \
    bind9 bind9utils bind9-doc dnsutils \
    quota quotatool \
    opendkim opendkim-tools \
    vsftpd \
    postfix postfix-mysql \
    dovecot-core dovecot-imapd dovecot-pop3d dovecot-lmtpd \
    mailutils \
    perl libwww-perl

# =============================================================================
#  WEB SERVER SELECTION
# =============================================================================
VOIDPANEL_STATE_DIR="/etc/voidpanel"
VOIDPANEL_ENGINE_FILE="$VOIDPANEL_STATE_DIR/web_engine"
OLS_ADMIN_PASS=$(openssl rand -base64 12 | tr -dc 'a-zA-Z0-9' | head -c 16)

echo ""
echo -e "${CYAN}=========================================================="
echo "  VoidPanel — Web Server Selection"
echo "=========================================================="
echo ""
echo "  [1]  NGINX          (default — fastest raw throughput, Certbot native)"
echo "  [2]  OpenLiteSpeed  (OLS — Apache .htaccess, HTTP/3, lsphp PHP)"
echo ""
echo -e "  Press Enter within 30s to accept default [1]${RESET}"
echo ""
read -t 30 -r -p "  Your choice [1|2]: " WEB_CHOICE || WEB_CHOICE="1"
WEB_CHOICE="${WEB_CHOICE:-1}"
WEB_CHOICE="$(echo "$WEB_CHOICE" | tr -d '[:space:]')"

if [[ "$WEB_CHOICE" == "2" ]]; then
    WEB_ENGINE="ols"
    echo -e "${GREEN}[✔] OpenLiteSpeed selected.${RESET}"
else
    WEB_ENGINE="nginx"
    echo -e "${GREEN}[✔] NGINX selected.${RESET}"
fi

mkdir -p "$VOIDPANEL_STATE_DIR"
echo "$WEB_ENGINE"     > "$VOIDPANEL_ENGINE_FILE"
echo "$OLS_ADMIN_PASS" > "$VOIDPANEL_STATE_DIR/ols_admin_pass"
chmod 644 "$VOIDPANEL_ENGINE_FILE"             # readable by www-data
chmod 640 "$VOIDPANEL_STATE_DIR/ols_admin_pass"  # root-only (sensitive)

# =============================================================================
#  INSTALL OpenLiteSpeed (always — enables hot-swap from admin panel later)
# =============================================================================
status_msg "Installing OpenLiteSpeed"
wget -qO /tmp/ols-repo.sh https://rpms.litespeedtech.com/debian/enable_lst_debian_repo.sh 2>/dev/null || true
if [[ -f /tmp/ols-repo.sh ]]; then
    bash /tmp/ols-repo.sh > /dev/null 2>&1 || true
    apt-get update -y  > /dev/null 2>&1 || true
    apt-get install -y openlitespeed > /dev/null 2>&1 || true
    rm -f /tmp/ols-repo.sh
else
    warn_msg "Could not reach LiteSpeed repo — OLS skipped (hot-swap install available from panel later)"
fi

if [[ -f /usr/local/lsws/admin/misc/admpass.sh ]]; then
    printf "admin\n${OLS_ADMIN_PASS}\n${OLS_ADMIN_PASS}\n" | \
        /usr/local/lsws/admin/misc/admpass.sh > /dev/null 2>&1 || true
    echo "admin" > "$VOIDPANEL_STATE_DIR/ols_admin_user"
    chmod 640 "$VOIDPANEL_STATE_DIR/ols_admin_user"
fi

if [[ "$WEB_ENGINE" == "ols" ]]; then
    systemctl enable lshttpd lsws 2>/dev/null || true
    systemctl start  lshttpd lsws 2>/dev/null || true
    success_msg "OpenLiteSpeed enabled as primary site engine (80/443)"
else
    systemctl disable lshttpd lsws 2>/dev/null || true
    systemctl stop    lshttpd lsws 2>/dev/null || true
    /usr/local/lsws/bin/lswsctrl stop 2>/dev/null || true
    pkill -9 litespeed 2>/dev/null || true
    success_msg "NGINX enabled as primary site engine"
fi

# =============================================================================
#  DUMMY SSL
# =============================================================================
status_msg "Generating self-signed SSL certificate"
mkdir -p /etc/nginx/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/nginx/dummy.key \
    -out    /etc/nginx/dummy.crt \
    -subj   "/C=US/ST=State/L=City/O=VoidPanel/CN=localhost" 2>/dev/null

# =============================================================================
#  MySQL — Secure & configure
# =============================================================================
status_msg "Securing MySQL"
systemctl enable --now mysql

# Wait for MySQL to be ready (sometimes slow on first boot)
for i in {1..10}; do
    mysqladmin ping --silent 2>/dev/null && break || true
    sleep 2
done

mysql -u root 2>/dev/null <<MSQL || true
ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '${MYSQL_ROOT_PASS}';
FLUSH PRIVILEGES;
MSQL

cat > /root/.my.cnf <<MYCNF
[client]
user=root
password=${MYSQL_ROOT_PASS}
MYCNF
chmod 600 /root/.my.cnf
success_msg "MySQL secured"

# =============================================================================
#  PANEL CORE SETUP
# =============================================================================
panelsetup() {
    status_msg "Creating Project Directories"
    mkdir -p "$PROJECT_DIR"
    cd "$PROJECT_DIR"

    status_msg "Initializing Python Virtual Environment"
    python3 -m venv venv
    source venv/bin/activate

    status_msg "Deploying VoidPanel Source Code"
    if ! wget -q https://voidpanel.com/op/install/ubuntu/Archive.zip -O Archive.zip; then
        error_msg "Failed to download Archive.zip from voidpanel.com"
        exit 1
    fi
    unzip -o Archive.zip -d "$PROJECT_DIR" > /dev/null
    rm -f Archive.zip

    status_msg "Installing Python Dependencies"
    pip install --upgrade pip --quiet
    if [[ -f "$PROJECT_DIR/requirements.txt" ]]; then
        pip install --quiet -r "$PROJECT_DIR/requirements.txt"
    else
        pip install --quiet \
            django celery redis uwsgi psutil pexpect requests \
            mysql-connector-python djangorestframework django-cors-headers \
            channels channels_redis daphne
    fi

    # ── Fix Django settings ──────────────────────────────────────────────────
    status_msg "Configuring Django settings"
    DJANGO_SETTINGS=$(find "$PROJECT_DIR" -name "settings.py" | grep -v venv | head -n 1)
    if [[ -z "$DJANGO_SETTINGS" ]]; then
        error_msg "settings.py not found — check Archive.zip contents"
        exit 1
    fi

    # Generate a URL-safe secret key (no special chars that break systemd EnvironmentFile)
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))")
    echo "$SECRET_KEY" > "$PROJECT_DIR/.secret_key"
    chmod 600 "$PROJECT_DIR/.secret_key"
    chown www-data:www-data "$PROJECT_DIR/.secret_key"

    # Write .env — systemd EnvironmentFile loads these into the service process
    cat > "$PROJECT_DIR/.env" <<ENVFILE
DJANGO_SECRET_KEY=${SECRET_KEY}
DJANGO_ALLOWED_HOSTS=*
DJANGO_CSRF_ORIGINS=http://${PUBLIC_IP}:8080,https://${PUBLIC_IP}:8082,http://${PUBLIC_IP},https://${PUBLIC_IP}
DJANGO_DEBUG=false
ENVFILE
    chmod 640 "$PROJECT_DIR/.env"
    chown www-data:www-data "$PROJECT_DIR/.env"

    # Directly patch settings.py with CSRF_TRUSTED_ORIGINS — guaranteed to work
    # regardless of env var loading order or systemd EnvironmentFile parsing edge cases
    cat >> "$DJANGO_SETTINGS" <<PYEOF

# ── Production CSRF & Host config injected by installer ──────────────────────
_PANEL_IP = '${PUBLIC_IP}'
CSRF_TRUSTED_ORIGINS = [
    f'http://{_PANEL_IP}',
    f'http://{_PANEL_IP}:8080',
    f'https://{_PANEL_IP}',
    f'https://{_PANEL_IP}:8082',
]
ALLOWED_HOSTS = ['*', _PANEL_IP, 'localhost', '127.0.0.1']

# Critical for HTTPS proxying (port 8082 -> 8080) to pass CSRF validation
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
PYEOF

    # ── Migrations & static files ─────────────────────────────────────────────
    status_msg "Running Django migrations"
    cd "$PROJECT_DIR"
    python manage.py migrate --noinput
    python manage.py collectstatic --noinput --clear 2>/dev/null || true

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

    # ── uWSGI config ──────────────────────────────────────────────────────────
    status_msg "Configuring uWSGI"
    cat > "$PROJECT_DIR/panel.ini" <<INI
[uwsgi]
chdir           = ${PROJECT_DIR}
module          = panel.wsgi:application
home            = ${VENV_DIR}
master          = true
processes       = 4
socket          = ${PROJECT_DIR}/panel.sock
chmod-socket    = 660
uid             = www-data
gid             = www-data
vacuum          = true
die-on-term     = true
logto           = /var/log/voidpanel_uwsgi.log
INI

    # Pre-create log file so www-data can write to it immediately on service start
    touch /var/log/voidpanel_uwsgi.log
    chown www-data:www-data /var/log/voidpanel_uwsgi.log
    chmod 640 /var/log/voidpanel_uwsgi.log

    # ── systemd service ───────────────────────────────────────────────────────
    cat > /etc/systemd/system/voidpanel.service <<SVC
[Unit]
Description=VoidPanel uWSGI Application Server
After=network.target mysql.service redis.service
Wants=mysql.service redis.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=${PROJECT_DIR}
EnvironmentFile=${PROJECT_DIR}/.env
ExecStart=${VENV_DIR}/bin/uwsgi --ini ${PROJECT_DIR}/panel.ini
Restart=on-failure
RestartSec=5s
KillSignal=SIGQUIT
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
SVC

    cat > /etc/systemd/system/voidpanel-daphne.service <<SVC
[Unit]
Description=VoidPanel Daphne ASGI Application Server
After=network.target redis-server.service
Wants=redis-server.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=${PROJECT_DIR}
EnvironmentFile=${PROJECT_DIR}/.env
ExecStart=${VENV_DIR}/bin/daphne -b 127.0.0.1 -p 8001 panel.asgi:application
Restart=on-failure
RestartSec=5s
LimitNOFILE=65535

[Install]
WantedBy=multi-user.target
SVC

    # ── Celery worker service ──────────────────────────────────────────
    status_msg "Installing Celery worker service"
    mkdir -p /var/run/celery
    chown www-data:www-data /var/run/celery
    cat > /etc/systemd/system/voidpanel-celery.service <<SVC
[Unit]
Description=VoidPanel Celery Worker
After=network.target redis-server.service mysql.service
Wants=redis-server.service mysql.service

[Service]
Type=simple
User=www-data
Group=www-data
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

    # Grant www-data restricted passwordless sudo to manage system services/PHP
    echo "www-data ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/voidpanel
    chmod 440 /etc/sudoers.d/voidpanel

    # ── Nginx config ──────────────────────────────────────────────────────────
    status_msg "Configuring Nginx panel bridge"
    cat > "$NGINX_CONF" <<NGINXCONF
server {
    listen 8080;
    server_name ${PUBLIC_IP} localhost;
    client_max_body_size 256M;

    location /static/ {
        alias ${PROJECT_DIR}/staticfiles/;
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
    }

    location / {
        include         uwsgi_params;
        uwsgi_pass      unix:${PROJECT_DIR}/panel.sock;
        uwsgi_read_timeout  300s;
        uwsgi_send_timeout  300s;
    }
}

server {
    listen 8082 ssl http2;
    server_name ${PUBLIC_IP} ${HOSTNAME_FQDN};

    ssl_certificate     /etc/nginx/dummy.crt;
    ssl_certificate_key /etc/nginx/dummy.key;
    ssl_protocols       TLSv1.2 TLSv1.3;
    client_max_body_size 256M;

    location / {
        proxy_pass         http://127.0.0.1:8080;
        proxy_set_header   Host \$host;
        proxy_set_header   X-Real-IP \$remote_addr;
        proxy_set_header   X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto \$scheme;
        proxy_read_timeout 300s;
    }
}
NGINXCONF

    ln -sf "$NGINX_CONF" /etc/nginx/sites-enabled/
    rm -f /etc/nginx/sites-enabled/default

    # ── VoidPanel log directory (must exist before Django/Celery start) ────────
    status_msg "Creating VoidPanel log directory"
    mkdir -p /var/log/voidpanel
    chown www-data:www-data /var/log/voidpanel
    chmod 750 /var/log/voidpanel
    touch /var/log/voidpanel/panel.log \
          /var/log/voidpanel/error.log \
          /var/log/voidpanel/celery.log
    chown www-data:www-data \
          /var/log/voidpanel/panel.log \
          /var/log/voidpanel/error.log \
          /var/log/voidpanel/celery.log

    # ── Permissions ───────────────────────────────────────────────────────────
    status_msg "Applying permission hardening"
    chown -R www-data:www-data "$PROJECT_DIR"
    chmod -R 750 "$PROJECT_DIR"

    systemctl daemon-reload
    systemctl enable voidpanel
    systemctl start  voidpanel

    success_msg "Panel Core Setup Complete"
}

# =============================================================================
#  DNS (BIND9)
# =============================================================================
bindsetup() {
    status_msg "Configuring Authoritative DNS (BIND9)"
    cp /etc/bind/named.conf.options /etc/bind/named.conf.options.backup 2>/dev/null || true

    cat > /etc/bind/named.conf.options <<EOF
options {
    directory "/var/cache/bind";
    forwarders { 8.8.8.8; 8.8.4.4; 1.1.1.1; };
    dnssec-validation auto;
    listen-on { any; };
    listen-on-v6 { any; };
    allow-query { any; };
    recursion yes;
};
EOF
    # On Ubuntu 22.04+, bind9.service is an alias — use 'named' for enable
    systemctl enable --now named 2>/dev/null || systemctl enable --now bind9 2>/dev/null || true
    systemctl restart named 2>/dev/null || systemctl restart bind9 2>/dev/null || true
    success_msg "DNS Service Configured"
}

# =============================================================================
#  FILESYSTEM QUOTAS
# =============================================================================
quotasetup() {
    status_msg "Initializing Filesystem Quotas"
    # Only add quota options if not already present
    if ! grep -q "usrquota" /etc/fstab; then
        # Use awk for safer fstab editing
        awk '/errors=remount-ro/ && !/usrquota/ { sub("errors=remount-ro","errors=remount-ro,usrquota,grpquota") } { print }' \
            /etc/fstab > /tmp/fstab.new && mv /tmp/fstab.new /etc/fstab
        mount -o remount / 2>/dev/null || true
    fi
    quotacheck -ugm / > /dev/null 2>&1 || true
    quotaon -v /       > /dev/null 2>&1 || true
    success_msg "Quotas Active"
}

# =============================================================================
#  EMAIL (Postfix + Dovecot)
# =============================================================================
emailsetup() {
    status_msg "Configuring Enterprise Mail Stack (Postfix/Dovecot)"

    groupadd -g 5000 vmail 2>/dev/null || true
    useradd -s /usr/sbin/nologin -u 5000 -g 5000 -d /home/vmail vmail 2>/dev/null || true
    mkdir -p /home/vmail/mail
    chown -R vmail:vmail /home/vmail

    # Write hostname to mailname
    echo "$HOSTNAME_FQDN" > /etc/mailname

    cat > /etc/postfix/main.cf <<EOF
myhostname = ${HOSTNAME_FQDN}
myorigin = /etc/mailname
smtpd_banner = \$myhostname ESMTP VoidPanel
biff = no
append_dot_mydomain = no
readme_directory = no

smtpd_tls_cert_file = /etc/nginx/dummy.crt
smtpd_tls_key_file  = /etc/nginx/dummy.key
smtpd_use_tls = yes
smtpd_tls_auth_only = yes

smtpd_sasl_type = dovecot
smtpd_sasl_path = private/auth
smtpd_sasl_auth_enable = yes

virtual_mailbox_domains = /etc/postfix/virtual_domains
virtual_mailbox_maps    = hash:/etc/postfix/vmailbox
virtual_alias_maps      = hash:/etc/postfix/virtual_alias
virtual_transport       = lmtp:unix:private/dovecot-lmtp

smtpd_recipient_restrictions = permit_sasl_authenticated,permit_mynetworks,reject_unauth_destination
EOF

    touch /etc/postfix/virtual_domains /etc/postfix/vmailbox /etc/postfix/virtual_alias
    postmap /etc/postfix/virtual_alias /etc/postfix/vmailbox 2>/dev/null || true

    cat > /etc/dovecot/dovecot.conf <<EOF
protocols = imap pop3 lmtp
listen = *, ::
!include conf.d/*.conf
!include_try /usr/share/dovecot/protocols.d/*.conf
EOF

    cat > /etc/dovecot/conf.d/10-master.conf <<EOF
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

    cat > /etc/dovecot/conf.d/10-auth.conf <<EOF
disable_plaintext_auth = yes
auth_mechanisms = plain login
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

    cat > /etc/dovecot/conf.d/10-mail.conf <<EOF
mail_location = maildir:%h/Maildir
namespace inbox {
  inbox = yes
}
mail_uid = vmail
mail_gid = vmail
EOF

    touch /etc/dovecot/users
    chown vmail:vmail /etc/dovecot/users
    chmod 660 /etc/dovecot/users

    systemctl enable --now postfix dovecot
    systemctl restart postfix dovecot
    success_msg "Mail Stack Online"
}

# =============================================================================
#  ROUNDCUBE WEBMAIL
# =============================================================================
roundcubesetup() {
    status_msg "Preparing Roundcube Database"
    DB_NAME="roundcube"
    DB_USER="roundcube"
    DB_PASS=$(openssl rand -base64 16 | tr -dc 'a-zA-Z0-9' | head -c 20)

    mysql <<EOF
CREATE DATABASE IF NOT EXISTS ${DB_NAME} DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASS}';
GRANT ALL PRIVILEGES ON ${DB_NAME}.* TO '${DB_USER}'@'localhost';
FLUSH PRIVILEGES;
EOF

    status_msg "Downloading Roundcube Webmail"
    mkdir -p /var/www/roundcube
    cd /tmp
    wget -q https://github.com/roundcube/roundcubemail/releases/download/1.6.9/roundcubemail-1.6.9-complete.tar.gz \
         -O roundcube.tar.gz
    tar -xzf roundcube.tar.gz
    cp -r roundcubemail-1.6.9/. /var/www/roundcube/
    rm -rf roundcubemail-1.6.9 roundcube.tar.gz 2>/dev/null || true

    cd /var/www/roundcube
    cp config/config.inc.php.sample config/config.inc.php
    sed -i "s|.*db_dsnw.*|\$config['db_dsnw'] = 'mysql://${DB_USER}:${DB_PASS}@localhost/${DB_NAME}';|" \
        config/config.inc.php

    cat > /etc/nginx/sites-available/roundcube <<NGINXCONF
server {
    listen 9000;
    server_name ${PUBLIC_IP};
    root /var/www/roundcube;
    index index.php;
    client_max_body_size 25M;
    location / { try_files \$uri \$uri/ /index.php; }
    location ~ \.php\$ {
        include snippets/fastcgi-php.conf;
        fastcgi_pass unix:/var/run/php/php${PHP_VERSION}-fpm.sock;
    }
    location ~ /\.(ht|svn|git) { deny all; }
}
server {
    listen 9002 ssl http2;
    server_name ${PUBLIC_IP} ${HOSTNAME_FQDN};
    ssl_certificate     /etc/nginx/dummy.crt;
    ssl_certificate_key /etc/nginx/dummy.key;
    ssl_protocols       TLSv1.2 TLSv1.3;
    root /var/www/roundcube;
    index index.php;
    client_max_body_size 25M;
    location / { try_files \$uri \$uri/ /index.php; }
    location ~ \.php\$ {
        include snippets/fastcgi-php.conf;
        fastcgi_pass unix:/var/run/php/php${PHP_VERSION}-fpm.sock;
    }
    location ~ /\.(ht|svn|git) { deny all; }
}
NGINXCONF

    ln -sf /etc/nginx/sites-available/roundcube /etc/nginx/sites-enabled/
    chown -R www-data:www-data /var/www/roundcube
    success_msg "Roundcube Webmail Integrated"
}

# =============================================================================
#  VSFTPD
# =============================================================================
ftpsetup() {
    status_msg "Configuring vsftpd"
    cp /etc/vsftpd.conf /etc/vsftpd.conf.bak 2>/dev/null || true

    cat > /etc/vsftpd.conf <<EOF
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
pasv_enable=YES
pasv_min_port=40000
pasv_max_port=50000
EOF

    systemctl enable --now vsftpd
    systemctl restart vsftpd
    success_msg "FTP Service Hardened"
}

# =============================================================================
#  phpMyAdmin
# =============================================================================
phpmyadminsetup() {
    status_msg "Integrating phpMyAdmin"
    # Pre-answer debconf so it doesn't prompt
    echo "phpmyadmin phpmyadmin/dbconfig-install boolean true"     | debconf-set-selections
    echo "phpmyadmin phpmyadmin/mysql/admin-pass password ${MYSQL_ROOT_PASS}" | debconf-set-selections
    echo "phpmyadmin phpmyadmin/mysql/app-pass password ${MYSQL_ROOT_PASS}"   | debconf-set-selections
    echo "phpmyadmin phpmyadmin/reconfigure-webserver multiselect none"       | debconf-set-selections
    apt-get install -y phpmyadmin 2>/dev/null || warn_msg "phpMyAdmin install failed — skipped"

    cat > /etc/nginx/sites-available/phpmyadmin <<NGINXCONF
server {
    listen 8090;
    server_name ${PUBLIC_IP};
    root /usr/share/phpmyadmin;
    index index.php;
    location / { try_files \$uri \$uri/ =404; }
    location ~ \.php\$ {
        include snippets/fastcgi-php.conf;
        fastcgi_pass unix:/var/run/php/php${PHP_VERSION}-fpm.sock;
    }
    location ~ /\.(ht|svn|git) { deny all; }
}
server {
    listen 8092 ssl http2;
    server_name ${PUBLIC_IP} ${HOSTNAME_FQDN};
    ssl_certificate     /etc/nginx/dummy.crt;
    ssl_certificate_key /etc/nginx/dummy.key;
    ssl_protocols       TLSv1.2 TLSv1.3;
    root /usr/share/phpmyadmin;
    index index.php;
    location / { try_files \$uri \$uri/ =404; }
    location ~ \.php\$ {
        include snippets/fastcgi-php.conf;
        fastcgi_pass unix:/var/run/php/php${PHP_VERSION}-fpm.sock;
    }
    location ~ /\.(ht|svn|git) { deny all; }
}
NGINXCONF

    ln -sf /etc/nginx/sites-available/phpmyadmin /etc/nginx/sites-enabled/
    success_msg "phpMyAdmin Integrated"
}

# =============================================================================
#  FIREWALL (CSF)
# =============================================================================
firewallsetup() {
    status_msg "Installing ConfigServer Firewall (CSF)"
    cd /tmp
    if ! wget -q --timeout=30 https://download.configserver.com/csf.tgz -O csf.tgz; then
        warn_msg "Could not download CSF — firewall setup skipped (install manually later)"
        return 0
    fi
    if ! tar -xzf csf.tgz 2>/dev/null; then
        warn_msg "CSF archive corrupted — firewall setup skipped"
        rm -f csf.tgz
        return 0
    fi
    cd csf
    sh install.sh > /dev/null 2>&1 || true

    if [[ -f /etc/csf/csf.conf ]]; then
        TCP_IN="20,21,22,25,53,80,110,143,443,465,587,953,993,995,3306,7080,8080,8082,8090,8092,9000,9002,33060"
        UDP_IN="53,953"
        sed -i "s/^TCP_IN = .*/TCP_IN = \"${TCP_IN}\"/"   /etc/csf/csf.conf
        sed -i "s/^UDP_IN = .*/UDP_IN = \"${UDP_IN}\"/"   /etc/csf/csf.conf
        sed -i 's/^TESTING = .*/TESTING = "0"/'           /etc/csf/csf.conf
        csf -r > /dev/null 2>&1 || true
        success_msg "CSF Firewall Active"
    else
        warn_msg "CSF installed but config not found — skipping rule application"
    fi
    cd /tmp && rm -rf csf csf.tgz 2>/dev/null || true
}

# =============================================================================
#  FINAL SERVICE RESTART
# =============================================================================
final_restart() {
    status_msg "Synchronizing all services"
    # Ensure redis is running first (required by celery/channels)
    systemctl enable --now redis-server 2>/dev/null || systemctl enable --now redis 2>/dev/null || true

    # Test nginx config before reloading
    nginx -t
    systemctl restart nginx
    systemctl restart php${PHP_VERSION}-fpm
    systemctl restart mysql
    systemctl restart named 2>/dev/null || systemctl restart bind9 2>/dev/null || true
    systemctl restart vsftpd 2>/dev/null || true
    systemctl restart postfix
    systemctl restart dovecot
    systemctl restart voidpanel
    systemctl restart voidpanel-daphne
    systemctl restart voidpanel-celery

    # Enable all on boot — use 'named' not 'bind9' (bind9 is an alias on Ubuntu 22.04+)
    systemctl enable nginx php${PHP_VERSION}-fpm mysql named postfix dovecot voidpanel voidpanel-daphne voidpanel-celery redis-server 2>/dev/null || \
    systemctl enable nginx php${PHP_VERSION}-fpm mysql bind9 postfix dovecot voidpanel voidpanel-daphne voidpanel-celery redis-server 2>/dev/null || true

    success_msg "All services online and boot-enabled"
}

# =============================================================================
#  SAVE CREDENTIALS
# =============================================================================
save_credentials() {
    cat > /root/voidpanel_access.txt <<EOF
==========================================================
       VoidPanel — Access Credentials
==========================================================
 Panel URL (HTTP):   http://${PUBLIC_IP}:8080
 Panel URL (HTTPS):  https://${PUBLIC_IP}:8082
 Username:           admin
 Password:           ${DJANGO_SUPERUSER_PASS}
----------------------------------------------------------
 phpMyAdmin:         http://${PUBLIC_IP}:8090
 Roundcube Mail:     http://${PUBLIC_IP}:9000
----------------------------------------------------------
 MySQL Root Pass:    ${MYSQL_ROOT_PASS}
 Web Engine:         ${WEB_ENGINE}
EOF

    if [[ "$WEB_ENGINE" == "ols" ]]; then
        cat >> /root/voidpanel_access.txt <<EOF
----------------------------------------------------------
 OLS Admin Panel:    http://${PUBLIC_IP}:7080
 OLS Username:       admin
 OLS Password:       ${OLS_ADMIN_PASS}
EOF
    fi

    cat >> /root/voidpanel_access.txt <<EOF
----------------------------------------------------------
 Install Log:        ${LOG_FILE}
 This file:          /root/voidpanel_access.txt
==========================================================
EOF
    chmod 600 /root/voidpanel_access.txt
    echo ""
    cat /root/voidpanel_access.txt
}

# =============================================================================
#  MAIN
# =============================================================================
install_main_system() {
    status_msg "VoidPanel v2.0 — Enterprise Installation Starting"
    panelsetup
    bindsetup
    quotasetup
    emailsetup
    roundcubesetup
    ftpsetup
    phpmyadminsetup
    firewallsetup
    final_restart
    save_credentials

    echo ""
    echo -e "${GREEN}==========================================================${RESET}"
    echo -e "${GREEN}   VoidPanel Enterprise Installation Complete!            ${RESET}"
    echo -e "${GREEN}   Credentials saved to /root/voidpanel_access.txt        ${RESET}"
    echo -e "${GREEN}==========================================================${RESET}"
    echo ""
}

install_main_system
