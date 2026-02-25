# Variables
#!/bin/bash
PROJECT_NAME="panel"
PHP_VERSION="8.3"
PROJECT_DIR="/var/www/$PROJECT_NAME"
VENV_DIR="$PROJECT_DIR/venv"
UWSGI_INI="$PROJECT_DIR/$PROJECT_NAME.ini"
NGINX_CONF="/etc/nginx/sites-available/$PROJECT_NAME"
NGINX_CONFf="/etc/nginx/sites-available/phpmyadmin"
NGINX_CONF_LINK="/etc/nginx/sites-enabled/$PROJECT_NAME"
DJANGO_SETTINGS="$PROJECT_DIR/$PROJECT_NAME/settings.py"
PUBLIC_IP=$(curl -s ifconfig.me)
MYSQL_USER="panel"
MYSQL_USER_PASS=$(openssl rand -base64 12)
DJANGO_SUPERUSER_PASSWORD=$(openssl rand -base64 12)
MYSQL_ROOT_PASSWORD=$(openssl rand -base64 12)
ROUNDCUBE_PASSWORD=$(openssl rand -base64 12)
MYSQL_ROOT_PASS=$(openssl rand -base64 12)
INSTALL_DIR="/usr/share/phpmyadmin"
ROUNDCUBE_DB="roundcube"
ROUNDCUBE_USER="roundcubeuser"
NGINX_CONFR="/etc/nginx/sites-available/roundcube"
PORT="9000"
LOG_FILE="/root/error_log.txt"
HOSTNAME=$(hostname)
MYSQL_USERR="mailuser"
MYSQL_PASS=$(openssl rand -base64 12)       
NEWUSER=$(openssl rand -base64 12)     
MYSQL_DB="mailserver"





#log error
log_error() {
    echo "$(date): $1" >> "$LOG_FILE"
}

#check installled service
check_installed() {
    if dpkg -l | grep -q "$1"; then
        echo "$1 is installed."
        log_error "Other Web Service is Installed"
        exit 1
    fi
}


#check sudo permission
check_permission(){
    if sudo -n true 2>/dev/null; then
    echo "You have sudo privileges."
else
    log_error "You do NOT have sudo privileges. Exiting script."
    exit 1
fi
}


#install all packages
packages() {
    
    sudo apt update
    # Install software-properties-common to manage repositories
    sudo apt install -y software-properties-common
    sudo apt-get install -y debconf-utils
    # Add the PHP PPA (Personal Package Archive) to your system automatically
    sudo add-apt-repository -y ppa:ondrej/php
    echo "Updating and upgrading the system..."
    echo "Installing necessary packages..."
    sudo apt install -y python3-pip python3-dev python3-venv nginx unzip
    sudo apt-get install -y certbot python3-certbot-nginx
    sudo apt install -y bind9 bind9utils bind9-doc opendkim opendkim-tools
    log_error "Packages Installed till bind"
    sudo apt install quota
    log_error "Installing PHP Now"
    sudo apt install -y git php${PHP_VERSION}-mbstring php${PHP_VERSION}-zip php${PHP_VERSION}-gd php${PHP_VERSION}-curl nginx mysql-server
    log_error "PHP Installed"
    sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout /etc/nginx/dummy.key -out /etc/nginx/dummy.crt -subj "/CN=localhost"

}

