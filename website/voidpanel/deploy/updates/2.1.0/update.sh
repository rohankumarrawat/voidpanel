#!/bin/bash
# ============================================================
#  VoidPanel Update Script — v2.1.0
#  https://voidpanel.com/updates/2.1.0/update.sh
#  Requires: v2.0.0 installed first (min_version=2.0.0)
# ============================================================
set -euo pipefail

VERSION="2.1.0"
PANEL_DIR="/var/www/panel"
VERSION_FILE="/etc/version.txt"
RELEASE_URL="https://voidpanel.com/releases/voidpanel-${VERSION}.tar.gz"
BACKUP_DIR="/var/backups/voidpanel-pre-${VERSION}-$(date +%Y%m%d%H%M%S)"
LOG_FILE="/var/log/voidpanel/update-${VERSION}.log"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"; }
mkdir -p "$(dirname "$LOG_FILE")"
log "=== VoidPanel Update to v${VERSION} ==="

# Guard: ensure minimum version 2.0.0 is installed
CURRENT=$(cat "$VERSION_FILE" 2>/dev/null || echo "1.0")
if [[ "$CURRENT" < "2.0.0" ]]; then
    log "ERROR: v2.0.0 must be installed before upgrading to v2.1.0. Current: $CURRENT"
    exit 1
fi

log "Backing up to $BACKUP_DIR ..."
cp -r "$PANEL_DIR" "$BACKUP_DIR" 2>/dev/null || true

log "Downloading v${VERSION} ..."
TMP=$(mktemp -d)
curl -fsSL "$RELEASE_URL" -o "$TMP/release.tar.gz"
tar -xzf "$TMP/release.tar.gz" -C "$TMP"
EXTRACTED=$(find "$TMP" -mindepth 1 -maxdepth 1 -type d | head -1)

cp "$PANEL_DIR/panel/settings.py" "$TMP/settings.bak" 2>/dev/null || true
cp "$PANEL_DIR/.env"              "$TMP/env.bak"       2>/dev/null || true

log "Applying update files ..."
rsync -a --exclude='*.pyc' --exclude='__pycache__' \
      --exclude='db.sqlite3' --exclude='media/' --exclude='.env' \
      "$EXTRACTED/" "$PANEL_DIR/"

cp "$TMP/settings.bak" "$PANEL_DIR/panel/settings.py" 2>/dev/null || true
cp "$TMP/env.bak"      "$PANEL_DIR/.env"              2>/dev/null || true

log "Installing dependencies ..."
cd "$PANEL_DIR"
source venv/bin/activate 2>/dev/null || true
pip install -r requirements.txt -q
python manage.py migrate --noinput
python manage.py collectstatic --noinput

echo "$VERSION" > "$VERSION_FILE"
log "Version updated to $VERSION."

log "Restarting service ..."
systemctl restart voidpanel 2>/dev/null || \
  (pkill -f "gunicorn.*panel" 2>/dev/null; sleep 2; \
   cd "$PANEL_DIR" && source venv/bin/activate && \
   gunicorn panel.wsgi:application --bind 0.0.0.0:8080 --workers 3 --daemon)

rm -rf "$TMP"
log "=== v${VERSION} update complete! ==="
