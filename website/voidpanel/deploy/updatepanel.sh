#!/bin/bash
# ============================================================
#  VoidPanel — General Updater (public_html entry point)
#  Served at: https://voidpanel.com/updatepanel.sh
#  This script is called directly by client panel servers.
#  It queries the migration path API and runs each step.
# ============================================================
set -euo pipefail

PANEL_DIR="/var/www/panel"
VERSION_FILE="/etc/version.txt"
LOG_FILE="/var/log/voidpanel/update-general.log"
MIGRATION_API="https://voidpanel.com/version_migration_path/"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"; }
mkdir -p "$(dirname "$LOG_FILE")"

log "=== VoidPanel General Updater started ==="
CURRENT_VER=$(cat "$VERSION_FILE" 2>/dev/null || echo "1.0")
log "Current installed version: $CURRENT_VER"

log "Querying migration path from $MIGRATION_API ..."
MIGRATION_JSON=$(curl -fsSL "${MIGRATION_API}?from=${CURRENT_VER}" 2>/dev/null || echo '{}')

STEPS=$(echo "$MIGRATION_JSON" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    for s in d.get('steps', []):
        print(s['version'] + '|' + s['script_url'])
except: pass
" 2>/dev/null)

if [ -z "$STEPS" ]; then
    log "Already up to date or migration API unreachable."
    exit 0
fi

while IFS='|' read -r VER SCRIPT_URL; do
    log "--- Applying step: v$VER ---"
    TMP=$(mktemp /tmp/vp_update_XXXXXX.sh)
    if curl -fsSL "$SCRIPT_URL" -o "$TMP"; then
        chmod +x "$TMP"
        bash "$TMP" && log "✅ v$VER applied." || { log "❌ v$VER failed."; rm -f "$TMP"; exit 1; }
    else
        log "❌ Could not download $SCRIPT_URL"; rm -f "$TMP"; exit 1
    fi
    rm -f "$TMP"
done <<< "$STEPS"

FINAL=$(cat "$VERSION_FILE" 2>/dev/null || echo "$CURRENT_VER")
log "=== Update complete. Now on v$FINAL ==="