#setupBasic Panel Requirement ll
panelsetup(){

# Create project directory
echo "Creating project directory..."
sudo mkdir -p $PROJECT_DIR
sudo chown $USER:$USER $PROJECT_DIR
# Navigate to project directory
cd $PROJECT_DIR
# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv
# Activate virtual environment
source $VENV_DIR/bin/activate
# Upgrade pip and install Django and uWSGI
echo "Upgrading pip and installing Django and uWSGI..."
pip install --upgrade pip
pip install django uwsgi
pip install psutil
pip install pexpect
pip install requests
pip install mysql-connector-python
pip install huggingface_hub

pip install djangorestframework



# Download and unzip project files
echo "Downloading and unzipping project files..."
wget https://voidpanel.com/op/install/ubuntu/Archive.zip
unzip Archive.zip
echo "from django.contrib.auth import get_user_model; 
User = get_user_model(); 
user = User.objects.get(username='admin'); 
user.set_password('$DJANGO_SUPERUSER_PASSWORD'); 
user.save();" | python manage.py shell

#deactivating
deactivate
sed -i "/ALLOWED_HOSTS = \[/c\ALLOWED_HOSTS = ['$PUBLIC_IP', 'localhost', '127.0.0.1','*']" $DJANGO_SETTINGS

sed -i "s/changetoip/$PUBLIC_IP/g" $DJANGO_SETTINGS


cat << EOF > $UWSGI_INI
[uwsgi]
chdir = $PROJECT_DIR
module = $PROJECT_NAME.wsgi:application
home = $VENV_DIR
master = true
processes = 5
socket = $PROJECT_DIR/$PROJECT_NAME.sock
chmod-socket = 664
vacuum = true
die-on-term = true
EOF

cat <<EOF | tee /etc/version.txt
1.0
EOF

cat <<EOF | tee /var/log/ssl.txt
SSL Informations
EOF

# Create systemd service for uWSGI
echo "Creating uWSGI systemd service..."
sudo bash -c "cat > /etc/systemd/system/uwsgi.service" << EOL
[Unit]
Description=uWSGI Emperor service

[Service]
ExecStart=$VENV_DIR/bin/uwsgi --ini $UWSGI_INI


[Install]
WantedBy=multi-user.target
EOL

# Start and enable uWSGI service
echo "Starting and enabling uWSGI service..."
sudo chown root:www-data /var/www/panel
sudo chmod g+s /var/www/panel
sudo systemctl daemon-reload
sudo systemctl start uwsgi




sudo systemctl enable uwsgi

# Configure Nginx for Django
echo "Configuring Nginx for Django..."
sudo bash -c "cat > $NGINX_CONF" << EOL
server {
    listen 8080;
    server_name $PUBLIC_IP;

    location = /favicon.ico { access_log off; log_not_found off; }
    location /static/ {
        alias $PROJECT_DIR/static/;
    }

    location /view/ {
        alias /;
    }
   

    location / {
        include uwsgi_params;
        uwsgi_pass unix:$PROJECT_DIR/$PROJECT_NAME.sock;
        uwsgi_buffering off; # Important for streaming
        uwsgi_read_timeout 600s;
    }
    client_max_body_size 300M; 
    client_body_timeout 600s; 
}
server {
    listen 8082 ssl;
    server_name $PUBLIC_IP $HOSTNAME;

    ssl_certificate /etc/nginx/dummy.crt ;
    ssl_certificate_key /etc/nginx/dummy.key ;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_buffering off;
        proxy_request_buffering off;

        # Increase timeout for long-running connections
        proxy_read_timeout 600s;
        proxy_send_timeout 600s;

        # Optional: Adjust buffer sizes
        proxy_buffers 16 16k;
        proxy_buffer_size 32k;
    }
       http2_max_field_size 16k;
    http2_max_header_size 32k;
       client_max_body_size 300M; 
    client_body_timeout 600s; 

}
EOL

# Enable Nginx configuration
echo "Enabling Nginx configuration..."
sudo ln -s $NGINX_CONF $NGINX_CONF_LINK

# Set permissions for the socket file
echo "Setting permissions for the socket file..."
sudo chmod 664 $PROJECT_DIR/$PROJECT_NAME.sock
sudo chown $USER:www-data $PROJECT_DIR/$PROJECT_NAME.sock

# Set permissions for static files
echo "Setting permissions for static files..."
sudo chown -R $USER:www-data $PROJECT_DIR/static/
sudo chmod -R 775 $PROJECT_DIR/static/
log_error "Panel Installed"
}

bind(){
    sudo cp /etc/bind/named.conf.options /etc/bind/named.conf.options.backup

# Configure BIND with default options
sudo bash -c 'cat > /etc/bind/named.conf.options' << EOF
options {
    directory "/var/cache/bind";

    // Uncomment and set your DNS forwarders here if needed
    // forwarders {
    //     8.8.8.8;
    //     8.8.4.4;
    // };

    dnssec-validation auto;

    auth-nxdomain no;    # conform to RFC1035
    listen-on-v6 { any; };
};
EOF

sudo apt autoremove -y
sudo apt clean
log_error "bind Installed"
}

quota(){
    MOUNTPOINT="/"          
sudo sed -i "s/errors=remount-ro/errors=remount-ro,usrquota,grpquota/g" /etc/fstab

echo "Reloading systemd to recognize changes in /etc/fstab..."
sudo systemctl daemon-reload

echo "Remounting ${MOUNTPOINT} to apply quota settings..."
sudo mount -o remount ${MOUNTPOINT}

sudo quotacheck -ugm / -f
sudo quotaon -v /

}

