#!/bin/bash
# ============================================================
#  VoidPanel — Upload & Release Script (NO GIT REQUIRED)
#  Run this on YOUR MAC after editing any file.
#
#  Usage:
#    bash upload_and_release.sh 2.2.0 "Fixed update endpoint"
#    bash upload_and_release.sh 2.2.0
# ============================================================
set -euo pipefail

VERSION="${1:-}"
NOTES="${2:-VoidPanel v$VERSION update}"

# ── CONFIG — edit these to match your server ───────────────
SERVER_USER="root"
SERVER_HOST="voidpanel.com"          # or use IP: 178.18.250.134
SERVER_PATH="/home/voidpanelc091/voidpanel"
LOCAL_PANEL="/Users/rohan/Desktop/voidpanel"
SSH_KEY=""  # optional: e.g. ~/.ssh/id_rsa  (leave blank to use password)
# ───────────────────────────────────────────────────────────

if [ -z "$VERSION" ]; then
    echo "❌ Usage: bash upload_and_release.sh <VERSION> [\"Notes\"]"
    echo "   Example: bash upload_and_release.sh 2.3.0 \"Fixed reseller login\""
    exit 1
fi

echo "📦 Step 0: Updating local installer scripts and packaging Archive.zip..."
cp "$LOCAL_PANEL/ubuntu.sh"     "$LOCAL_PANEL/website/voidpanel/static/ubuntu.sh"
cp "$LOCAL_PANEL/almalinux.sh"  "$LOCAL_PANEL/website/voidpanel/static/almalinux.sh"
cp "$LOCAL_PANEL/install.sh"    "$LOCAL_PANEL/website/voidpanel/static/install.sh"

rm -f "$LOCAL_PANEL/Archive.zip"
(cd "$LOCAL_PANEL" && zip -r Archive.zip . -x "*.git*" -x "*venv*" -x "website/*" -x "*.env" -x "*.sqlite3" -x "media/*" -x "*.DS_Store" -x "*__pycache__*" -x "Archive.zip" -x ".gemini/*")

# ── Critical: copy to BOTH locations ──────────────────────────────────────────
# Archive.zip  → website root (used by deploy.sh to build release tarball)
# voidpanel.zip → website/static/ (served to fresh installs via collectstatic)
cp "$LOCAL_PANEL/Archive.zip" "$LOCAL_PANEL/website/voidpanel/Archive.zip"
cp "$LOCAL_PANEL/Archive.zip" "$LOCAL_PANEL/website/voidpanel/static/voidpanel.zip"

echo "   ✅ Packaging completed (Archive.zip + static/voidpanel.zip updated)"



SSH_OPTS="-o StrictHostKeyChecking=no"
[ -n "$SSH_KEY" ] && SSH_OPTS="$SSH_OPTS -i $SSH_KEY"

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  VoidPanel Upload & Release — v$VERSION"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# ── Step 1: Upload changed files from Mac → voidpanel.com ──
echo "📤 Uploading code to $SERVER_HOST ..."
rsync -avz --progress \
    --exclude='*.pyc' \
    --exclude='__pycache__/' \
    --exclude='.git/' \
    --exclude='*.sqlite3' \
    --exclude='media/' \
    --exclude='.env' \
    --exclude='venv/' \
    --exclude='.venv/' \
    --exclude='node_modules/' \
    -e "ssh $SSH_OPTS" \
    "$LOCAL_PANEL/website/voidpanel/" "$SERVER_USER@$SERVER_HOST:$SERVER_PATH/"

echo "   ✅ Files uploaded"

# ── Step 2: Run deploy.sh on the server ────────────────────
echo ""
echo "🚀 Running deploy.sh on server for v$VERSION ..."
ssh $SSH_OPTS "$SERVER_USER@$SERVER_HOST" \
    "bash $SERVER_PATH/deploy/deploy.sh \"$VERSION\" \"$NOTES\""

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  ✅ v$VERSION live on voidpanel.com!"
echo "║  All servers can now update from the panel."
echo "╚══════════════════════════════════════════════════════╝"
echo ""
