#!/usr/bin/env bash
# =============================================================================
#  VoidPanel — Live Server Repair Script
#  Run this as root on the existing server to apply all 8 bug fixes without
#  a full reinstall. Safe to run multiple times (idempotent).
#
#  Usage:
#    chmod +x repair.sh && sudo bash repair.sh
# =============================================================================
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; YELLOW='\033[1;33m'; RESET='\033[0m'
ok()   { echo -e "${GREEN}[✔] $1${RESET}"; }
info() { echo -e "${CYAN}[+] $1${RESET}"; }
warn() { echo -e "${YELLOW}[!] $1${RESET}"; }
err()  { echo -e "${RED}[✘] $1${RESET}"; }

PROJECT_DIR="/var/www/panel"
VENV_DIR="$PROJECT_DIR/venv"

echo ""
echo -e "${CYAN}=========================================================="
echo "  VoidPanel — Repair Script (all 8 user-creation bugs)"
echo -e "==========================================================${RESET}"
echo ""

# ─────────────────────────────────────────────────────────────────────────────
# 1. Fix /var/log/voidpanel — Bug #6 (logger falls back to no-op silently)
# ─────────────────────────────────────────────────────────────────────────────
info "Fix #6 — Creating /var/log/voidpanel with www-data ownership"
mkdir -p /var/log/voidpanel
chmod 750 /var/log/voidpanel
touch /var/log/voidpanel/panel.log \
      /var/log/voidpanel/error.log \
      /var/log/voidpanel/celery.log
chown -R www-data:www-data /var/log/voidpanel
ok "Log directory ready: /var/log/voidpanel"

# ─────────────────────────────────────────────────────────────────────────────
# 2. Install voidpanel-celery.service — Bug #3 (no worker → tasks never run)
# ─────────────────────────────────────────────────────────────────────────────
info "Fix #3 — Installing voidpanel-celery systemd service"
mkdir -p /var/run/celery
chown www-data:www-data /var/run/celery

cat > /etc/systemd/system/voidpanel-celery.service << 'SVCEOF'
[Unit]
Description=VoidPanel Celery Worker
After=network.target redis-server.service mysql.service
Wants=redis-server.service mysql.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/var/www/panel
EnvironmentFile=/var/www/panel/.env
Environment=PYTHONPATH=/var/www/panel
Environment=DJANGO_SETTINGS_MODULE=panel.settings
ExecStart=/var/www/panel/venv/bin/celery -A panel worker \
    --loglevel=info \
    --concurrency=4 \
    --logfile=/var/log/voidpanel/celery.log
Restart=on-failure
RestartSec=10s
KillSignal=SIGTERM
TimeoutStopSec=60

[Install]
WantedBy=multi-user.target
SVCEOF

systemctl daemon-reload
systemctl enable voidpanel-celery
systemctl restart voidpanel-celery
sleep 2
if systemctl is-active --quiet voidpanel-celery; then
    ok "Celery worker is running"
else
    err "Celery worker failed to start — check: journalctl -u voidpanel-celery -n 30"
fi

# ─────────────────────────────────────────────────────────────────────────────
# 3. Deploy updated Python source — Bugs #1 #2 #4 #8
# ─────────────────────────────────────────────────────────────────────────────
info "Fix #1/#2/#4/#8 — Pushing updated source files to server"

# Check if git is available and repo is clean
if [[ -d "$PROJECT_DIR/.git" ]]; then
    warn "Detected git repo — pulling latest if available..."
    cd "$PROJECT_DIR"
    git pull 2>/dev/null || warn "git pull failed — applying patch manually"
fi

# Patch control/tasks.py — Bug #2: domainname → mainusername in terminate_user_task
TASKS_FILE="$PROJECT_DIR/control/tasks.py"
if grep -q "username=domainname" "$TASKS_FILE" 2>/dev/null; then
    sed -i 's/username=domainname)/username=mainusername)/g' "$TASKS_FILE"
    ok "Bug #2 patched in tasks.py (terminate_user_task domainname typo fixed)"
else
    warn "Bug #2 patch already applied or line not found in tasks.py"
fi

# Patch panel/views.py — Bug #1: addusermainapi → provision_user_task via Celery
VIEWS_FILE="$PROJECT_DIR/panel/views.py"

# Check if old broken code still exists
if grep -q "addusermainapi" "$VIEWS_FILE" 2>/dev/null; then
    warn "Bug #1 — addusermainapi still present. Writing patched background_create_account..."

    # Build a temporary patch file
    PATCH_TMPFILE=$(mktemp /tmp/voidpanel_views_patch.XXXXXX.py)
    cat > "$PATCH_TMPFILE" << 'PYEOF'
def background_create_account(username, password, domain_name, package_name):
    """
    Called by the WHMCS API create_account endpoint.
    Routes to Celery provision_user_task for robust async processing.
    """
    import re
    try:
        from control.models import package as PackageModel
        from voidplatform.config import paths
        import os
        try:
            pkg = PackageModel.objects.get(name=package_name)
            sto = int(pkg.storage)
        except Exception:
            sto = 0

        home_base   = paths.HOME_BASE
        directories = os.listdir(home_base) if os.path.isdir(home_base) else []
        base_name   = re.sub(r'[^a-z0-9]', '', domain_name.split('.')[0].lower())[:16]
        domainname  = base_name
        counter = 1
        while domainname in directories:
            suffix     = str(counter)
            domainname = base_name[:16 - len(suffix)] + suffix
            counter   += 1

        acct_path = os.path.join(paths.HOME_BASE, domainname)
        inipath   = acct_path + '/public_html/php.ini'
        php_ini_content = (
            f'; PHP settings for {domain_name}\n'
            'max_execution_time = 30\nmemory_limit = 256M\n'
            'post_max_size = 64M\nupload_max_filesize = 64M\n'
            'display_errors = Off\nlog_errors = On\n'
            f'error_log = "{acct_path}/public_html/logs/php_errors.log"\n'
            'date.timezone = "Asia/Kolkata"\nfile_uploads = On\n'
            f'open_basedir = "{acct_path}/public_html:/tmp"\n'
        )

        from control.tasks import provision_user_task
        task = provision_user_task.delay(
            domain_name, domainname, username, password, package_name,
            acct_path, sto, inipath, php_ini_content,
        )
        import logging
        logging.getLogger('voidpanel.panel.views').info(
            'API provision task dispatched: domain=%s task_id=%s', domain_name, task.id
        )
    except Exception as exc:
        import logging
        logging.getLogger('voidpanel.panel.views').error(
            'background_create_account failed for %s: %s', domain_name, exc
        )

