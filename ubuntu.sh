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
    echo "          VoidPanel Enterprise Installation Pipeline v1.0"
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
NGINX_CONF="/etc/nginx/sites-available/$PROJECT_NAME"
PUBLIC_IP=$(curl -s ifconfig.me)
MYSQL_ROOT_PASS=$(openssl rand -base64 16)
DJANGO_SUPERUSER_PASS=$(openssl rand -base64 16)
HOSTNAME=$(hostname)

print_header

# --- 1. Environment Hardening ---
status_msg "Initializing System Update"
apt-get update -y && apt-get upgrade -y
status_msg "Installing Core Dependencies"
apt-get install -y software-properties-common curl wget git unzip libwww-perl python3-pip python3-dev python3-venv nginx

# Add PHP PPA
status_msg "Configuring PHP Repositories"
add-apt-repository -y ppa:ondrej/php
apt-get update -y

# --- 2. Package Installation ---
status_msg "Installing Service Stack (LEMP + Mail + DNS)"
apt-get install -y \
    php${PHP_VERSION}-fpm php${PHP_VERSION}-mysql php${PHP_VERSION}-mbstring php${PHP_VERSION}-zip \
    php${PHP_VERSION}-gd php${PHP_VERSION}-curl php${PHP_VERSION}-xml php${PHP_VERSION}-intl php${PHP_VERSION}-bcmath \
    mysql-server certbot python3-certbot-nginx \
    bind9 bind9utils quota opendkim opendkim-tools vsftpd \
    postfix dovecot-core dovecot-pop3d dovecot-imapd

# Generate Dummy SSL for Nginx (replaced by Certbot/AutoSSL later)
status_msg "Generating Initial SSL Certificates"
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/nginx/dummy.key -out /etc/nginx/dummy.crt \
    -subj "/CN=localhost"

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
    # Download the project archive
    if ! wget -q https://voidpanel.com/op/install/ubuntu/Archive.zip; then
        error_msg "Failed to download Archive.zip. Ensure it is uploaded to voidpanel.com"
        exit 1
    fi
    unzip -o Archive.zip
    rm Archive.zip

    status_msg "Configuring Django Environment"
    # Find settings.py dynamically
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
chmod-socket = 666
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
Group=www-data
WorkingDirectory=$PROJECT_DIR
ExecStart=$VENV_DIR/bin/uwsgi --ini $PROJECT_DIR/voidpanel.ini
Restart=always

[Install]
WantedBy=multi-user.target
EOF

    status_msg "Configuring Nginx High-Performance Bridge"
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

    ln -sf "$NGINX_CONF" /etc/nginx/sites-enabled/
    rm -f /etc/nginx/sites-enabled/default

    status_msg "Applying Permission Hardening"
    chown -R root:www-data "$PROJECT_DIR"
    chmod -R 775 "$PROJECT_DIR"
    
    systemctl daemon-reload
    systemctl enable uwsgi
    systemctl start uwsgi
    success_msg "Panel Core Setup Complete"
}

# --- 4. DNS (BIND9) Configuration ---
bindsetup() {
    status_msg "Configuring Authoritative DNS (BIND9)"
    cp /etc/bind/named.conf.options /etc/bind/named.conf.options.backup

    cat << EOF > /etc/bind/named.conf.options
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
    systemctl restart bind9
    success_msg "DNS Service Configured"
}

# --- 5. Storage Quota Setup ---
quotasetup() {
    status_msg "Initializing Filesystem Quotas"
    if ! grep -q "usrquota" /etc/fstab; then
        sed -i "s/errors=remount-ro/errors=remount-ro,usrquota,grpquota/g" /etc/fstab
        mount -o remount /
    fi
    quotacheck -ugm / > /dev/null 2>&1
    quotaon -v / > /dev/null 2>&1
    success_msg "Quotas Active"
}