roundcube(){
 sudo debconf-set-selections <<< "roundcube-core roundcube/dbconfig-install boolean true"
sudo debconf-set-selections <<< "roundcube-core roundcube/database-type select mysql"
sudo debconf-set-selections <<< "roundcube-core roundcube/mysql/admin-pass password $MYSQL_ROOT_PASSWORD"
sudo debconf-set-selections <<< "roundcube-core roundcube/db/dbname string $ROUNDCUBE_DB"
sudo debconf-set-selections <<< "roundcube-core roundcube/mysql/app-pass password $ROUNDCUBE_PASSWORD"
sudo debconf-set-selections <<< "roundcube-core roundcube/app-password-confirm password $ROUNDCUBE_PASSWORD"
sudo debconf-set-selections <<< "roundcube-core roundcube/dbconfig-reinstall boolean false"

sudo DEBIAN_FRONTEND=noninteractive apt-get install -y roundcube roundcube-mysql nginx php${PHP_VERSION}-fpm php${PHP_VERSION}-mbstring php${PHP_VERSION}-mysqli
cd /var/www/
wget https://github.com/roundcube/roundcubemail/releases/download/1.6.9/roundcubemail-1.6.9-complete.tar.gz
tar -xvzf roundcubemail-1.6.9-complete.tar.gz
mv roundcubemail-1.6.9 roundcube
sudo chown -R www-data:www-data /var/www/roundcube/temp /var/www/roundcube/logs
sudo chmod -R 755 /var/www/roundcube/temp /var/www/roundcube/logs
cd /var/www/roundcube
rm -r installer
sudo cp /var/www/roundcube/config/config.inc.php.sample /var/www/roundcube/config/config.inc.php
sudo sed -i "s|^\\\$config\['db_dsnw'\] = 'mysql://roundcube:.*@localhost/roundcubemail';|\\\$config['db_dsnw'] = 'mysql://$ROUNDCUBE_USER:$ROUNDCUBE_PASSWORD@localhost/$ROUNDCUBE_DB';|" /var/www/roundcube/config/config.inc.php

# Secure MySQL installation and create database and user
sudo mysql -u root -p$MYSQL_ROOT_PASSWORD <<EOF
-- Delete the user if it exists
DROP USER IF EXISTS '$ROUNDCUBE_USER'@'localhost';

-- Create the user
CREATE USER '$ROUNDCUBE_USER'@'localhost' IDENTIFIED BY '$ROUNDCUBE_PASSWORD';

-- Create the database if it does not exist
CREATE DATABASE IF NOT EXISTS $ROUNDCUBE_DB;

-- Grant all privileges to the user for the Roundcube database
GRANT ALL PRIVILEGES ON $ROUNDCUBE_DB.* TO '$ROUNDCUBE_USER'@'localhost';

-- Flush privileges to ensure changes are applied
FLUSH PRIVILEGES;
EOF
sudo apt install -y php7.4 php7.4-fpm php7.4-mysql php7.4-imap php7.4-xml php7.4-mbstring php7.4-curl php7.4-zip php7.4-gd php7.4-intl



# Configure Nginx to use port 9000 for Roundcube with server IP address
sudo bash -c "cat > $NGINX_CONFR" <<EOL
server {
    listen $PORT;
    server_name $PUBLIC_IP;

    root /var/www/roundcube;
    index index.php;

    location / {
        try_files \$uri \$uri/ /index.php;
    }

    location ~ \.php\$ {
        include snippets/fastcgi-php.conf;
        fastcgi_pass unix:/var/run/php/php7.4-fpm.sock;
        fastcgi_param SCRIPT_FILENAME \$document_root\$fastcgi_script_name;
        include fastcgi_params;
    }

    location ~* ^/(README|INSTALL|LICENSE|CHANGELOG|UPGRADING)\$ {
        deny all;
    }

    location ~ /\. {
        deny all;
        access_log off;
        log_not_found off;
    }
}
server {
    listen 9002 ssl;
    server_name $PUBLIC_IP $HOSTNAME;

    ssl_certificate /etc/nginx/dummy.crt ;
    ssl_certificate_key /etc/nginx/dummy.key ;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers HIGH:!aNULL:!MD5;

    root /var/www/roundcube;
    index index.php;

    location / {
        try_files \$uri \$uri/ /index.php;
    }

    location ~ \.php\$ {
        include snippets/fastcgi-php.conf;
        fastcgi_pass unix:/var/run/php/php7.4-fpm.sock;
        fastcgi_param SCRIPT_FILENAME \$document_root\$fastcgi_script_name;
        include fastcgi_params;
    }

    location ~* ^/(README|INSTALL|LICENSE|CHANGELOG|UPGRADING)\$ {
        deny all;
    }

    location ~ /\. {
        deny all;
        access_log off;
        log_not_found off;
    }

}
EOL
sudo ln -s /etc/nginx/sites-available/roundcube /etc/nginx/sites-enabled/
sudo apt-get remove --purge apache2 -y
}


