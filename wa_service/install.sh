#!/usr/bin/env bash
# ============================================================
#  VoidPanel — WhatsApp Web Service Installer
#  ============================================================
#  This script:
#   1. Checks/installs Node.js >= 18
#   2. Installs npm dependencies for wa_service
#   3. Installs & enables the systemd service
#   4. Starts the service
#
#  Usage:
#    chmod +x wa_service/install.sh
#    sudo bash wa_service/install.sh
# ============================================================

set -e

PANEL_DIR="/var/www/panel"
WA_DIR="$PANEL_DIR/wa_service"
SERVICE_NAME="voidpanel-wa"
SERVICE_FILE="$WA_DIR/voidpanel-wa.service"
SYSTEMD_PATH="/etc/systemd/system/$SERVICE_NAME.service"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=== VoidPanel WhatsApp Web Service Installer ===${NC}"

# ── 1. Check root ─────────────────────────────────────────────────────────────
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}Error: This script must be run as root (sudo bash install.sh)${NC}"
   exit 1
fi

# ── 2. Check/Install Node.js >= 18 ────────────────────────────────────────────
echo -e "\n${YELLOW}[1/4] Checking Node.js installation...${NC}"

install_node() {
    echo "Installing Node.js 20 LTS via NodeSource..."
    if command -v apt-get &>/dev/null; then
        apt-get update -qq
        apt-get install -y -qq curl ca-certificates gnupg
        curl -fsSL https://deb.nodesource.com/setup_20.x | bash - 
        apt-get install -y -qq nodejs
    elif command -v dnf &>/dev/null; then
        curl -fsSL https://rpm.nodesource.com/setup_20.x | bash -
        dnf install -y nodejs
    elif command -v yum &>/dev/null; then
        curl -fsSL https://rpm.nodesource.com/setup_20.x | bash -
        yum install -y nodejs
    else
        echo -e "${RED}Error: Cannot detect package manager. Please install Node.js 20 manually.${NC}"
        exit 1
    fi
}

if command -v node &>/dev/null; then
    NODE_VER=$(node -e "console.log(parseInt(process.versions.node.split('.')[0]))")
    if [[ "$NODE_VER" -lt 18 ]]; then
        echo "Node.js $NODE_VER found — too old. Installing Node.js 20..."
        install_node
    else
        echo -e "${GREEN}✓ Node.js $(node --version) found.${NC}"
    fi
else
    echo "Node.js not found. Installing..."
    install_node
fi

echo -e "${GREEN}✓ Node.js $(node --version) ready.${NC}"

# ── 3. Install npm dependencies ───────────────────────────────────────────────
echo -e "\n${YELLOW}[2/4] Installing WhatsApp service npm dependencies...${NC}"

if [[ ! -d "$WA_DIR" ]]; then
    echo -e "${RED}Error: $WA_DIR not found. Is VoidPanel installed at $PANEL_DIR?${NC}"
    exit 1
fi

cd "$WA_DIR"
# Do NOT use --prefer-offline — npm cache is empty on fresh servers
npm install --omit=dev 2>&1 | tail -5
echo -e "${GREEN}✓ npm dependencies installed.${NC}"

# The service runs as root — chown accordingly
chown -R root:root "$WA_DIR"
chmod +x "$WA_DIR/server.js"

# Create auth_sessions dir (server.js will also create it, but doing it here ensures correct permissions)
mkdir -p "$WA_DIR/auth_sessions"
chown root:root "$WA_DIR/auth_sessions"
chmod 700 "$WA_DIR/auth_sessions"
echo -e "${GREEN}✓ Permissions set (running as root).${NC}"

# ── 5. Install & start systemd service ────────────────────────────────────────
echo -e "\n${YELLOW}[4/4] Installing systemd service...${NC}"

# Detect correct node binary — prefer /usr/local/bin (NodeSource) over /usr/bin (old distro)
NODE_BIN=""
for candidate in /usr/local/bin/node /usr/bin/node /usr/local/node/bin/node; do
    if [[ -x "$candidate" ]]; then
        VER=$("$candidate" -e "console.log(parseInt(process.versions.node.split('.')[0]))" 2>/dev/null)
        if [[ "$VER" -ge 18 ]]; then
            NODE_BIN="$candidate"
            break
        fi
    fi
done

if [[ -z "$NODE_BIN" ]]; then
    echo -e "${RED}Error: Could not find Node.js >= 18. Please install Node.js 20 and re-run.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Using Node.js at: $NODE_BIN ($(${NODE_BIN} --version))${NC}"

# Patch the service file with the correct node path and running as root
cat > "$SYSTEMD_PATH" <<EOF
[Unit]
Description=VoidPanel WhatsApp Web Microservice (Baileys)
Documentation=https://github.com/WhiskeySockets/Baileys
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$WA_DIR
ExecStart=$NODE_BIN $WA_DIR/server.js
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=voidpanel-wa
Environment=NODE_ENV=production
Environment=PATH=/usr/local/bin:/usr/bin:/bin
Environment=HOST=127.0.0.1
Environment=PORT=3001

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl restart "$SERVICE_NAME"

# Verify it started
sleep 3
if systemctl is-active --quiet "$SERVICE_NAME"; then
    echo -e "${GREEN}✓ $SERVICE_NAME service is running!${NC}"
else
    echo -e "${RED}Warning: Service may not have started. Check logs:${NC}"
    echo "  journalctl -u $SERVICE_NAME -n 20"
fi

echo ""
echo -e "${GREEN}=== Installation Complete ===${NC}"
echo -e "WhatsApp Web microservice is now running at ${YELLOW}http://127.0.0.1:3001${NC}"
echo ""
echo "Useful commands:"
echo "  systemctl status $SERVICE_NAME"
echo "  journalctl -u $SERVICE_NAME -f"
echo "  systemctl restart $SERVICE_NAME"
echo ""