# --- 6. Roundcube Webmail Setup ---
roundcubesetup() {
    status_msg "Preparing Roundcube Database"
    DB_NAME="roundcube"
    DB_USER="roundcube"
    DB_PASS=$(openssl rand -base64 16)

    mysql -u root <<EOF
CREATE DATABASE IF NOT EXISTS $DB_NAME;
CREATE USER IF NOT EXISTS '$DB_USER'@'localhost' IDENTIFIED BY '$DB_PASS';
GRANT ALL PRIVILEGES ON $DB_NAME.* TO '$DB_USER'@'localhost';
FLUSH PRIVILEGES;
EOF

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
    sed -i "s|db_dsnw.*|db_dsnw'\] = 'mysql://$DB_USER:$DB_PASS@localhost/$DB_NAME';|" config/config.inc.php
    
    status_msg "Configuring Roundcube Nginx Bridge"
    cat << EOF > /etc/nginx/sites-available/roundcube
server {
    listen 9000;
    server_name $PUBLIC_IP;
    root /var/www/roundcube;
    index index.php;

    location / { try_files \$uri \$uri/ /index.php; }
    location ~ \.php\$ {
        include snippets/fastcgi-php.conf;
        fastcgi_pass unix:/var/run/php/php${PHP_VERSION}-fpm.sock;
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
        include snippets/fastcgi-php.conf;
        fastcgi_pass unix:/var/run/php/php${PHP_VERSION}-fpm.sock;
    }
}
EOF

    ln -sf /etc/nginx/sites-available/roundcube /etc/nginx/sites-enabled/
    chown -R www-data:www-data /var/www/roundcube
    success_msg "Roundcube Webmail Stack Integrated"
}


# --- 7. FTP (vsftpd) Setup ---
ftpsetup() {
    status_msg "Configuring vsftpd Server"
    cp /etc/vsftpd.conf /etc/vsftpd.conf.bak

    cat << EOF > /etc/vsftpd.conf
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
tcp_wrappers=YES
pasv_min_port=40000
pasv_max_port=50000
EOF

    systemctl restart vsftpd
    systemctl enable vsftpd
    success_msg "FTP Service Hardened"
}

# --- 8. phpMyAdmin Setup ---
phpmyadminsetup() {
    status_msg "Integrating phpMyAdmin"
    export DEBIAN_FRONTEND=noninteractive
    apt-get install -y phpmyadmin

    status_msg "Configuring phpMyAdmin Nginx Bridge"
    cat << EOF > /etc/nginx/sites-available/phpmyadmin
server {
    listen 8090;
    server_name $PUBLIC_IP;
    root /usr/share/phpmyadmin;
    index index.php;

    location / { try_files \$uri \$uri/ =404; }
    location ~ \.php\$ {
        include snippets/fastcgi-php.conf;
        fastcgi_pass unix:/var/run/php/php${PHP_VERSION}-fpm.sock;
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
        include snippets/fastcgi-php.conf;
        fastcgi_pass unix:/var/run/php/php${PHP_VERSION}-fpm.sock;
    }
}
EOF

    ln -sf /etc/nginx/sites-available/phpmyadmin /etc/nginx/sites-enabled/
    chown -R www-data:www-data /usr/share/phpmyadmin
    success_msg "Database Management Stack Integrated"
}
# --- 9. Email (Postfix & Dovecot) Setup ---
emailsetup() {
    status_msg "Configuring Enterprise Mail Stack (Postfix/Dovecot)"
    
    # Base directories
    mkdir -p /var/mail/vhosts
    groupadd -g 5000 vmail || true
    useradd -s /usr/sbin/nologin -u 5000 -g 5000 vmail || true
    chown -R vmail:vmail /var/mail/vhosts

    # Postfix main.cf
    cat << EOF > /etc/postfix/main.cf
myhostname = $HOSTNAME
myorigin = /etc/mailname
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

# Virtual Mailbox Settings
virtual_mailbox_domains = /etc/postfix/virtual_domains
virtual_mailbox_base = /var/mail/vhosts
virtual_mailbox_maps = hash:/etc/postfix/vmailbox
virtual_alias_maps = hash:/etc/postfix/virtual_alias
virtual_uid_maps = static:5000
virtual_gid_maps = static:5000

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
EOF

    cat << EOF > /etc/dovecot/conf.d/10-auth.conf
disable_plaintext_auth = yes
auth_mechanisms = plain login
!include auth-system.conf.ext
EOF

    status_msg "Configuring Mail Services Enablement"
    systemctl restart postfix dovecot
    systemctl enable postfix dovecot
    success_msg "Mail Stack Online"
}

# --- 10. Service Orchestration ---
final_restart() {
    status_msg "Synchronizing System Services"
    systemctl restart nginx uwsgi php${PHP_VERSION}-fpm mysql bind9 vsftpd postfix dovecot
    systemctl enable nginx uwsgi php${PHP_VERSION}-fpm mysql bind9 vsftpd postfix dovecot
    success_msg "All Services Synchronized"
}
}
# --- 11. Security (CSF Firewall) ---
firewallsetup() {
    status_msg "Installing ConfigServer Security & Firewall (CSF)"
    apt-get install -y perl libwww-perl unzip
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

# --- 12. Finalization & Credentials ---
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
    status_msg "VoidPanel Enterprise Pipeline Starting"
    
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
    echo -e "${GREEN}==========================================================${RESET}"
}

# Run the installer
install_main_system
