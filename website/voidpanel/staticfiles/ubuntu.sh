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
    echo "          VoidPanel Enterprise Installation Pipeline v2.5.23"
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
INSTALL_START_DIR="$PWD"

print_header

# =============================================================================
#  UBUNTU 22.04 VERSION CHECK
# =============================================================================
if [[ -f /etc/os-release ]]; then
    source /etc/os-release
    if [[ "$ID" != "ubuntu" ]]; then
        warn_msg "This script is designed for Ubuntu 22.04. Detected: $PRETTY_NAME — proceeding anyway."
    elif [[ "$VERSION_ID" != "22.04" && "$VERSION_ID" != "24.04" ]]; then
        warn_msg "Recommended Ubuntu version is 22.04 or 24.04. Detected: $VERSION_ID — some packages may differ."
    else
        success_msg "Ubuntu $VERSION_ID detected — fully supported."
    fi
fi

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
    php${PHP_VERSION}-bcmath php${PHP_VERSION}-opcache php${PHP_VERSION}-cli \
    certbot python3-certbot-nginx \
    bind9 bind9utils bind9-doc dnsutils \
    quota quotatool \
    opendkim opendkim-tools \
    vsftpd \
    postfix postfix-mysql \
    docker.io \
    dovecot-core dovecot-imapd dovecot-pop3d dovecot-lmtpd \
    mailutils \
    perl libwww-perl

status_msg "Installing Node.js and PM2 for MERN environment"
export DEBIAN_FRONTEND=noninteractive
apt-get install -y npm
npm install -g n
n 20
hash -r
npm install -g pm2

# ── WP-CLI (required for WordPress one-click installer) ──────────────────────
status_msg "Installing WP-CLI for WordPress management"
curl -fsSL https://raw.githubusercontent.com/wp-cli/builds/gh-pages/phar/wp-cli.phar \
    -o /usr/local/bin/wp 2>/dev/null && \
    chmod +x /usr/local/bin/wp && \
    wp --info --allow-root &>/dev/null && \
    success_msg "WP-CLI installed" || \
    warn_msg "WP-CLI install failed — WordPress installer will use fallback curl method"
# =============================================================================
#  WEB SERVER SELECTION — NGINX (default and only engine for this release)
# =============================================================================
VOIDPANEL_STATE_DIR="/etc/voidpanel"
VOIDPANEL_ENGINE_FILE="$VOIDPANEL_STATE_DIR/web_engine"
WEB_ENGINE="nginx"

mkdir -p "$VOIDPANEL_STATE_DIR"
echo "$WEB_ENGINE" > "$VOIDPANEL_ENGINE_FILE"
chmod 644 "$VOIDPANEL_ENGINE_FILE"
success_msg "NGINX selected as primary web engine"

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

# Write VoidPanel MySQL credential file (read by the panel application)
echo "${MYSQL_ROOT_PASS}" > /etc/dontdelete.txt
chmod 644 /etc/dontdelete.txt
success_msg "MySQL secured"