ftp(){
    # Install vsftpd
echo "Installing vsftpd..."
sudo apt-get install vsftpd -y

# Backup the original vsftpd configuration file
echo "Backing up the original vsftpd.conf..."
sudo cp /etc/vsftpd.conf /etc/vsftpd.conf.bak

# Configure vsftpd
echo "Configuring vsftpd..."
sudo tee /etc/vsftpd.conf > /dev/null <<EOL
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
EOL

}

phpmyadmin(){
    sudo DEBIAN_FRONTEND=noninteractive apt-get install -y phpmyadmin
    # Create symbolic link for phpMyAdmin
if [ -L "/var/www/html/phpmyadmin" ]; then
    echo "Symbolic link for phpMyAdmin already exists. Skipping link creation."
else
    sudo ln -s "$INSTALL_DIR" /var/www/html/phpmyadmin
fi

if [ ! -f /etc/nginx/sites-available/phpmyadmin ]; then
    sudo bash -c "cat > /etc/nginx/sites-available/phpmyadmin <<EOF

server {
    listen 8090;
    server_name $PUBLIC_IP;

   root /usr/share/phpmyadmin;
    index index.php index.html index.htm;
    client_max_body_size 1500M;

    

    location ~ \.php$ {
        include snippets/fastcgi-php.conf;
        fastcgi_pass unix:/var/run/php/php${PHP_VERSION}-fpm.sock;
        fastcgi_param SCRIPT_FILENAME  loll;
        include fastcgi_params;
    }

    location /phpmyadmin {
        alias /usr/share/phpmyadmin;
        index index.php;

        location ~ ^/phpmyadmin/(.+\.php)$ {
            alias /usr/share/phpmyadmin/$1;
            fastcgi_pass unix:/var/run/php/php${PHP_VERSION}-fpm.sock;
            fastcgi_index index.php;
            include fastcgi_params;
        }

        location ~ ^/phpmyadmin/(.+\.(gif|jpe?g|png|ico|css|js))$ {
            alias /usr/share/phpmyadmin/$1;
        }
    }
}
server {
    listen 8092 ssl;
    server_name $PUBLIC_IP $HOSTNAME;
    client_max_body_size 64M;

    ssl_certificate /etc/nginx/dummy.crt ;
    ssl_certificate_key /etc/nginx/dummy.key ;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location / {
        proxy_pass http://127.0.0.1:8090;
        proxy_set_header Host zod;
        proxy_set_header X-Real-IP wwe;
        proxy_set_header X-Forwarded-For yum;
        proxy_set_header X-Forwarded-Proto hum;
    }

}
EOF"
fi
sudo sed -i 's|loll|$document_root$fastcgi_script_name|' $NGINX_CONFf
sudo sed -i 's|zod|$host|' $NGINX_CONFf
sudo sed -i 's|wwe|$remote_addr|' $NGINX_CONFf
sudo sed -i 's|yum|$proxy_add_x_forwarded_for|' $NGINX_CONFf
sudo sed -i 's|hum|$scheme|' $NGINX_CONFf
sudo ln -s /etc/nginx/sites-available/phpmyadmin /etc/nginx/sites-enabled/
sudo chown -R www-data:www-data /usr/share/phpmyadmin
sudo chmod -R 755 /usr/share/phpmyadmin
}


restart(){
sudo systemctl start uwsgi
sudo systemctl enable uwsgi
sudo systemctl restart nginx
sudo systemctl enable nginx
sudo systemctl restart php7.4-fpm
sudo systemctl enable php7.4-fpm
sudo systemctl enable postfix
sudo systemctl enable dovecot

sudo systemctl restart php${PHP_VERSION}-fpm
# Restart BIND to apply changes
sudo systemctl restart bind9
# Enable BIND to start on boot
sudo systemctl enable named
sudo systemctl enable php${PHP_VERSION}-fpm
systemctl restart postfix
systemctl restart dovecot


}


#!/bin/bash

