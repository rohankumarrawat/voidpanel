#!/bin/bash
# =============================================================================
#  VoidPanel — phpMyAdmin SSO Fix Script
#  Run this on your server as root to fix phpMyAdmin auto-login
#  Usage: bash fix_pma.sh
# =============================================================================
set -uo pipefail

GREEN='\033[0;32m'; CYAN='\033[0;36m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; RESET='\033[0m'
ok()   { echo -e "${GREEN}[✔] $1${RESET}"; }
info() { echo -e "${CYAN}[+] $1${RESET}"; }
warn() { echo -e "${YELLOW}[!] $1${RESET}"; }
err()  { echo -e "${RED}[✘] $1${RESET}"; exit 1; }

[[ $EUID -ne 0 ]] && err "This script must be run as root."

echo ""
echo "  VoidPanel — phpMyAdmin SSO Fix"
echo "  ================================"
echo ""

# Check phpMyAdmin is installed
if [[ ! -d /usr/share/phpmyadmin ]]; then
    err "phpMyAdmin not found at /usr/share/phpmyadmin — is it installed?"
fi

# Step 1: Deploy fixed vp_sso.php
info "Deploying fixed vp_sso.php (with session_write_close)"
cat > /usr/share/phpmyadmin/vp_sso.php << 'VPSSOPHP'
<?php
/**
 * VoidPanel phpMyAdmin Single Sign-On gateway
 * Version: 2.5.4+
 */
session_name('phpMyAdmin');

// Set proper session cookie flags for cross-port access
$port = (int)$_SERVER['SERVER_PORT'];
$secure = ($port === 8092);
ini_set('session.cookie_samesite', 'None');
if ($secure) { ini_set('session.cookie_secure', '1'); }
ini_set('session.cookie_httponly', '0');

session_start();

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    // Handle GET requests (e.g., phpMyAdmin redirecting here for re-auth)
    http_response_code(200);
    echo '<!DOCTYPE html><html><head><title>VoidPanel Database Access</title>';
    echo '<meta http-equiv="refresh" content="0;url=index.php">';
    echo '</head><body><p>Redirecting to phpMyAdmin login...</p>';
    echo '<script>window.location.href="index.php";</script></body></html>';
    exit;
}

$user     = isset($_POST['temp_user'])     ? trim($_POST['temp_user'])     : '';
$password = isset($_POST['temp_password']) ? trim($_POST['temp_password']) : '';

if (empty($user) || empty($password)) {
    http_response_code(400);
    die('<h3 style="font-family:sans-serif;color:#ef4444;padding:40px;">&#9888; Missing credentials. Use VoidPanel dashboard to open phpMyAdmin.</h3>');
}

if (!preg_match('/^vp_temp_[a-z0-9]+$/', $user)) {
    http_response_code(403);
    die('<h3 style="font-family:sans-serif;color:#ef4444;padding:40px;">&#128274; Access denied.</h3>');
}

$_SESSION['PMA_single_signon_user']     = $user;
$_SESSION['PMA_single_signon_password'] = $password;
$_SESSION['PMA_single_signon_host']     = 'localhost';
$_SESSION['PMA_single_signon_port']     = '3306';

// CRITICAL: flush session to disk before redirect
session_write_close();

header('Location: index.php');
exit;
VPSSOPHP

WEB_USER="www-data"
if ! id -u www-data &>/dev/null && id -u nginx &>/dev/null; then WEB_USER="nginx"; fi
chown "$WEB_USER:$WEB_USER" /usr/share/phpmyadmin/vp_sso.php
chmod 644 /usr/share/phpmyadmin/vp_sso.php
ok "vp_sso.php deployed"

# Step 2: Apply SSO configuration to phpMyAdmin config files
info "Configuring phpMyAdmin SSO auth_type"
PMA_CONF_PATCHED=0

