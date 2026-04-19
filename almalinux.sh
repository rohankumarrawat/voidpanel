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
#  WEB SERVER SELECTION — Ask admin which engine to install
# =============================================================================
VOIDPANEL_STATE_DIR="/etc/voidpanel"
VOIDPANEL_ENGINE_FILE="$VOIDPANEL_STATE_DIR/web_engine"

echo ""
echo -e "${CYAN}=========================================================="
echo "  VoidPanel — Web Server Selection"
echo "=========================================================="
echo ""
echo "  [1]  NGINX         (default — fastest raw throughput)"
echo "  [2]  OpenLiteSpeed (OLS — Apache/.htaccess compatible, HTTP/3)"
echo ""
echo -e "  Press Enter within 30 s to accept default [1]${RESET}"
echo ""
read -t 30 -r -p "  Your choice [1|2]: " WEB_CHOICE || WEB_CHOICE="1"

# Normalize input
WEB_CHOICE="${WEB_CHOICE:-1}"
WEB_CHOICE="$(echo "$WEB_CHOICE" | tr -d '[:space:]')"

if [[ "$WEB_CHOICE" == "2" ]]; then
    WEB_ENGINE="ols"
    echo -e "${GREEN}[✔] OpenLiteSpeed selected as primary web server.${RESET}"
else
    WEB_ENGINE="nginx"
    echo -e "${GREEN}[✔] NGINX selected as primary web server.${RESET}"
fi

# Persist the choice so the Django backend knows the engine immediately
mkdir -p "$VOIDPANEL_STATE_DIR"
echo "$WEB_ENGINE" > "$VOIDPANEL_ENGINE_FILE"
chmod 644 "$VOIDPANEL_ENGINE_FILE"

# =============================================================================
#  INSTALL BOTH WEB SERVERS (one active, one installed-but-disabled for hot-swap)
# =============================================================================

# --- Install NGINX ---
status_msg "Installing NGINX"
dnf install -y nginx

# --- Install OpenLiteSpeed ---
status_msg "Installing OpenLiteSpeed (OLS)"
# Add LiteSpeed repositories
rpm -Uvh https://rpms.litespeedtech.com/centos/litespeed-repo-1.1-1.el${RHEL_MAJOR}.noarch.rpm 2>/dev/null || \
    rpm -Uvh https://rpms.litespeedtech.com/centos/litespeed-repo-1.1-1.el8.noarch.rpm 2>/dev/null || true
dnf install -y openlitespeed 2>/dev/null || true

# Set default OLS admin password
if [[ -f /usr/local/lsws/admin/misc/admpass.sh ]]; then
    echo -e "admin\nadmin\n" | /usr/local/lsws/admin/misc/admpass.sh 2>/dev/null || true
fi

# Enable/disable engines based on user choice
if [[ "$WEB_ENGINE" == "ols" ]]; then
    systemctl enable  lsws   2>/dev/null || true
    systemctl disable nginx  2>/dev/null || true
    systemctl stop    nginx  2>/dev/null || true
    NGINX_CONF_DIR="/usr/local/lsws/conf"           # OLS primary conf dir
    status_msg "OpenLiteSpeed will be the primary web server"
else
    systemctl enable  nginx  2>/dev/null || true
    systemctl disable lsws   2>/dev/null || true
    systemctl stop    lsws   2>/dev/null || true
    /usr/local/lsws/bin/lswsctrl stop 2>/dev/null || true
    pkill -9 litespeed 2>/dev/null || true
    NGINX_CONF_DIR="/etc/nginx/conf.d"
    status_msg "NGINX will be the primary web server"
fi

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