emailset() {




# Update and install necessary packages
apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y postfix dovecot-core dovecot-pop3d dovecot-imapd
groupadd -g 5000 vmail
useradd -s /usr/sbin/nologin -u 5000 -g 5000 vmail
usermod -aG vmail postfix
usermod -aG vmail dovecot
touch /var/log/dovecot
chgrp vmail /var/log/dovecot
chmod 660 /var/log/dovecot
touch /etc/postfix/virtual_domains
touch /etc/postfix/vmailbox
touch /etc/postfix/virtual_alias
postmap /etc/postfix/virtual_alias


file_path="/etc/postfix/main.cf"
lines_to_add="
virtual_mailbox_domains = /etc/postfix/virtual_domains
virtual_mailbox_base = /var/mail/vhosts
virtual_mailbox_maps = hash:/etc/postfix/vmailbox
virtual_alias_maps = hash:/etc/postfix/virtual_alias
virtual_minimum_uid = 100
virtual_uid_maps = static:5000
virtual_gid_maps = static:5000
virtual_transport = virtual
virtual_mailbox_limit = 104857600
##SASL##
smtpd_sasl_auth_enable = yes
smtpd_sasl_type = dovecot
smtpd_sasl_path = private/auth
smtpd_sasl_security_options = noanonymous
broken_sasl_auth_clients = yes

smtpd_milters = inet:localhost:8891
non_smtpd_milters = \$smtpd_milters
milter_default_action = accept

##TLS##
smtpd_use_tls = yes
smtpd_tls_security_level = may
smtpd_tls_auth_only = no
smtpd_tls_received_header = yes
smtpd_tls_security_level = may
smtp_tls_security_level = may
tls_random_source = dev:/dev/urandom

##restrictions##
smtpd_helo_required = no
smtpd_delay_reject = yes
strict_rfc821_envelopes = yes
disable_vrfy_command = yes

##limit rate##
anvil_rate_time_unit = 60s
smtpd_client_connection_rate_limit = 5
smtpd_client_connection_count_limit = 5

smtpd_error_sleep_time = 5s
smtpd_soft_error_limit = 2
smtpd_hard_error_limit = 3
##################

smtpd_helo_restrictions = permit_mynetworks,
  permit_sasl_authenticated,
  reject_non_fqdn_hostname,
  reject_invalid_helo_hostname,
  reject_unknown_helo_hostname

smtpd_client_restrictions = permit_mynetworks,
  permit_sasl_authenticated,
  reject_unknown_client_hostname,
  reject_unauth_pipelining,
  reject_rbl_client zen.spamhaus.org

smtpd_sender_restrictions = reject_non_fqdn_sender,
  reject_unknown_sender_domain

smtpd_recipient_restrictions = permit_mynetworks,
  permit_sasl_authenticated,
  reject_invalid_hostname,
  reject_non_fqdn_hostname,
  reject_non_fqdn_sender,
  reject_non_fqdn_recipient,
  reject_unauth_destination,
  reject_unauth_pipelining,
  reject_rbl_client zen.spamhaus.org,
  reject_rbl_client cbl.abuseat.org,
  reject_rbl_client dul.dnsbl.sorbs.net

smtpd_recipient_limit = 250
broken_sasl_auth_clients = yes"
echo "$lines_to_add" >> "$file_path"


# Configure Dovecot
cat > /etc/dovecot/dovecot.conf <<EOF
auth_mechanisms = plain login
disable_plaintext_auth = no
log_path = /var/log/dovecot
mail_location = maildir:/var/mail/vhosts/%d/%n


passdb {
	args = /var/mail/vhosts/%d/shadow
	driver = passwd-file
}

protocols = imap pop3

service auth {
	unix_listener /var/spool/postfix/private/auth {
		group = vmail
		mode = 0660
		user = postfix
	}
		unix_listener auth-master {
		group = vmail
		mode = 0600
		user = vmail
	}
}


userdb {
	args = /var/mail/vhosts/%d/passwd
	driver = passwd-file
}

protocol lda {
	auth_socket_path = /var/run/dovecot/auth-master
	hostname = CHANGETHIS, example: imouto.moe
	mail_plugin_dir = /usr/lib/dovecot/modules
	mail_plugins = sieve
	postmaster_address = CHANGETHIS, example: postmaster@imouto.moe
}
EOF

# Configure Dovecot
cat > /etc/dovecot/conf.d/10-mail.conf <<EOF
mail_location = maildir:/var/mail/vhosts/%d/%n
	namespace inbox {

   
  inbox = yes

}
mail_privileged_group = mail

protocol !indexer-worker {

}
EOF

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

service submission-login {
  inet_listener submission {
    #port = 587
  }
}

service lmtp {
  unix_listener lmtp {
   
  }

 
}

service imap {
  
}

service pop3 {
 
}

service submission {

}
service auth {
  
  unix_listener auth-userdb {
 
  }


}

service auth-worker {

}

service dict {
  
  unix_listener dict {

  }
}

EOF






cat > /etc/dovecot/conf.d/10-mail.conf <<EOF
auth_mechanisms = plain login
!include auth-system.conf.ext
EOF


cat > /etc/postfix/master.cf <<EOF
smtp       inet  n       -       -       -       -       smtpd
587       inet  n       -       -       -       -       smtpd
smtps      inet  n       -       -       -       -       smtpd
submission inet  n       -       n       -       -       smtpd
pickup     fifo  n       -       -       60      1       pickup
cleanup    unix  n       -       -       -       0       cleanup
qmgr       fifo  n       -       n       300     1       qmgr
tlsmgr     unix  -       -       -       1000?   1       tlsmgr
rewrite    unix  -       -       -       -       -       trivial-rewrite
bounce     unix  -       -       -       -       0       bounce
defer      unix  -       -       -       -       0       bounce
trace      unix  -       -       -       -       0       bounce
verify     unix  -       -       -       -       1       verify
flush      unix  n       -       -       1000?   0       flush
proxymap   unix  -       -       n       -       -       proxymap
proxywrite unix  -       -       n       -       1       proxymap
smtp       unix  -       -       -       -       -       smtp
relay      unix  -       -       -       -       -       smtp
showq      unix  n       -       -       -       -       showq
error      unix  -       -       -       -       -       error
retry      unix  -       -       -       -       -       error
discard    unix  -       -       -       -       -       discard
local      unix  -       n       n       -       -       local
virtual    unix  -       n       n       -       -       virtual
lmtp       unix  -       -       -       -       -       lmtp
anvil      unix  -       -       -       -       1       anvil
scache     unix  -       -       -       -       1       scache
uucp       unix  -       n       n       -       -       pipe
  flags=Fqhu user=uucp argv=uux -r -n -z -a\$sender - \$nexthop!rmail (\$recipient)
ifmail     unix  -       n       n       -       -       pipe
  flags=F user=ftn argv=/usr/lib/ifmail/ifmail -r \$nexthop (\$recipient)
bsmtp      unix  -       n       n       -       -       pipe
  flags=Fq. user=bsmtp argv=/usr/lib/bsmtp/bsmtp -t\$nexthop -f\sender \$recipient
scalemail-backend unix	-	n	n	-	2	pipe
  flags=R user=scalemail argv=/usr/lib/scalemail/bin/scalemail-store \${nexthop} \${user} \${extension}
mailman    unix  -       n       n       -       -       pipe
  flags=FR user=list argv=/usr/lib/mailman/bin/postfix-to-mailman.py
  \${nexthop} \${user}
dovecot    unix  -       n       n       -       -       pipe
  flags=DRhu user=vmail:vmail argv=/usr/lib/dovecot/deliver -f \${sender} -d \${recipient}
EOF






mkdir -p /var/mail/vhosts/
chown -R vmail:vmail /var/mail/vhosts
chmod -R 775 /var/mail/vhosts


# Restart services
systemctl restart postfix
systemctl restart dovecot





}


