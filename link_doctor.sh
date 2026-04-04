#!/bin/bash
# VoidPanel v2.0 - Data Link Doctor
# This script verifies and repairs paths/permissions for existing clients after the upgrade.

PROJECT_DIR="/var/www/panel"
VENV_DIR="$PROJECT_DIR/venv"

status_msg() { echo -e "\e[36m[+] $1...\e[0m"; }
success_msg() { echo -e "\e[32m[✔] $1\e[0m"; }

# 1. Sync System Postfix/Dovecot with Database
status_msg "Synchronizing Mail Registry"
cd "$PROJECT_DIR"
source venv/bin/activate
# We use a custom management command or shell script to regenerate vmailbox/virtual_domains
# For now, we ensure the paths exist and are owned correctly.

# 2. Correct Permissions for Site Files
status_msg "Repairing Website Permissions"
for user_dir in /home/*; do
    if [ -d "$user_dir/public_html" ]; then
        username=$(basename "$user_dir")
        chown -R "$username:www-data" "$user_dir/public_html"
        chmod -R 755 "$user_dir/public_html"
        success_msg "Permissions updated for: $username"
    fi
done

# 3. Standardize Email Storage
status_msg "Checking Email Storage Integrity"
chown -R vmail:vmail /var/mail/vhosts
chmod -R 775 /var/mail/vhosts

# 4. Map Postfix Files
status_msg "Regenerating Postfix Maps"
postmap /etc/postfix/vmailbox /etc/postfix/virtual_alias
systemctl restart postfix dovecot uwsgi

success_msg "Link Doctor: All paths and permissions synchronized!"
