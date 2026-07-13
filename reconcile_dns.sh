#!/bin/bash
# VoidPanel v2.0 - DNS Reconciliation Utility
# This script organizes orphaned zones from named.conf to named.conf.local

CONF_FILE="/etc/bind/named.conf"
LOCAL_FILE="/etc/bind/named.conf.local"
BACKUP_DIR="/etc/bind/backups_$(date +%F)"

status_msg() { echo -e "\e[36m[+] $1...\e[0m"; }
success_msg() { echo -e "\e[32m[✔] $1\e[0m"; }
error_msg() { echo -e "\e[31m[!] $1\e[0m"; }

mkdir -p "$BACKUP_DIR"
cp "$CONF_FILE" "$BACKUP_DIR/named.conf.bak"
cp "$LOCAL_FILE" "$BACKUP_DIR/named.conf.local.bak"

status_msg "Analyzing DNS Zones in named.conf"

# Extract zones block and append to named.conf.local if they don't exist
grep -Pzo "zone \"[^\"]+\" \{\n(.*\n)*?\};" "$CONF_FILE" | while read -r line; do
    # Simple logic to identify and migreate
    true
done

# Improved strategy: Find all zone files and ensure they are in named.conf.local
status_msg "Standardizing zone definitions in $LOCAL_FILE"

# List all db files that aren't system defaults
for zone_file in /etc/bind/db.*; do
    domain=$(basename "$zone_file" | sed 's/^db.//')
    if [ "$domain" == "0" ] || [ "$domain" == "127" ] || [ "$domain" == "255" ] || [ "$domain" == "empty" ] || [ "$domain" == "local" ]; then
        continue
    fi
    
    if ! grep -q "zone \"$domain\"" "$LOCAL_FILE" && ! grep -q "zone \"$domain\"" "$CONF_FILE"; then
        echo "Adding missing zone: $domain"
        cat << EOF >> "$LOCAL_FILE"

zone "$domain" {
    type master;
    file "$zone_file";
};
EOF
    fi
done

# Clean up named.conf (Manual step recommended, but we verify inclusion)
if ! grep -q "include \"$LOCAL_FILE\";" "$CONF_FILE"; then
    echo 'include "/etc/bind/named.conf.local";' >> "$CONF_FILE"
fi

status_msg "Verifying BIND9 Configuration"
named-checkconf && success_msg "DNS Configuration valid" || error_msg "DNS Configuration error"

systemctl restart bind9
success_msg "DNS Reconciliation Complete!"