# --- 3. Panel Core Setup ---
panelsetup() {
    status_msg "Creating Project Directories"
    mkdir -p "$PROJECT_DIR"
    cd "$PROJECT_DIR"

    status_msg "Initializing Python Virtual Environment"
    python3 -m venv venv
    source venv/bin/activate

    status_msg "Installing Python Workspace Dependencies"
    pip install --upgrade pip
    pip install django uwsgi psutil pexpect requests mysql-connector-python huggingface_hub djangorestframework django-cors-headers

    status_msg "Deploying VoidPanel Source Code"
    if ! wget -q https://voidpanel.com/op/install/almalinux/Archive.zip; then
        # Fall back to the ubuntu archive (same Django codebase)
        if ! wget -q https://voidpanel.com/op/install/ubuntu/Archive.zip; then
            error_msg "Failed to download Archive.zip."
            exit 1
        fi
    fi
    unzip -o Archive.zip
    rm -f Archive.zip

    status_msg "Configuring Django Environment"
    DJANGO_SETTINGS=$(find . -name "settings.py" | head -n 1)

    if [[ -n "$DJANGO_SETTINGS" ]]; then
        sed -i "s/ALLOWED_HOSTS = .*/ALLOWED_HOSTS = ['*', '$PUBLIC_IP', 'localhost']/" "$DJANGO_SETTINGS"
    fi

    # Initialize Database & Superuser
    python manage.py migrate
    echo "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('admin', 'admin@voidpanel.com', '$DJANGO_SUPERUSER_PASS') if not User.objects.filter(username='admin').exists() else None" | python manage.py shell

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
vacuum = true
die-on-term = true
EOF

    # uWSGI Systemd Service
    cat << EOF > /etc/systemd/system/uwsgi.service
[Unit]
Description=uWSGI service for VoidPanel
After=network.target

[Service]
User=root
Group=nginx
WorkingDirectory=$PROJECT_DIR
ExecStart=$VENV_DIR/bin/uwsgi --ini $PROJECT_DIR/panel.ini
Restart=always

[Install]
WantedBy=multi-user.target
EOF

    status_msg "Configuring Nginx High-Performance Bridge"
    # RHEL uses /etc/nginx/conf.d/ instead of sites-available/sites-enabled
    cat << EOF > "$NGINX_CONF"
server {
    listen 8080;
    server_name $PUBLIC_IP;

    location /static/ {
        alias $PROJECT_DIR/staticfiles/;
    }

    location / {
        include uwsgi_params;
        uwsgi_pass unix:$PROJECT_DIR/panel.sock;
        uwsgi_read_timeout 300s;
        uwsgi_send_timeout 300s;
    }
}

server {
    listen 8082 ssl http2;
    server_name $PUBLIC_IP $HOSTNAME;

    ssl_certificate /etc/nginx/dummy.crt;
    ssl_certificate_key /etc/nginx/dummy.key;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 300s;
    }
}
EOF

    # Remove default nginx server block if it exists
    if [[ -f /etc/nginx/conf.d/default.conf ]]; then
        mv /etc/nginx/conf.d/default.conf /etc/nginx/conf.d/default.conf.disabled
    fi

    status_msg "Applying Permission Hardening"
    chown -R root:nginx "$PROJECT_DIR"
    chmod -R 775 "$PROJECT_DIR"

    # SELinux: allow nginx to connect to uwsgi socket and network
    if command -v setsebool &>/dev/null; then
        status_msg "Configuring SELinux policies"
        setsebool -P httpd_can_network_connect 1 2>/dev/null || true
        setsebool -P httpd_read_user_content 1 2>/dev/null || true
        setsebool -P httpd_enable_homedirs 1 2>/dev/null || true
        # Allow nginx to access the uwsgi socket
        chcon -R -t httpd_sys_rw_content_t "$PROJECT_DIR" 2>/dev/null || true
    fi

    systemctl daemon-reload
    systemctl enable uwsgi
    systemctl start uwsgi
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
CREATE USER IF NOT EXISTS '$DB_USER'@'localhost' IDENTIFIED BY '$DB_PASS';
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
    server_name $PUBLIC_IP;
    root /usr/share/phpmyadmin;
    index index.php;

    location / { try_files \$uri \$uri/ =404; }
    location ~ \.php\$ {
        fastcgi_pass unix:$PHP_FPM_SOCK;
        fastcgi_index index.php;
        fastcgi_param SCRIPT_FILENAME \$document_root\$fastcgi_script_name;
        include fastcgi_params;
    }
}

server {
    listen 8092 ssl http2;
    server_name $PUBLIC_IP $HOSTNAME;
    ssl_certificate /etc/nginx/dummy.crt;
    ssl_certificate_key /etc/nginx/dummy.key;
    root /usr/share/phpmyadmin;
    index index.php;

    location / { try_files \$uri \$uri/ =404; }
    location ~ \.php\$ {
        fastcgi_pass unix:$PHP_FPM_SOCK;
        fastcgi_index index.php;
        fastcgi_param SCRIPT_FILENAME \$document_root\$fastcgi_script_name;
        include fastcgi_params;
    }
}
EOF

    if command -v chcon &>/dev/null; then
        chcon -R -t httpd_sys_rw_content_t /usr/share/phpmyadmin 2>/dev/null || true
    fi
    success_msg "Database Management Stack Integrated"
}

# --- 9. Email (Postfix & Dovecot) Setup ---
emailsetup() {
    status_msg "Configuring Enterprise Mail Stack (Postfix/Dovecot)"

    # Mail user (owns all mailboxes)
    groupadd -g 5000 vmail 2>/dev/null || true
    useradd -s /sbin/nologin -u 5000 -g 5000 -d /home/vmail vmail 2>/dev/null || true
    mkdir -p /home/vmail/mail
    chown -R vmail:vmail /home/vmail

    # Postfix main.cf — deliver via Dovecot LMTP so per-user paths work
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

# SASL
smtpd_sasl_type = dovecot
smtpd_sasl_path = private/auth
smtpd_sasl_auth_enable = yes

# Virtual Mailbox Settings — delivery handled by Dovecot LMTP
virtual_mailbox_domains = /etc/postfix/virtual_domains
virtual_mailbox_maps = hash:/etc/postfix/vmailbox
virtual_alias_maps = hash:/etc/postfix/virtual_alias
virtual_transport = lmtp:unix:private/dovecot-lmtp

# Standard SMTP Restrictions
smtpd_recipient_restrictions = permit_sasl_authenticated,permit_mynetworks,reject_unauth_destination
EOF

    touch /etc/postfix/virtual_domains /etc/postfix/vmailbox /etc/postfix/virtual_alias
    postmap /etc/postfix/virtual_alias /etc/postfix/vmailbox

    # Dovecot Configuration
    cat << EOF > /etc/dovecot/dovecot.conf
protocols = imap pop3 lmtp
listen = *, ::
!include conf.d/*.conf
!include_try /usr/share/dovecot/protocols.d/*.conf
EOF

    cat << EOF > /etc/dovecot/conf.d/10-master.conf
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

    status_msg "Configuring Mail Services Enablement"
    systemctl enable --now postfix dovecot
    systemctl restart postfix dovecot
    success_msg "Mail Stack Online"
}

# --- 10. Service Orchestration ---
final_restart() {
    status_msg "Synchronizing System Services"
    systemctl restart nginx uwsgi php-fpm mariadb named vsftpd postfix dovecot
    systemctl enable nginx uwsgi php-fpm mariadb named vsftpd postfix dovecot
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
    TCP_IN="20,21,22,25,53,80,110,143,443,465,587,953,993,995,3306,8080,8082,8090,8092,9000,9002,33060"
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