install_ftp_server() {
    # Update package list
    echo "Updating package list..."
    sudo apt update

    # Install vsftpd if not already installed
    if ! command -v vsftpd &> /dev/null; then
        echo "vsftpd not found, installing..."
        sudo apt install -y vsftpd
    else
        echo "vsftpd is already installed."
    fi

    # Backup the original configuration file
    echo "Backing up the original configuration file..."
    sudo cp /etc/vsftpd.conf /etc/vsftpd.conf.bak

    # Configure vsftpd
    echo "Configuring vsftpd..."
    {
        echo "# Custom vsftpd configuration"
        echo "listen=YES"
        echo "anonymous_enable=NO"
        echo "local_enable=YES"
        echo "write_enable=YES"
        echo "local_umask=022"
        echo "dirmessage_enable=YES"
        echo "xferlog_enable=YES"
        echo "connect_from_port_20=YES"
        echo "xferlog_file=/var/log/vsftpd.log"
        echo "xferlog_std_format=YES"
        echo "pam_service_name=vsftpd"
        echo "userlist_enable=YES"
        echo "tcp_wrappers=YES"
        echo "chroot_local_user=YES"
        echo "allow_writeable_chroot=YES"
        echo "userlist_file=/etc/vsftpd.userlist"
        echo "userlist_deny=NO"





      

    } | sudo tee /etc/vsftpd.conf

    # Restart vsftpd service
    # echo "Starting vsftpd service..."
    # sudo systemctl restart vsftpd

    # # Enable vsftpd to start on boot
    # echo "Enabling vsftpd to start on boot..."
    # sudo systemctl enable vsftpd

    echo "FTP server installation and configuration complete."
}