for PMA_CONF in "/etc/phpmyadmin/config.inc.php" "/usr/share/phpmyadmin/config.inc.php"; do
    if [[ -f "$PMA_CONF" ]]; then
        info "Patching $PMA_CONF"
        # Remove any old/duplicate SSO lines
        sed -i '/PMA_single_signon\|auth_type.*signon\|SignonSession\|SignonURL\|LogoutURL\|VoidPanel SSO/d' \
            "$PMA_CONF" 2>/dev/null || true
        # Also remove cookie auth lines that override signon
        sed -i "/auth_type.*=.*'cookie'/d" "$PMA_CONF" 2>/dev/null || true
        # Append fresh SSO config
        printf "\n/* VoidPanel SSO - applied by fix_pma.sh */\n" >> "$PMA_CONF"
        printf "\$cfg['Servers'][1]['auth_type']     = 'signon';\n" >> "$PMA_CONF"
        printf "\$cfg['Servers'][1]['SignonSession'] = 'phpMyAdmin';\n" >> "$PMA_CONF"
        printf "\$cfg['Servers'][1]['SignonURL']     = '/vp_sso.php';\n" >> "$PMA_CONF"
        printf "\$cfg['Servers'][1]['LogoutURL']     = '/vp_sso.php';\n" >> "$PMA_CONF"
        ok "Patched: $PMA_CONF"
        PMA_CONF_PATCHED=1
    fi
done

if [[ $PMA_CONF_PATCHED -eq 0 ]]; then
    warn "No phpMyAdmin config.inc.php found at /etc/phpmyadmin/ or /usr/share/phpmyadmin/"
fi

# Step 3: Test if phpMyAdmin is reachable on port 8090
info "Testing phpMyAdmin connectivity on port 8090"
if curl -s --connect-timeout 3 http://127.0.0.1:8090/ -o /dev/null; then
    ok "phpMyAdmin is reachable on port 8090"
else
    warn "phpMyAdmin port 8090 not responding — check nginx and php-fpm"
    warn "Run: systemctl status nginx php*-fpm"
fi

# Step 4: Test vp_sso.php GET response
info "Testing vp_sso.php GET response"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8090/vp_sso.php 2>/dev/null || echo "000")
if [[ "$HTTP_CODE" == "200" ]]; then
    ok "vp_sso.php responds correctly to GET (200)"
elif [[ "$HTTP_CODE" == "000" ]]; then
    warn "Could not reach vp_sso.php — check nginx is running"
else
    warn "vp_sso.php returned HTTP $HTTP_CODE on GET (expected 200)"
fi

# Step 5: Verify session_write_close is in the file
if grep -q "session_write_close" /usr/share/phpmyadmin/vp_sso.php; then
    ok "session_write_close() is present in vp_sso.php"
else
    err "session_write_close() missing from vp_sso.php — deployment failed!"
fi

# Step 6: Restart nginx and php-fpm to pick up config changes
info "Restarting nginx and PHP-FPM"
PHP_VER=$(php --version 2>/dev/null | grep -oP '^\S+\s+\K\d+\.\d+' | head -1 || echo "8.1")
systemctl reload nginx 2>/dev/null || systemctl restart nginx 2>/dev/null || warn "Could not reload nginx"
systemctl restart "php${PHP_VER}-fpm" 2>/dev/null || \
    systemctl restart php-fpm 2>/dev/null || \
    warn "Could not restart php-fpm — restart manually"

# Step 7: Restart VoidPanel
info "Restarting VoidPanel"
systemctl restart voidpanel voidpanel-daphne 2>/dev/null || true

echo ""
echo -e "${GREEN}══════════════════════════════════════════${RESET}"
echo -e "${GREEN}  phpMyAdmin SSO Fix complete!            ${RESET}"
echo -e "${GREEN}══════════════════════════════════════════${RESET}"
echo ""
echo -e "  ${CYAN}Test it:${RESET} Log into VoidPanel → Database Manager → phpMyAdmin"
echo -e "  ${CYAN}Logs:${RESET}   tail -f /tmp/sso_debug.log"
echo -e "  ${CYAN}Nginx:${RESET}  tail -f /var/log/nginx/error.log"
echo ""