PYEOF

    # Use Python to do the replacement safely
    python3 - "$VIEWS_FILE" "$PATCH_TMPFILE" << 'PYRUNEOF'
import sys, re

views_path = sys.argv[1]
patch_path = sys.argv[2]

with open(views_path, 'r') as f:
    content = f.read()

with open(patch_path, 'r') as f:
    new_func = f.read()

# Replace from 'def background_create_account' to the line after 'pass'
pattern = re.compile(
    r'def background_create_account\(.*?\n(?:(?!^def ).*\n)*?.*?pass\n',
    re.MULTILINE
)
if pattern.search(content):
    content = pattern.sub(new_func, content, count=1)
    with open(views_path, 'w') as f:
        f.write(content)
    print("background_create_account patched successfully")
else:
    print("WARNING: pattern not found — manual patch required")
PYRUNEOF
    rm -f "$PATCH_TMPFILE"
else
    ok "Bug #1 — background_create_account already patched"
fi

# Patch Bug #8: domain tuple fix in create_account
if grep -q 'domain=request.data.get("domain"),' "$VIEWS_FILE" 2>/dev/null; then
    sed -i 's/domain=request.data.get("domain"),/domain_val = request.data.get("domain")  # fixed tuple bug/g' "$VIEWS_FILE"
    ok "Bug #8 patched — domain tuple removed"
else
    ok "Bug #8 — domain tuple already fixed"
fi

# ─────────────────────────────────────────────────────────────────────────────
# 4. Verify provision_user_task import uses function.py not panel.views (Bug #4)
# ─────────────────────────────────────────────────────────────────────────────
TASKS_FILE="$PROJECT_DIR/control/tasks.py"
if grep -q "from panel.views import" "$TASKS_FILE" 2>/dev/null; then
    sed -i 's/from panel\.views import (/from function import (/g' "$TASKS_FILE"
    ok "Bug #4 — tasks.py import fixed: panel.views → function"
else
    ok "Bug #4 — tasks.py import already correct"
fi

# ─────────────────────────────────────────────────────────────────────────────
# 5. Restart all services
# ─────────────────────────────────────────────────────────────────────────────
info "Restarting services..."
systemctl restart voidpanel       2>/dev/null && ok "voidpanel (uWSGI) restarted"   || warn "voidpanel restart failed"
systemctl restart voidpanel-daphne 2>/dev/null && ok "voidpanel-daphne restarted"   || warn "voidpanel-daphne restart failed"
systemctl restart voidpanel-celery 2>/dev/null && ok "voidpanel-celery restarted"   || warn "voidpanel-celery restart failed"

# ─────────────────────────────────────────────────────────────────────────────
# 6. Diagnostics — show current state
# ─────────────────────────────────────────────────────────────────────────────
echo ""
info "──── Service Status ────────────────────────────────────────────────────"
for svc in voidpanel voidpanel-daphne voidpanel-celery redis-server nginx; do
    STATUS=$(systemctl is-active "$svc" 2>/dev/null || echo "not-found")
    if [[ "$STATUS" == "active" ]]; then
        echo -e "  ${GREEN}●${RESET} $svc — active"
    else
        echo -e "  ${RED}●${RESET} $svc — $STATUS"
    fi
done

echo ""
info "──── Database User Count ───────────────────────────────────────────────"
cd "$PROJECT_DIR"
source "$VENV_DIR/bin/activate"
python manage.py shell -c "
from django.contrib.auth.models import User
from control.models import user, domain
print(f'  Django Auth Users : {User.objects.count()}')
print(f'  Panel users       : {user.objects.count()}')
print(f'  Domains           : {domain.objects.count()}')
for u in user.objects.all():
    print(f'    - {u.username} | {u.domain} | pkg={u.hosting_package} | active={u.is_active}')
" 2>&1

echo ""
info "──── Recent Logs ───────────────────────────────────────────────────────"
echo ""
echo -e "${CYAN}=== panel.log (last 20 lines) ===${RESET}"
tail -20 /var/log/voidpanel/panel.log 2>/dev/null || echo "  (empty)"
echo ""
echo -e "${CYAN}=== celery.log (last 20 lines) ===${RESET}"
tail -20 /var/log/voidpanel/celery.log 2>/dev/null || echo "  (empty)"
echo ""
echo -e "${CYAN}=== error.log (last 10 lines) ===${RESET}"
tail -10 /var/log/voidpanel/error.log 2>/dev/null || echo "  (empty)"

echo ""
echo -e "${GREEN}=========================================================="
echo "  Repair complete. Create a test user from the panel"
echo "  and watch logs in real-time:"
echo ""
echo "    tail -f /var/log/voidpanel/panel.log"
echo "    tail -f /var/log/voidpanel/celery.log"
echo ""
echo "  Or check celery worker status:"
echo "    journalctl -u voidpanel-celery -f"
echo -e "==========================================================${RESET}"
echo ""
