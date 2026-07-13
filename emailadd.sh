#!/bin/bash
USAGE="Usage: $0 EMAIL PASSWORD [SYS_USER]";

if [ ! -n "$2" ]
then
	echo $USAGE;
	exit 1;
fi

ADDRESS=$1;
USERNAME=$(echo "$1" | cut -f1 -d@);
DOMAIN=$(echo "$1" | cut -f2 -d@);
PASSWD=$2;
SYS_USER=${3:-vmail}

# Always store mail under the user's home directory
if [ "$SYS_USER" != "vmail" ] && [ -d "/home/$SYS_USER" ]; then
    BASEDIR="/home/$SYS_USER/mail/$DOMAIN/$USERNAME"
    FILEDIR="/home/$SYS_USER/mail"
    # Ensure home directory has execute permission for others so vmail can traverse it
    chmod o+x "/home/$SYS_USER" 2>/dev/null || true
else
    BASEDIR="/home/$SYS_USER/mail/$DOMAIN/$USERNAME"
    FILEDIR="/home/$SYS_USER/mail"
fi

echo "Creating Mailbox at $BASEDIR..."
mkdir -p "$BASEDIR/Maildir/cur" "$BASEDIR/Maildir/new" "$BASEDIR/Maildir/tmp"
chown -R vmail:vmail "$FILEDIR"
chmod -R 775 "$FILEDIR"
chmod -R 700 "$BASEDIR"

# Global Dovecot user registry
TOUCH_FILE="/etc/dovecot/users"
if [ ! -f "$TOUCH_FILE" ]; then
    touch "$TOUCH_FILE"
    chown vmail:dovecot "$TOUCH_FILE"
    chmod 640 "$TOUCH_FILE"
fi

# Insert routing mapping into Dovecot's global users file
sed -i "/^${ADDRESS}:/d" "$TOUCH_FILE"
HASH=$(doveadm pw -s SHA512-CRYPT -p "$PASSWD")
# Format: address:password:uid:gid::home
echo "${ADDRESS}:${HASH}:5000:5000::${BASEDIR}" >> "$TOUCH_FILE"

systemctl reload postfix || true
systemctl reload dovecot || true
