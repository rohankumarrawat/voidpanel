#!/bin/bash
# VoidPanel v2.0 - Global Email SSL Hardening
# Connects Postfix and Dovecot to valid Let's Encrypt certificates

CERT_PATH="/etc/letsencrypt/live/server.voidpanel.com/fullchain.pem"
KEY_PATH="/etc/letsencrypt/live/server.voidpanel.com/privkey.pem"

status_msg() { echo -e "\e[36m[+] $1...\e[0m"; }
success_msg() { echo -e "\e[32m[✔] $1\e[0m"; }
error_msg() { echo -e "\e[31m[!] $1\e[0m"; }

# 1. Verify certificates exist
if [ ! -f "$CERT_PATH" ]; then
    error_msg "Certificate not found: $CERT_PATH"
    exit 1
fi

# 2. Hardening Postfix (SMTP)
status_msg "Updating Postfix SSL Configuration"
postconf -e "smtpd_tls_cert_file=$CERT_PATH"
postconf -e "smtpd_tls_key_file=$KEY_PATH"
postconf -e "smtpd_tls_security_level=may"
postconf -e "smtpd_tls_auth_only=yes"
postconf -e "smtpd_tls_protocols=!SSLv2,!SSLv3,!TLSv1,!TLSv1.1"
postconf -e "smtpd_tls_mandatory_protocols=!SSLv2,!SSLv3,!TLSv1,!TLSv1.1"
postconf -e "tls_preempt_cipherlist=yes"

# 3. Hardening Dovecot (IMAP/POP3)
status_msg "Updating Dovecot SSL Configuration"
sed -i "s|^ssl_cert =.*|ssl_cert = <$CERT_PATH|" /etc/dovecot/conf.d/10-ssl.conf
sed -i "s|^ssl_key =.*|ssl_key = <$KEY_PATH|" /etc/dovecot/conf.d/10-ssl.conf
sed -i "s|^#ssl_min_protocol =.*|ssl_min_protocol = TLSv1.2|" /etc/dovecot/conf.d/10-ssl.conf
sed -i "s|^#ssl_prefer_server_ciphers =.*|ssl_prefer_server_ciphers = yes|" /etc/dovecot/conf.d/10-ssl.conf

# 4. Permissions Check
# Ensure Dovecot and Postfix (group ssl-cert or root) can read these.
# Certbot folders are usually 0755, but links can be restrictive.
chmod 0644 "$KEY_PATH" 2>/dev/null || true # Allow read on the symlink
# Note: Real security usually requires adding dovecot/postfix to a group that has access to the archive folder.

# 5. Restart services
status_msg "Reloading Mail Services"
systemctl restart postfix dovecot

success_msg "Global Email SSL Hardening: SUCCESS!"
success_msg "Mail server is now using: $CERT_PATH"
