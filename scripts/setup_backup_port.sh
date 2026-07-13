#!/usr/bin/env bash
# =============================================================================
#  VoidPanel — Setup Always-On Backup Web Server (Port 8081)
#  Run this as root on the existing Linux server to configure a secondary
#  public port for administrative recovery.
# =============================================================================
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; YELLOW='\033[1;33m'; RESET='\033[0m'
ok()   { echo -e "${GREEN}[✔] $1${RESET}"; }
info() { echo -e "${CYAN}[+] $1${RESET}"; }
warn() { echo -e "${YELLOW}[!] $1${RESET}"; }
err()  { echo -e "${RED}[✘] $1${RESET}"; }

if [ "$EUID" -ne 0 ]; then
   err "Please run this script as root (sudo bash setup_backup_port.sh)"
   exit 1
fi

PROJECT_DIR="/var/www/panel"

if [ ! -d "$PROJECT_DIR" ]; then
    err "VoidPanel installation directory not found at $PROJECT_DIR."
    exit 1
fi

info "Creating systemd unit: voidpanel-backup.service (Port 8081)"

cat > /etc/systemd/system/voidpanel-backup.service << 'EOF'
[Unit]
Description=VoidPanel Backup Dashboard (Always-On Port 8081)
After=network.target redis-server.service mysql.service
Wants=redis-server.service mysql.service

[Service]
Type=simple
User=root
WorkingDirectory=/var/www/panel
EnvironmentFile=/var/www/panel/.env
Environment=PYTHONPATH=/var/www/panel
Environment=DJANGO_SETTINGS_MODULE=panel.settings
ExecStart=/var/www/panel/venv/bin/daphne -b 0.0.0.0 -p 8081 panel.asgi:application
Restart=always
RestartSec=5s

[Install]
WantedBy=multi-user.target
EOF

info "Reloading systemd and enabling service..."
systemctl daemon-reload
systemctl enable voidpanel-backup
systemctl restart voidpanel-backup

# Wait and check status
sleep 2
if systemctl is-active --quiet voidpanel-backup; then
    ok "Backup service is running on port 8081!"
else
    err "Backup service failed to start. Check logs: journalctl -u voidpanel-backup -n 30"
    exit 1
fi

# Configure Firewall
if command -v ufw >/dev/null 2>&1; then
    info "Configuring UFW firewall to allow port 8081..."
    ufw allow 8081/tcp >/dev/null || true
    ok "Port 8081 opened in UFW firewall"
elif command -v firewall-cmd >/dev/null 2>&1; then
    info "Configuring firewalld to allow port 8081..."
    firewall-cmd --permanent --add-port=8081/tcp >/dev/null || true
    firewall-cmd --reload >/dev/null || true
    ok "Port 8081 opened in firewalld"
else
    warn "No standard firewall (UFW/firewalld) found. Ensure port 8081/tcp is open in your network settings."
fi

# Get Public IP
IP=$(curl -s https://api.ipify.org || echo "<your-server-ip>")

echo ""
echo -e "${GREEN}=========================================================="
echo "  Setup Complete! VoidPanel Backup Web Server is Live."
echo -e "==========================================================${RESET}"
echo "  You can now access your control panel at:"
echo -e "  ${CYAN}http://${IP}:8081/${RESET}"
echo ""
echo "  Note: This port bypasses Nginx completely."
echo "        It will remain accessible even if Nginx is down."
echo -e "${GREEN}==========================================================${RESET}"
echo ""
