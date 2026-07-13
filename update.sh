#!/bin/bash
# VoidPanel — live update script
# Usage: bash update.sh (run as root on the panel server)
set -euo pipefail
GREEN='\033[0;32m'; CYAN='\033[0;36m'; RED='\033[0;31m'; RESET='\033[0m'
info()  { echo -e "${CYAN}[+] $1${RESET}"; }
ok()    { echo -e "${GREEN}[✔] $1${RESET}"; }
err()   { echo -e "${RED}[!] $1${RESET}"; exit 1; }

PROJECT_DIR="/var/www/panel"
VENV="$PROJECT_DIR/venv"

info "Fetching latest version info from voidpanel.com"
LATEST=$(curl -fsSL --max-time 10 https://voidpanel.com/version.txt 2>/dev/null | tr -d '[:space:]') || LATEST=""
if [[ -z "$LATEST" ]]; then
    err "Could not fetch version from voidpanel.com — check your internet connection."
fi

CURRENT=$(cat /var/www/panel/version.txt 2>/dev/null | tr -d '[:space:]') || CURRENT="0"
if [[ "$CURRENT" == "$LATEST" ]]; then
    ok "Already on the latest version ($CURRENT). Nothing to do."
    exit 0
fi

info "Downloading VoidPanel $LATEST"
cd /tmp
curl -fsSL --max-time 300 "https://voidpanel.com/releases/voidpanel-${LATEST}.tar.gz" -o voidpanel-update.tar.gz \
    || curl -fsSL --max-time 300 "https://voidpanel.com/static/voidpanel.zip" -o voidpanel-update.zip

if [[ -f /tmp/voidpanel-update.tar.gz ]]; then
    info "Extracting tarball"
    mkdir -p /tmp/voidpanel-src
    tar -xzf voidpanel-update.tar.gz -C /tmp/voidpanel-src --strip-components=1
    rm -f voidpanel-update.tar.gz
elif [[ -f /tmp/voidpanel-update.zip ]]; then
    info "Extracting zip"
    mkdir -p /tmp/voidpanel-src
    unzip -o voidpanel-update.zip -d /tmp/voidpanel-src > /dev/null
    rm -f voidpanel-update.zip
else
    err "Download failed — no update package found."
fi

info "Syncing files (preserving .env, venv, staticfiles)"
rsync -a --exclude='venv/' --exclude='.env' --exclude='staticfiles/' \
    --exclude='*.log' --exclude='*.sock' --exclude='__pycache__/' \
    /tmp/voidpanel-src/ "$PROJECT_DIR/"
rm -rf /tmp/voidpanel-src

info "Installing/updating Python dependencies"
source "$VENV/bin/activate"
pip install --quiet --upgrade pip
[[ -f "$PROJECT_DIR/requirements.txt" ]] && pip install --quiet -r "$PROJECT_DIR/requirements.txt" || true

info "Running database migrations"
cd "$PROJECT_DIR"
python manage.py makemigrations --no-input 2>/dev/null || true
python manage.py migrate --noinput
python manage.py collectstatic --noinput --clear 2>/dev/null || true

info "Restarting services"
systemctl restart voidpanel voidpanel-daphne voidpanel-celery voidpanel-celery-beat voidpanel-wa 2>/dev/null || true

info "Re-applying phpMyAdmin SSO configuration"
# Redeploy vp_sso.php with session_write_close fix
if [[ -d /usr/share/phpmyadmin ]]; then
    cat > /usr/share/phpmyadmin/vp_sso.php << 'VPSSOPHP'
<?php
/**
 * VoidPanel phpMyAdmin Single Sign-On gateway
 */
session_name('phpMyAdmin');
$port = (int)$_SERVER['SERVER_PORT'];
$secure = ($port === 8092);
ini_set('session.cookie_samesite', 'None');
if ($secure) { ini_set('session.cookie_secure', '1'); }
ini_set('session.cookie_httponly', '0');
session_start();
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(200);
    echo '<!DOCTYPE html><html><head><title>VoidPanel Database Access</title>';
    echo '<meta http-equiv="refresh" content="0;url=index.php">';
    echo '</head><body><p>Redirecting to phpMyAdmin...</p></body></html>';
    exit;
}
$user     = isset($_POST['temp_user'])     ? trim($_POST['temp_user'])     : '';
$password = isset($_POST['temp_password']) ? trim($_POST['temp_password']) : '';
if (empty($user) || empty($password)) { http_response_code(400); die('Missing credentials.'); }
if (!preg_match('/^vp_temp_[a-z0-9]+$/', $user)) { http_response_code(403); die('Forbidden.'); }
$_SESSION['PMA_single_signon_user']     = $user;
$_SESSION['PMA_single_signon_password'] = $password;
$_SESSION['PMA_single_signon_host']     = 'localhost';
$_SESSION['PMA_single_signon_port']     = '3306';
session_write_close();
header('Location: index.php');
exit;
VPSSOPHP
    WEB_USER="www-data"
    if ! id -u www-data &>/dev/null && id -u nginx &>/dev/null; then WEB_USER="nginx"; fi
    chown "$WEB_USER:$WEB_USER" /usr/share/phpmyadmin/vp_sso.php
    chmod 644 /usr/share/phpmyadmin/vp_sso.php
    # Re-apply SSO config in phpMyAdmin config
    for PMA_CONF in "/etc/phpmyadmin/config.inc.php" "/usr/share/phpmyadmin/config.inc.php"; do
        if [[ -f "$PMA_CONF" ]]; then
            sed -i '/PMA_single_signon\|auth_type.*signon\|SignonSession\|SignonURL\|LogoutURL\|VoidPanel SSO/d' "$PMA_CONF" 2>/dev/null || true
            printf "\n/* VoidPanel SSO */\n\$cfg['Servers'][1]['auth_type']='signon';\n\$cfg['Servers'][1]['SignonSession']='phpMyAdmin';\n\$cfg['Servers'][1]['SignonURL']='/vp_sso.php';\n\$cfg['Servers'][1]['LogoutURL']='/vp_sso.php';\n" >> "$PMA_CONF"
        fi
    done
