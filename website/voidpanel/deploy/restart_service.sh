#!/bin/bash
set -euo pipefail

echo "=== Restarting VoidOnyx Service ==="

# Add EnvironmentFile to voidonyx service if not present
if ! grep -q EnvironmentFile /etc/systemd/system/app-voidonyx-voidonyx.service; then
    sed -i '/\[Service\]/a EnvironmentFile=/etc/environment' /etc/systemd/system/app-voidonyx-voidonyx.service
    echo "Added EnvironmentFile to voidonyx service"
fi

# Fix file ownership
chown -R www-data:www-data /home/voidonyx/voidonyx/voidpanel/views.py
chown -R www-data:www-data /home/voidonyx/voidonyx/voidpanel/urls.py
chown -R www-data:www-data /home/voidonyx/voidonyx/voidpanel/settings.py
chown -R www-data:www-data /home/voidonyx/voidonyx/data/crypto.py
echo "Fixed file ownership"

# Reload and restart
systemctl daemon-reload
systemctl restart app-voidonyx-voidonyx.service
sleep 2
systemctl is-active app-voidonyx-voidonyx.service && echo "VOIDONYX SERVICE: ACTIVE" || echo "VOIDONYX SERVICE: FAILED"

# Test security endpoints
echo ""
echo "=== Security Verification ==="
echo -n "voidonyx.in: "
curl -s -o /dev/null -w "%{http_code}" https://voidonyx.in/
echo ""

echo -n "/admin/ (should be 404): "
curl -s -o /dev/null -w "%{http_code}" https://voidonyx.in/admin/
echo ""

echo -n "/notifications/ (should be 302): "
curl -s -o /dev/null -w "%{http_code}" https://voidonyx.in/notifications/
echo ""

echo -n "/db/ (should be 302): "
curl -s -o /dev/null -w "%{http_code}" https://voidonyx.in/db/
echo ""

echo -n "/chpass/ (should be 302): "
curl -s -o /dev/null -w "%{http_code}" https://voidonyx.in/chpass/
echo ""

echo -n "/overview/ (should be 302): "
curl -s -o /dev/null -w "%{http_code}" https://voidonyx.in/overview/
echo ""

echo -n "/admindocs/ (should be 403): "
curl -s -o /dev/null -w "%{http_code}" https://voidonyx.in/admindocs/
echo ""

echo -n "Server header: "
curl -sI https://voidonyx.in/ 2>/dev/null | grep -i "^Server:"
echo ""

echo "=== DONE ==="
