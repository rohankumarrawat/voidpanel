#!/bin/bash
# ============================================================
#  VoidPanel — General Fallback Update Script
#  https://voidpanel.com/updatepanel.sh
#  Used when no specific migration path is returned.
# ============================================================
set -euo pipefail

PANEL_DIR="/var/www/panel"
VERSION_FILE="/etc/version.txt"
LOG_FILE="/var/log/voidpanel/update-general.log"
MIGRATION_API="https://voidpanel.com/version_migration_path/"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"; }

mkdir -p "$(dirname "$LOG_FILE")"
log "=== VoidPanel General Updater started ==="

# Read current version
CURRENT_VER=$(cat "$VERSION_FILE" 2>/dev/null || echo "1.0")
log "Current version: $CURRENT_VER"

# Fetch migration path
log "Fetching migration path from $MIGRATION_API ..."
MIGRATION_JSON=$(curl -fsSL "${MIGRATION_API}?from=${CURRENT_VER}" 2>/dev/null || echo '{}')
STEPS=$(echo "$MIGRATION_JSON" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    steps = d.get('steps', [])
    for s in steps:
        print(s['version'] + '|' + s['script_url'])
except:
    pass
" 2>/dev/null)

if [ -z "$STEPS" ]; then
    log "No migration steps returned. Server is already up to date or API unreachable."
    exit 0
fi

# Execute each step in order
while IFS='|' read -r VER SCRIPT_URL; do
    log "--- Applying update step: v$VER ---"
    TMP_SCRIPT=$(mktemp /tmp/voidpanel_update_XXXXXX.sh)
    if curl -fsSL "$SCRIPT_URL" -o "$TMP_SCRIPT"; then
        chmod +x "$TMP_SCRIPT"
        bash "$TMP_SCRIPT"
        log "Step v$VER applied successfully."
    else
        log "ERROR: Failed to download $SCRIPT_URL — aborting update chain."
        rm -f "$TMP_SCRIPT"
        exit 1
    fi
    rm -f "$TMP_SCRIPT"
done <<< "$STEPS"

FINAL_VER=$(cat "$VERSION_FILE" 2>/dev/null || echo "$CURRENT_VER")
log "=== Update complete. Now running v$FINAL_VER ==="