firewall(){


# Install necessary dependencies
echo "Installing required packages..."
sudo apt-get install -y perl libwww-perl unzip || sudo yum install -y perl-libwww-perl.noarch unzip

# Download and install CSF
echo "Downloading and installing CSF..."
cd /usr/src
sudo wget https://download.configserver.com/csf.tgz
sudo tar -xzf csf.tgz
cd csf
sudo sh install.sh

ports=(
  "443"
  "80"
  "22"
  "9000"
  "9002"
  "143"
  "21"
  "20"
  "53"
  "33060"
  "3306"
  "110"
  "993"
  "995"
  "25"
  "587"
  "465"
  "953"
  "8080"
  "8082"
  "8090"
  "8092"
)

CONFIG_FILE="/etc/csf/csf.conf"

for port in "${ports[@]}"
do

# Check if the port is already in the configuration
if grep -q "$port" $CONFIG_FILE; then
  echo "Port $port is already configured in CSF."
else
# Add the port to TCP_IN and TCP_OUT in the CSF configuration
echo "Adding port $port to TCP_IN and TCP_OUT..."
sudo sed -i "/^TCP_IN/s/\"$/,$port\"/" $CONFIG_FILE
sudo sed -i "/^TCP_OUT/s/\"$/,$port\"/" $CONFIG_FILE


echo "Port $port added and CSF reloaded successfully."

fi

done
# Reload CSF to apply changes
echo "Reloading CSF..."
sudo csf -r










# sudo csf --deny 3306
sudo systemctl start csf
sudo systemctl enable csf
sudo systemctl enable lfd
}
#!/bin/bash

# Define the function
save_details() {
    cat <<EOF | tee /etc/details.txt
VoidPanel_Username='admin'
VoidPanel_Password="$DJANGO_SUPERUSER_PASSWORD"
MYSQL_ROOT_Username='root'
MYSQL_ROOT_Password="$MYSQL_ROOT_PASSWORD"
ROUNDCUBE_Password="$ROUNDCUBE_PASSWORD"
EOF

    # Echo the details to the terminal
    echo "Details saved in /etc/details.txt:"
    cat /etc/details.txt
}


  




echo_details() {
    # Echo the details
    echo "Admin_Link: https://$PUBLIC_IP:8082"
    echo "----------------or-----------------"
    echo "Admin_Link: http://$PUBLIC_IP:8080"
    echo "username: admin"
    echo "Password: $DJANGO_SUPERUSER_PASSWORD"
    
    
}