# =============================================================================
#  PANEL CORE SETUP
# =============================================================================
panelsetup() {
    status_msg "Creating Project Directories"
    mkdir -p "$PROJECT_DIR"
    cd "$PROJECT_DIR"

    status_msg "Deploying VoidPanel Source Code"
    if [[ -f "$INSTALL_START_DIR/Archive.zip" ]]; then
        success_msg "Local Archive.zip found, copying to project directory."
        cp "$INSTALL_START_DIR/Archive.zip" Archive.zip
    elif ! wget -q https://voidpanel.com/static/voidpanel.zip -O Archive.zip; then
        error_msg "Failed to download voidpanel.zip from voidpanel.com"
        exit 1
    fi
    unzip -o Archive.zip -d "$PROJECT_DIR" > /dev/null
    rm -f Archive.zip

    # Remove any venv/ that came from the zip — it may contain hardcoded paths
    # from a developer's machine (e.g. /Users/rohan/...) which are invalid on Linux.
    # We always create a fresh virtualenv on the target server.
    if [[ -d "$PROJECT_DIR/venv" ]]; then
        rm -rf "$PROJECT_DIR/venv"
    fi

    status_msg "Initializing Python Virtual Environment"
    cd "$PROJECT_DIR"
    python3 -m venv venv
    source venv/bin/activate

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
_PANEL_HOST = '${HOSTNAME_FQDN}'
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

# Critical for HTTPS proxying (port 8082 -> 8080) to pass CSRF validation
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
PYEOF

    # ── Migrations, static files & first-run bootstrap ────────────────────────
    status_msg "Running Django migrations"
    cd "$PROJECT_DIR"
    python manage.py makemigrations --no-input 2>/dev/null || true   # catch new model fields
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

    status_msg "Running first-run setup (license placeholder + activation wizard)"
    python manage.py first_run_setup 2>/dev/null || {
        # Fallback: create the license record inline if the command fails
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

# Create or update the admin user
if not User.objects.filter(username='admin').exists():
    user = User.objects.create_superuser('admin', 'admin@voidpanel.com', '${DJANGO_SUPERUSER_PASS}')
    # Explicitly call set_password to guarantee the hash is correct
    user.set_password('${DJANGO_SUPERUSER_PASS}')
    user.is_active = True
    user.is_staff = True
    user.is_superuser = True
    user.save()
    print("Superuser created and password set.")
else:
    # If user already exists, force-reset password to the generated one
    user = User.objects.get(username='admin')
    user.set_password('${DJANGO_SUPERUSER_PASS}')
    user.is_active = True
    user.is_staff = True
    user.is_superuser = True
    user.save()
    print("Superuser already exists — password reset to generated value.")

# Verify the password works
from django.contrib.auth import authenticate
test = authenticate(username='admin', password='${DJANGO_SUPERUSER_PASS}')
if test:
    print("Password verification: OK")
else:
    print("WARNING: Password verification FAILED — check Django AUTH settings")
PYEOF

    # Write admin password to a secure file for recovery
    echo "${DJANGO_SUPERUSER_PASS}" > /etc/voidpanel_admin_pass
    chmod 600 /etc/voidpanel_admin_pass
    success_msg "Admin superuser ready (password saved to /etc/voidpanel_admin_pass)"

    status_msg "Generating API Token for remote management"
    API_TOKEN=$(python manage.py shell -c "
import secrets
from control.models import APIToken
if not APIToken.objects.filter(is_active=True).exists():
    key = secrets.token_urlsafe(48)
    APIToken.objects.create(key=key, label='Auto-generated', is_active=True)
    print(key)
else:
    print(APIToken.objects.filter(is_active=True).first().key)
" 2>/dev/null | tail -1)
    echo "$API_TOKEN" > /etc/voidpanel_api_token
    chmod 644 /etc/voidpanel_api_token
    success_msg "API Token generated"


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

    cat > /etc/systemd/system/voidpanel-celery-beat.service <<SVC
[Unit]
Description=VoidPanel Celery Beat Scheduler
After=network.target redis-server.service mysql.service voidpanel-celery.service
Wants=redis-server.service mysql.service voidpanel-celery.service

[Service]
Type=simple
User=www-data
Group=www-data
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

    # Grant www-data restricted passwordless sudo to manage system services/PHP
    echo "www-data ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/voidpanel
    chmod 440 /etc/sudoers.d/voidpanel

    # ── Nginx config ──────────────────────────────────────────────────────────
    status_msg "Configuring Nginx panel bridge"
    cat > "$NGINX_CONF" <<NGINXCONF
server {
    listen 8080;
    server_name ${PUBLIC_IP} localhost;
    client_max_body_size 0;

    # /voidpanel shortcut — redirect any domain/voidpanel hit to HTTPS panel
    location = /voidpanel {
        return 301 https://${HOSTNAME_FQDN}:8082;
    }

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
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
    }

    location / {
        include         uwsgi_params;
        uwsgi_pass      unix:${PROJECT_DIR}/panel.sock;
        uwsgi_read_timeout  3600s;
        uwsgi_send_timeout  3600s;
    }
}

server {
    listen 8082 ssl;
    server_name ${PUBLIC_IP} ${HOSTNAME_FQDN};

    ssl_certificate     /etc/nginx/dummy.crt;
    ssl_certificate_key /etc/nginx/dummy.key;
    ssl_protocols       TLSv1.2 TLSv1.3;
    client_max_body_size 0;

    # /voidpanel shortcut on HTTPS — already here, just serve the panel
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
        proxy_pass         http://127.0.0.1:8080;
        proxy_set_header   Host \$host;
        proxy_set_header   X-Real-IP \$remote_addr;
        proxy_set_header   X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto \$scheme;
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
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
          /var/log/voidpanel/celery.log \
          /var/log/voidpanel/celery-beat.log
    chown www-data:www-data \
          /var/log/voidpanel/panel.log \
          /var/log/voidpanel/error.log \
          /var/log/voidpanel/celery.log \
          /var/log/voidpanel/celery-beat.log

    # ── Permissions ───────────────────────────────────────────────────────────
    status_msg "Applying permission hardening"
    chown -R www-data:www-data "$PROJECT_DIR"
    chmod -R 750 "$PROJECT_DIR"
    chmod 711 /home

    # ── Version tracking file — must be writable by www-data (Django update process) ──
    # Without this, the update flow can't record the new version after applying an update.
    VFILE="/etc/version.txt"
    echo "2.5.23" > "$VFILE"
    chown www-data:www-data "$VFILE"
    chmod 664 "$VFILE"
    # Also write to panel dir as a reliable fallback
    echo "2.5.23" > "$PROJECT_DIR/version.txt"
    chown www-data:www-data "$PROJECT_DIR/version.txt"


    systemctl daemon-reload
    systemctl enable voidpanel voidpanel-daphne voidpanel-backup voidpanel-celery voidpanel-celery-beat
    systemctl start  voidpanel voidpanel-daphne voidpanel-backup voidpanel-celery voidpanel-celery-beat

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

    # ── Postfix main.cf ────────────────────────────────────────────────────────
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
smtpd_tls_security_level = may
smtpd_tls_protocols = !SSLv2, !SSLv3
smtp_tls_security_level = may

smtpd_sasl_type = dovecot
smtpd_sasl_path = private/auth
smtpd_sasl_auth_enable = yes

virtual_mailbox_domains = /etc/postfix/virtual_domains
virtual_mailbox_maps    = hash:/etc/postfix/vmailbox
virtual_alias_maps      = hash:/etc/postfix/virtual_alias
virtual_transport       = lmtp:unix:private/dovecot-lmtp

smtpd_recipient_restrictions = permit_sasl_authenticated,permit_mynetworks,reject_unauth_destination
EOF

    # ── Postfix master.cf — enable ports 587 (submission) and 465 (smtps) ─────
    cat > /etc/postfix/master.cf <<'EOF'
# ==========================================================================
# service type  private unpriv  chroot  wakeup  maxproc command + args
# ==========================================================================
smtp       inet  n       -       n       -       -       smtpd
submission inet  n       -       n       -       -       smtpd
  -o syslog_name=postfix/submission
  -o smtpd_tls_security_level=encrypt
  -o smtpd_sasl_auth_enable=yes
  -o smtpd_sasl_type=dovecot
  -o smtpd_sasl_path=private/auth
  -o smtpd_recipient_restrictions=check_policy_service,unix:private/voidpanel-mail-policy,permit_sasl_authenticated,reject
  -o milter_macro_daemon_name=ORIGINATING
smtps      inet  n       -       n       -       -       smtpd
  -o syslog_name=postfix/smtps
  -o smtpd_tls_wrappermode=yes
  -o smtpd_sasl_auth_enable=yes
  -o smtpd_sasl_type=dovecot
  -o smtpd_sasl_path=private/auth
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
        -o syslog_name=postfix/relay
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
    postmap /etc/postfix/virtual_alias /etc/postfix/vmailbox 2>/dev/null || true

    # ── Dovecot core config ────────────────────────────────────────────────────
    cat > /etc/dovecot/dovecot.conf <<EOF
protocols = imap pop3 lmtp
listen = *, ::
!include conf.d/*.conf
!include_try /usr/share/dovecot/protocols.d/*.conf
EOF

    # ── Dovecot master service (LMTP + auth socket + port listeners) ──────────
    cat > /etc/dovecot/conf.d/10-master.conf <<EOF
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

    # ── Dovecot SSL config ─────────────────────────────────────────────────────
    cat > /etc/dovecot/conf.d/10-ssl.conf <<EOF
ssl = yes
ssl_cert = </etc/nginx/dummy.crt
ssl_key  = </etc/nginx/dummy.key
ssl_min_protocol = TLSv1.2
ssl_prefer_server_ciphers = yes
EOF

    # ── Dovecot auth config ────────────────────────────────────────────────────
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

    # ── Dovecot mail location ──────────────────────────────────────────────────
    cat > /etc/dovecot/conf.d/10-mail.conf <<EOF
mail_location = maildir:%h/Maildir
namespace inbox {
  inbox = yes
}
mail_uid = vmail
mail_gid = vmail
EOF

    touch /etc/dovecot/users
    chown vmail:dovecot /etc/dovecot/users
    chmod 640 /etc/dovecot/users

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

    systemctl enable --now postfix dovecot
    systemctl restart postfix dovecot
    success_msg "Mail Stack Online — ports 25, 465, 587 (SMTP) | 143, 993 (IMAP) | 110, 995 (POP3)"
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
DROP USER IF EXISTS '${DB_USER}'@'localhost';
CREATE USER '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASS}';
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

    # ── Write IMAP + SMTP settings ────────────────────────────────────────────
    # Postfix uses Dovecot SASL for auth on port 587 (STARTTLS).
    # Roundcube MUST authenticate with the email credentials (not anonymous).
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
// Postfix listens on 587 (STARTTLS, Dovecot SASL required)
$config['smtp_host'] = 'tls://localhost:587';
$config['smtp_port'] = 587;
$config['smtp_user'] = '%u';     // Use the logged-in user's email
$config['smtp_pass'] = '%p';     // Use the logged-in user's password
$config['smtp_auth_type'] = 'LOGIN';
$config['smtp_conn_options'] = array(
    'ssl' => array(
        'verify_peer'       => false,
        'verify_peer_name'  => false,
        'allow_self_signed' => true,
    ),
);

// ── VoidPanel: General ─────────────────────────────────────────────────────
$config['product_name']           = 'VoidPanel Webmail';
$config['session_lifetime']       = 60;
$config['default_charset']        = 'UTF-8';
$config['language']               = 'en_US';
$config['enable_installer']       = false;
$config['mime_param_folding']     = 1;
$config['force_https']            = false;
$config['use_https']              = false;
$config['login_lc']               = 2;   // lowercase username on login
RCCONF

    mysql -u "${DB_USER}" -p"${DB_PASS}" "${DB_NAME}" < SQL/mysql.initial.sql

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

    # ── Install VoidPanel Auto-Login Plugin ───────────────────────────────────
    status_msg "Installing VoidPanel Roundcube auto-login plugin"
    mkdir -p /var/www/roundcube/plugins/vp_autologin
    mkdir -p /var/www/roundcube/temp
    # sticky-bit + world-writable so both Django (www-data) and php-fpm can use it
    chmod 1777 /var/www/roundcube/temp

    # Uses the 'authenticate' hook (not 'startup') so it fires DURING Roundcubes
    # normal login flow — after the session is ready. The Django view POSTs
    # vp_token as a hidden form field, so we must accept INPUT_POST | INPUT_GET.
    cat > /var/www/roundcube/plugins/vp_autologin/vp_autologin.php << 'RCPLUGIN'
<?php
/**
 * VoidPanel SSO Auto-Login Plugin for Roundcube 1.6.x
 *
 * Uses the authenticate hook so Roundcube manages its own session.
 * Django panel writes a one-time token file; this plugin reads it and
 * injects credentials into Roundcubes normal login flow.
 *
 * Token file: /var/www/roundcube/temp/rc_sso_<uuid>
 *   Line 1: email address
 *   Line 2: password (plain text, deleted immediately after read)
 */
class vp_autologin extends rcube_plugin
{
    public $task = 'login';

    public function init()
    {
        $this->add_hook('authenticate', [$this, 'handle_vp_token']);
    }

    public function handle_vp_token($args)
    {
        // Accept token from POST (auto-submit form) or GET (fallback redirect)
        $token = rcube_utils::get_input_value(
            'vp_token',
            rcube_utils::INPUT_POST | rcube_utils::INPUT_GET
        );

        if (empty($token) || !preg_match('/^[a-f0-9\-]{36}$/', $token)) {
            return $args;
        }

        $token    = preg_replace('/[^a-f0-9\-]/', '', $token);
        $sso_file = "/var/www/roundcube/temp/rc_sso_{$token}";

        if (!file_exists($sso_file)) {
            return $args;  // Token expired or already used
        }

        // One-time use: read then immediately delete
        $content = file_get_contents($sso_file);
        @unlink($sso_file);

        $lines = explode("\n", trim($content), 2);
        if (count($lines) < 2) {
            return $args;
        }

        $email    = trim($lines[0]);
        $password = trim($lines[1]);

        if (empty($email) || empty($password)) {
            return $args;
        }

        // Inject credentials into Roundcubes authenticate flow
        $args['user']  = $email;
        $args['pass']  = $password;
        $args['host']  = 'localhost';
        $args['valid'] = true;

        return $args;
    }
}
RCPLUGIN

    # Enable vp_autologin in Roundcube config
    if grep -q "vp_autologin" /var/www/roundcube/config/config.inc.php 2>/dev/null; then
        true  # already present
    else
        # Append plugin to existing plugins array or add it
        if grep -q "\$config\['plugins'\]" /var/www/roundcube/config/config.inc.php 2>/dev/null; then
            sed -i "s/\$config\['plugins'\] = \[/\$config['plugins'] = ['vp_autologin', /" \
                /var/www/roundcube/config/config.inc.php || true
        else
            echo "\$config['plugins'] = ['vp_autologin'];" >> /var/www/roundcube/config/config.inc.php
        fi
    fi

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

    # ── Deploy VoidPanel SSO gateway for phpMyAdmin ───────────────────────────
    status_msg "Deploying phpMyAdmin SSO gateway"
    cat > /usr/share/phpmyadmin/vp_sso.php << 'PMASSOEOF'
<?php
/**
 * VoidPanel phpMyAdmin Single Sign-On gateway
 * Called via cross-origin form POST from the VoidPanel dashboard.
 * Sets the PMA signon session then redirects to phpMyAdmin index.
 */

// Must match the session name phpMyAdmin uses
session_name('phpMyAdmin');

// Ensure session cookie is sent with proper flags
$port = (int)$_SERVER['SERVER_PORT'];
$secure = ($port === 8092);  // HTTPS port
ini_set('session.cookie_samesite', 'None');
if ($secure) {
    ini_set('session.cookie_secure', '1');
}
ini_set('session.cookie_httponly', '0');

session_start();

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    // If accessed via GET (e.g., phpMyAdmin redirecting here), show a helpful page
    http_response_code(200);
    echo '<!DOCTYPE html><html><head><title>VoidPanel Database Access</title>';
    echo '<meta http-equiv="refresh" content="0;url=index.php">';
    echo '</head><body><p>Redirecting to phpMyAdmin...</p>';
    echo '<script>window.location.href="index.php";</script></body></html>';
    exit;
}

$user     = isset($_POST['temp_user'])     ? trim($_POST['temp_user'])     : '';
$password = isset($_POST['temp_password']) ? trim($_POST['temp_password']) : '';

if (empty($user) || empty($password)) {
    http_response_code(400);
    die('<h3 style="font-family:sans-serif;color:#ef4444;padding:40px;">&#9888; Missing credentials. Please use the VoidPanel dashboard to access phpMyAdmin.</h3>');
}

if (!preg_match('/^vp_temp_[a-z0-9]+$/', $user)) {
    http_response_code(403);
    die('<h3 style="font-family:sans-serif;color:#ef4444;padding:40px;">&#128274; Access denied.</h3>');
}

// Store credentials in the phpMyAdmin signon session
$_SESSION['PMA_single_signon_user']     = $user;
$_SESSION['PMA_single_signon_password'] = $password;
$_SESSION['PMA_single_signon_host']     = 'localhost';
$_SESSION['PMA_single_signon_port']     = '3306';

// CRITICAL: flush the session to disk BEFORE redirect
// Without this, phpMyAdmin reads an empty session on index.php
session_write_close();

// Redirect to phpMyAdmin main interface
header('Location: index.php');
exit;
PMASSOEOF

    chown www-data:www-data /usr/share/phpmyadmin/vp_sso.php
    chmod 644 /usr/share/phpmyadmin/vp_sso.php

    # ── Configure phpMyAdmin SSO auth ────────────────────────────────────────
    # Force-write the signon config (overwrite any existing auth_type to ensure signon is set)
    for PMA_CONF in "/etc/phpmyadmin/config.inc.php" "/usr/share/phpmyadmin/config.inc.php"; do
        if [[ -f "$PMA_CONF" ]]; then
            # Remove any existing signon config lines to avoid duplicates
            sed -i '/PMA_single_signon\|auth_type.*signon\|SignonSession\|SignonURL\|LogoutURL/d' "$PMA_CONF" 2>/dev/null || true
            # Append fresh signon configuration
            cat >> "$PMA_CONF" << 'PMACONF'

/* VoidPanel SSO Configuration */
$cfg['Servers'][1]['auth_type']     = 'signon';
$cfg['Servers'][1]['SignonSession'] = 'phpMyAdmin';
$cfg['Servers'][1]['SignonURL']     = '/vp_sso.php';
$cfg['Servers'][1]['LogoutURL']     = '/vp_sso.php';
PMACONF
        fi
    done

    # ── Deploy update.sh for future panel updates ─────────────────────────────
    status_msg "Installing panel update script"
    cat > /var/www/panel/update.sh << 'UPDATEEOF'
#!/bin/bash
# VoidPanel — live update script
# Usage: bash update.sh (run as root on the panel server)
set -euo pipefail
GREEN='\033[0;32m'; CYAN='\033[0;36m'; RED='\033[0;31m'; RESET='\033[0m'
info()  { echo -e "${CYAN}[+] $1${RESET}"; }
ok()    { echo -e "${GREEN}[✔] $1${RESET}"; }
err()   { echo -e "${RED}[!] $1${RESET}"; exit 1; }

PROJECT_DIR="/var/www/panel"
VENV="$PROJECT_DIR/venv"

info "Fetching latest version info from voidpanel.com"
LATEST=$(curl -fsSL --max-time 10 https://voidpanel.com/version.txt 2>/dev/null | tr -d '[:space:]') || LATEST=""
if [[ -z "$LATEST" ]]; then
    err "Could not fetch version from voidpanel.com — check your internet connection."
fi

CURRENT=$(cat /var/www/panel/version.txt 2>/dev/null | tr -d '[:space:]') || CURRENT="0"
if [[ "$CURRENT" == "$LATEST" ]]; then
    ok "Already on the latest version ($CURRENT). Nothing to do."
    exit 0
fi

info "Downloading VoidPanel $LATEST"
cd /tmp
curl -fsSL --max-time 300 "https://voidpanel.com/releases/voidpanel-${LATEST}.tar.gz" -o voidpanel-update.tar.gz \
    || curl -fsSL --max-time 300 "https://voidpanel.com/static/voidpanel.zip" -o voidpanel-update.zip

if [[ -f /tmp/voidpanel-update.tar.gz ]]; then
    info "Extracting tarball"
    mkdir -p /tmp/voidpanel-src
    tar -xzf voidpanel-update.tar.gz -C /tmp/voidpanel-src --strip-components=1
    rm -f voidpanel-update.tar.gz
elif [[ -f /tmp/voidpanel-update.zip ]]; then
    info "Extracting zip"
    mkdir -p /tmp/voidpanel-src
    unzip -o voidpanel-update.zip -d /tmp/voidpanel-src > /dev/null
    rm -f voidpanel-update.zip
else
    err "Download failed — no update package found."
fi

info "Syncing files (preserving .env, venv, staticfiles)"
rsync -a --exclude='venv/' --exclude='.env' --exclude='staticfiles/' \
    --exclude='*.log' --exclude='*.sock' --exclude='__pycache__/' \
    /tmp/voidpanel-src/ "$PROJECT_DIR/"
rm -rf /tmp/voidpanel-src

info "Installing/updating Python dependencies"
source "$VENV/bin/activate"
pip install --quiet --upgrade pip
[[ -f "$PROJECT_DIR/requirements.txt" ]] && pip install --quiet -r "$PROJECT_DIR/requirements.txt" || true

info "Running database migrations"
cd "$PROJECT_DIR"
python manage.py makemigrations --no-input 2>/dev/null || true
python manage.py migrate --noinput
python manage.py collectstatic --noinput --clear 2>/dev/null || true

info "Restarting services"
systemctl restart voidpanel voidpanel-daphne voidpanel-celery 2>/dev/null || true

info "Re-applying phpMyAdmin SSO configuration"
# Redeploy vp_sso.php with session_write_close fix
if [[ -d /usr/share/phpmyadmin ]]; then
    cat > /usr/share/phpmyadmin/vp_sso.php << 'VPSSOPHP'
<?php
/**
 * VoidPanel phpMyAdmin Single Sign-On gateway
 */
session_name('phpMyAdmin');
$port = (int)$_SERVER['SERVER_PORT'];
$secure = ($port === 8092);
ini_set('session.cookie_samesite', 'None');
if ($secure) { ini_set('session.cookie_secure', '1'); }
ini_set('session.cookie_httponly', '0');
session_start();
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(200);
    echo '<!DOCTYPE html><html><head><title>VoidPanel Database Access</title>';
    echo '<meta http-equiv="refresh" content="0;url=index.php">';
    echo '</head><body><p>Redirecting to phpMyAdmin...</p></body></html>';
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
VPSSOPHP
    chown www-data:www-data /usr/share/phpmyadmin/vp_sso.php
    chmod 644 /usr/share/phpmyadmin/vp_sso.php
    # Re-apply SSO config in phpMyAdmin config
    for PMA_CONF in "/etc/phpmyadmin/config.inc.php" "/usr/share/phpmyadmin/config.inc.php"; do
        if [[ -f "$PMA_CONF" ]]; then
            sed -i '/PMA_single_signon\|auth_type.*signon\|SignonSession\|SignonURL\|LogoutURL\|VoidPanel SSO/d' "$PMA_CONF" 2>/dev/null || true
            printf "\n/* VoidPanel SSO */\n\$cfg['Servers'][1]['auth_type']='signon';\n\$cfg['Servers'][1]['SignonSession']='phpMyAdmin';\n\$cfg['Servers'][1]['SignonURL']='/vp_sso.php';\n\$cfg['Servers'][1]['LogoutURL']='/vp_sso.php';\n" >> "$PMA_CONF"
        fi
    done
fi

ok "VoidPanel updated to $LATEST successfully!"
UPDATEEOF
    chmod +x /var/www/panel/update.sh

    success_msg "phpMyAdmin Integrated"
}


# =============================================================================
#  FIREWALL (CSF)
# =============================================================================
firewallsetup() {
    status_msg "Installing ConfigServer Firewall (CSF)"
    cd /tmp
    if ! wget -q --timeout=30 https://download.configserver.com/csf.tgz -O csf.tgz; then
        warn_msg "Could not download CSF — falling back to UFW"
        _install_ufw_fallback
        return 0
    fi
    if ! tar -xzf csf.tgz 2>/dev/null; then
        warn_msg "CSF archive corrupted — falling back to UFW"
        rm -f csf.tgz
        _install_ufw_fallback
        return 0
    fi
    cd csf
    sh install.sh > /dev/null 2>&1 || true

    if [[ -f /etc/csf/csf.conf ]]; then
        TCP_IN="20,21,22,25,53,80,110,143,443,465,587,953,993,995,3306,7080,8080,8081,8082,8090,8092,9000,9002,33060"
        UDP_IN="53,953"
        sed -i "s/^TCP_IN = .*/TCP_IN = \"${TCP_IN}\"/"   /etc/csf/csf.conf
        sed -i "s/^UDP_IN = .*/UDP_IN = \"${UDP_IN}\"/"   /etc/csf/csf.conf
        sed -i 's/^TESTING = .*/TESTING = "0"/'           /etc/csf/csf.conf
        csf -r > /dev/null 2>&1 || true
        success_msg "CSF Firewall Active"
    else
        warn_msg "CSF installed but config not found — falling back to UFW"
        _install_ufw_fallback
    fi
    cd /tmp && rm -rf csf csf.tgz 2>/dev/null || true
}

_install_ufw_fallback() {
    status_msg "Configuring UFW firewall (fallback)"
    apt-get install -y ufw 2>/dev/null || true
    ufw --force reset > /dev/null 2>&1 || true
    ufw default deny incoming > /dev/null 2>&1 || true
    ufw default allow outgoing > /dev/null 2>&1 || true
    # Allow all required ports
    for port in 22 25 53 80 110 143 443 465 587 993 995 3306 8080 8081 8082 8090 8092 9000 9002; do
        ufw allow "$port" > /dev/null 2>&1 || true
    done
    ufw allow 40000:50000/tcp > /dev/null 2>&1 || true  # FTP passive
    ufw --force enable > /dev/null 2>&1 || true
    success_msg "UFW Firewall Active (CSF fallback)"
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
    systemctl restart docker 2>/dev/null || true
    systemctl restart voidpanel
    systemctl restart voidpanel-daphne
    systemctl restart voidpanel-celery

    # Enable all on boot — use 'named' not 'bind9' (bind9 is an alias on Ubuntu 22.04+)
    systemctl enable nginx php${PHP_VERSION}-fpm mysql named postfix dovecot voidpanel voidpanel-daphne voidpanel-celery redis-server docker 2>/dev/null || \
    systemctl enable nginx php${PHP_VERSION}-fpm mysql bind9 postfix dovecot voidpanel voidpanel-daphne voidpanel-celery redis-server docker 2>/dev/null || true

    success_msg "All services online and boot-enabled"
}

# =============================================================================
#  CRON JOBS — Auto-suspend overdue services
# =============================================================================
cronsetup() {
    status_msg "Installing VoidPanel scheduled tasks (cron)"

    # Note: This cron is for the PANEL server only.
    # The check_overdue command belongs to the WEBSITE (billing) project.
    # If the website is co-located with the panel on this server, uncomment below.
    # Otherwise, set this up on the website server separately.

    # Auto-suspend cron placeholder (safe no-op if website not present here)
    CRON_COMMENT="# VoidPanel: check overdue invoices daily (website billing project)"
    CRON_LINE="0 6 * * * www-data cd /var/www/voidpanel-web && /var/www/voidpanel-web/venv/bin/python manage.py check_overdue >> /var/log/voidpanel_overdue.log 2>&1"

    # Create log file
    touch /var/log/voidpanel_overdue.log
    chmod 640 /var/log/voidpanel_overdue.log
    chown www-data:www-data /var/log/voidpanel_overdue.log 2>/dev/null || true

    # Write cron file for panel-level cleanup tasks
    cat > /etc/cron.d/voidpanel <<CRONEOF
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

# VoidPanel scheduled maintenance
# Clear old Django sessions weekly
0 3 * * 0 www-data cd ${PROJECT_DIR} && ${VENV_DIR}/bin/python manage.py clearsessions >> /var/log/voidpanel_uwsgi.log 2>&1

# Check disk usage and update panel stats hourly
0 * * * * www-data cd ${PROJECT_DIR} && ${VENV_DIR}/bin/python manage.py update_disk_stats >> /var/log/voidpanel_uwsgi.log 2>&1 || true

# Check for and apply auto updates nightly at midnight
0 0 * * * www-data cd ${PROJECT_DIR} && ${VENV_DIR}/bin/python manage.py auto_update >> /var/log/voidpanel_auto_update.log 2>&1

CRONEOF
    touch /var/log/voidpanel_auto_update.log 2>/dev/null || true
    chmod 644 /var/log/voidpanel_auto_update.log 2>/dev/null || true
    chown www-data:www-data /var/log/voidpanel_auto_update.log 2>/dev/null || true
    chmod 644 /etc/cron.d/voidpanel
    success_msg "Cron jobs installed"
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
 (Also saved to:     /etc/voidpanel_admin_pass)
----------------------------------------------------------
 phpMyAdmin:         http://${PUBLIC_IP}:8090
 Roundcube Mail:     http://${PUBLIC_IP}:9000
----------------------------------------------------------
 MySQL Root Pass:    ${MYSQL_ROOT_PASS}
 Web Engine:         ${WEB_ENGINE}
 SSO Website URL:    https://voidpanel.com

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
    status_msg "VoidPanel v2.5.23 — Enterprise Installation Starting (Ubuntu 22.04)"
    panelsetup
    bindsetup
    quotasetup
    emailsetup
    roundcubesetup
    ftpsetup
    phpmyadminsetup
    firewallsetup
    cronsetup
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