fi

info "Patching phpMyAdmin nginx config (upload limits + timeout)"
# Detect which nginx config file phpMyAdmin uses (Ubuntu vs AlmaLinux)
PMA_NGINX_CONF=""
for f in /etc/nginx/sites-available/phpmyadmin /etc/nginx/conf.d/phpmyadmin.conf; do
    [[ -f "$f" ]] && PMA_NGINX_CONF="$f" && break
done

if [[ -n "$PMA_NGINX_CONF" ]]; then
    # Add client_max_body_size 256M if not already present
    if ! grep -q "client_max_body_size 256M" "$PMA_NGINX_CONF"; then
        # Insert after each 'listen 809' line
        sed -i '/listen 809/a\    client_max_body_size 256M;' "$PMA_NGINX_CONF"
        ok "Added client_max_body_size 256M to $PMA_NGINX_CONF"
    fi
    # Add fastcgi read/send timeouts inside PHP location blocks if missing
    if ! grep -q "fastcgi_read_timeout 600" "$PMA_NGINX_CONF"; then
        sed -i '/fastcgi_pass unix/a\        fastcgi_read_timeout 600;\n        fastcgi_send_timeout 600;' "$PMA_NGINX_CONF"
        ok "Added fastcgi timeouts (600s) to $PMA_NGINX_CONF"
    fi
    # Reload nginx to apply changes
    nginx -t 2>/dev/null && systemctl reload nginx 2>/dev/null || true
else
    warn "phpMyAdmin nginx config not found — skipping nginx patch"
fi

info "Tuning PHP-FPM limits for phpMyAdmin imports"
# Ubuntu: /etc/php/X.Y/fpm/php.ini
for PHP_FPM_INI in /etc/php/*/fpm/php.ini; do
    [[ -f "$PHP_FPM_INI" ]] || continue
    sed -i 's/^upload_max_filesize = .*/upload_max_filesize = 256M/'  "$PHP_FPM_INI"
    sed -i 's/^post_max_size = .*/post_max_size = 256M/'              "$PHP_FPM_INI"
    sed -i 's/^max_execution_time = .*/max_execution_time = 600/'     "$PHP_FPM_INI"
    sed -i 's/^max_input_time = .*/max_input_time = 600/'             "$PHP_FPM_INI"
    CURRENT_MEM=$(grep '^memory_limit' "$PHP_FPM_INI" | grep -oP '\d+' | head -1)
    if [[ -z "$CURRENT_MEM" || "$CURRENT_MEM" -lt 512 ]]; then
        sed -i 's/^memory_limit = .*/memory_limit = 512M/' "$PHP_FPM_INI"
    fi
    ok "PHP-FPM ini tuned at $PHP_FPM_INI"
done
# AlmaLinux/RHEL: /etc/php.ini or /etc/php-fpm.d/www.conf
for PHP_FPM_INI in /etc/php.ini /etc/php/php.ini; do
    [[ -f "$PHP_FPM_INI" ]] || continue
    sed -i 's/^upload_max_filesize = .*/upload_max_filesize = 256M/'  "$PHP_FPM_INI"
    sed -i 's/^post_max_size = .*/post_max_size = 256M/'              "$PHP_FPM_INI"
    sed -i 's/^max_execution_time = .*/max_execution_time = 600/'     "$PHP_FPM_INI"
    sed -i 's/^max_input_time = .*/max_input_time = 600/'             "$PHP_FPM_INI"
    CURRENT_MEM=$(grep '^memory_limit' "$PHP_FPM_INI" | grep -oP '\d+' | head -1)
    if [[ -z "$CURRENT_MEM" || "$CURRENT_MEM" -lt 512 ]]; then
        sed -i 's/^memory_limit = .*/memory_limit = 512M/' "$PHP_FPM_INI"
    fi
    ok "PHP ini tuned at $PHP_FPM_INI"
done
# Reload PHP-FPM
for svc in php-fpm php8.1-fpm php8.2-fpm php8.3-fpm php8.0-fpm php7.4-fpm; do
    systemctl is-active --quiet "$svc" 2>/dev/null && systemctl reload "$svc" 2>/dev/null && break
done

ok "VoidPanel updated to $LATEST successfully!"