ioncube(){

IONCUBE_URL="https://downloads.ioncube.com/loader_downloads/ioncube_loaders_lin_x86-64.tar.gz"
TMP_DIR="/tmp/ioncube"
IONCUBE_DIR="$TMP_DIR/ioncube"

# Download and extract IonCube Loader
echo "Downloading IonCube Loader..."
mkdir -p $TMP_DIR
wget -qO- $IONCUBE_URL | tar -xz -C $TMP_DIR


# Iterate over each PHP version
for PHP_VERSION in $PHP_VERSIONS; do
  echo "Processing PHP $PHP_VERSION..."

  # Verify if PHP is installed for this version
  if ! command -v php$PHP_VERSION >/dev/null 2>&1; then
    echo "PHP $PHP_VERSION binary not found. Skipping..."
    continue
  fi

  # Determine PHP extension directory
  EXT_DIR=$(php$PHP_VERSION -i | grep extension_dir | awk '{print $3}')
  if [ -z "$EXT_DIR" ]; then
    echo "Failed to locate PHP extension directory for PHP $PHP_VERSION. Skipping..."
    continue
  fi

  # Determine PHP INI file
  INI_FILE=$(php$PHP_VERSION --ini | grep "Loaded Configuration File" | awk '{print $4}')
  if [ -z "$INI_FILE" ]; then
    echo "Failed to locate PHP INI file for PHP $PHP_VERSION. Skipping..."
    continue
  fi

  # Copy the appropriate IonCube loader
  IONCUBE_SO="ioncube_loader_lin_$PHP_VERSION.so"
  if [ ! -f "$IONCUBE_DIR/$IONCUBE_SO" ]; then
    echo "IonCube Loader for PHP $PHP_VERSION is not available. Skipping..."
    continue
  fi

  echo "Installing IonCube Loader for PHP $PHP_VERSION..."
  cp "$IONCUBE_DIR/$IONCUBE_SO" "$EXT_DIR"

  # Enable IonCube Loader in PHP INI
  if ! grep -q "ioncube_loader" $INI_FILE; then
    echo "zend_extension = $EXT_DIR/$IONCUBE_SO" >> $INI_FILE
  fi

  # Restart PHP-FPM
  echo "Restarting PHP-FPM for PHP $PHP_VERSION..."
  systemctl restart php$PHP_VERSION-fpm
done

# Clean up
echo "Cleaning up..."
rm -rf $TMP_DIR

# Verify installation
for PHP_VERSION in $PHP_VERSIONS; do
  if php$PHP_VERSION -m | grep -q "ionCube Loader"; then
    echo "IonCube Loader installed successfully for PHP $PHP_VERSION!"
  else
    echo "IonCube Loader installation failed for PHP $PHP_VERSION."
  fi
done

echo "IonCube Loader installation process completed."

}

#main

check installation
check_permission
packages
panelsetup
bind
quota
emailset
roundcube
phpmyadmin
install_ftp_server
ioncube

# sudo phpenmod mbstring
sudo  apt-get install -y shellinabox
cd /etc/shellinabox/options-enabled
sudo mv 00+Black\ on\ White.css 00_Black\ on\ White.css
sudo mv 00_White\ On\ Black.css 00+White\ On\ Black.css





rm -rf /var/www/html/*
cp -r /var/www/panel/voidpanel/*  /var/www/html/
mkdir -p /var/www/suspend/
cp -r /var/www/panel/suspend/*  /var/www/suspend/




#firewall
# success: function (response) {
#                             if (response.status === 'success') {
#                                 alert('File deleted successfully!');
#                                 var row = document.getElementById(name);
#                                 if (row) {
#                                     row.parentNode.removeChild(row);
#                                 }
#                             } else {
#                                 alert("Error Deleting File!");
#                             }
#                         },
#                         error: function (xhr, errmsg, err) {
#                             alert("Error Deleting File!");
#                         }

#   try:
#             os.remove(f'/{file_path}')
#             return JsonResponse({'status':'success'})

#         except Exception as e:
          
#             return JsonResponse({'error':'error'})
#   return JsonResponse({'error':'error'})


# echo "Stopping MySQL service..."
# sudo systemctl stop mysql

# # Start MySQL in safe mode (skip-grant-tables)
# echo "Starting MySQL in safe mode (skip-grant-tables)..."
# sudo mysqld_safe --skip-grant-tables > /dev/null 2>&1 &

# # Wait for MySQL to start
# echo "Waiting for MySQL to start..."
# sleep 5

# # Check if MySQL is running
# if mysqladmin ping -u root > /dev/null 2>&1; then
#     echo "MySQL is running. Proceeding to reset the password..."
#     mysql -u root <<EOF
# FLUSH PRIVILEGES;
# ALTER USER 'root'@'localhost' IDENTIFIED WITH 'mysql_native_password' BY '${MYSQL_ROOT_PASSWORD}';
# FLUSH PRIVILEGES;
# EOF

# fi

# # Stop the MySQL safe mode
# echo "Stopping MySQL safe mode..."
# sudo killall -w mysqld_safe

# # Restart the MySQL service normally
# echo "Restarting MySQL service..."
# sudo systemctl start mysql



sudo mysql -u root -p"$MYSQL_ROOT_PASSWORD" <<EOF
CREATE USER 'newuser'@'localhost' IDENTIFIED BY '$NEWUSER';
GRANT ALL PRIVILEGES ON *.* TO 'newuser'@'localhost' WITH GRANT OPTION;
FLUSH PRIVILEGES;
EOF

cat <<EOF | tee /etc/dontdelete.txt
$NEWUSER
EOF


echo  "Now Rebooting The server"
restart
echo  "Configuring Firewall"
firewall
echo  " Details"
save_details
echo_details

rm -r /var/www/panel/Archive.zip


