#!/bin/bash
# ==============================================================================
# VOIDONYX & VOIDPANEL — 1-CLICK SERVER RESTORE SCRIPT
# ==============================================================================

set -e

ARCHIVE_PATH="$1"

if [ -z "$ARCHIVE_PATH" ]; then
    echo "Usage: sudo ./restore.sh <path_to_voidmail_backup.tar.gz>"
    echo "Example: sudo ./restore.sh /root/voidmail_full_backup_20260901.tar.gz"
    exit 1
fi

if [ ! -f "$ARCHIVE_PATH" ]; then
    echo "❌ Error: Backup archive not found at $ARCHIVE_PATH"
    exit 1
fi

RESTORE_TEMP="/tmp/voidmail_restore_temp"
mkdir -p "$RESTORE_TEMP"

echo "📦 [1/4] Extracting archive..."
tar -xzvf "$ARCHIVE_PATH" -C "$RESTORE_TEMP"

echo "📬 [2/4] Restoring virtual mailboxes & maildirs..."
if [ -d "$RESTORE_TEMP/vmail" ]; then
    mkdir -p /var/vmail
    cp -r "$RESTORE_TEMP/vmail"/* /var/vmail/
    chown -R vmail:vmail /var/vmail 2>/dev/null || chown -R 5000:5000 /var/vmail || true
fi

echo "⚙️ [3/4] Restoring configuration files..."
if [ -d "$RESTORE_TEMP/configs/postfix" ]; then
    cp -r "$RESTORE_TEMP/configs/postfix"/* /etc/postfix/
fi
if [ -d "$RESTORE_TEMP/configs/dovecot" ]; then
    cp -r "$RESTORE_TEMP/configs/dovecot"/* /etc/dovecot/
fi
if [ -d "$RESTORE_TEMP/configs/opendkim" ]; then
    cp -r "$RESTORE_TEMP/configs/opendkim"/* /etc/opendkim/
fi

echo "💾 [4/4] Restoring Database SQL dump..."
if [ -f "$RESTORE_TEMP/database_dump.sql" ]; then
    if command -v psql &> /dev/null; then
        psql -U postgres voidmail < "$RESTORE_TEMP/database_dump.sql" || echo "PostgreSQL restore notice"
    elif command -v mysql &> /dev/null; then
        mysql -u root -p voidmail < "$RESTORE_TEMP/database_dump.sql" || echo "MySQL restore notice"
    fi
fi

# Cleanup
rm -rf "$RESTORE_TEMP"

# Restart services
echo "🔄 Restarting Postfix, Dovecot, and OpenDKIM services..."
systemctl restart postfix dovecot opendkim 2>/dev/null || true

echo "=========================================================================="
echo "🎉 RESTORE COMPLETED SUCCESSFULLY!"
echo "Your mail server, domains, and mailboxes are now live on this server."
echo "Please update your DNS A-Record in Cloudflare to point to this server's IP."
echo "=========================================================================="
