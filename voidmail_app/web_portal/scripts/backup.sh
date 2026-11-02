#!/bin/bash
# ==============================================================================
# VOIDONYX & VOIDPANEL — 1-CLICK SERVER BACKUP SCRIPT
# ==============================================================================

set -e

BACKUP_DIR="/tmp/voidmail_backup_$(date +%Y%m%d_%H%M%S)"
OUTPUT_ARCHIVE="/root/voidmail_full_backup_$(date +%Y%m%d).tar.gz"

echo "📦 [1/4] Creating temporary backup workspace..."
mkdir -p "$BACKUP_DIR"

echo "💾 [2/4] Dumping database and mailbox schemas..."
if command -v pg_dump &> /dev/null; then
    pg_dump -U postgres voidmail > "$BACKUP_DIR/database_dump.sql" || echo "PostgreSQL dump skipped"
elif command -v mysqldump &> /dev/null; then
    mysqldump -u root -p voidmail > "$BACKUP_DIR/database_dump.sql" || echo "MySQL dump skipped"
fi

echo "📬 [3/4] Copying maildirs and server configuration..."
# Copy maildirs
if [ -d "/var/vmail" ]; then
    cp -r /var/vmail "$BACKUP_DIR/vmail"
fi

# Copy Postfix & Dovecot configs
mkdir -p "$BACKUP_DIR/configs"
if [ -d "/etc/postfix" ]; then
    cp -r /etc/postfix "$BACKUP_DIR/configs/postfix"
fi
if [ -d "/etc/dovecot" ]; then
    cp -r /etc/dovecot "$BACKUP_DIR/configs/dovecot"
fi

# Copy DKIM keys
if [ -d "/etc/opendkim" ]; then
    cp -r /etc/opendkim "$BACKUP_DIR/configs/opendkim"
fi

echo "🗜️ [4/4] Compressing into standalone archive: $OUTPUT_ARCHIVE..."
tar -czvf "$OUTPUT_ARCHIVE" -C "$BACKUP_DIR" .
rm -rf "$BACKUP_DIR"

echo "✅ SUCCESS! Backup archive created at: $OUTPUT_ARCHIVE"
echo "To migrate to a new server (Hetzner / Contabo / OVH), run:"
echo "scp $OUTPUT_ARCHIVE root@NEW_SERVER_IP:/root/"
echo "Then run ./restore.sh on the new server."
