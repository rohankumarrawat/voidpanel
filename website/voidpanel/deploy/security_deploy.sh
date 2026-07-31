#!/bin/bash
set -euo pipefail

echo "=== VoidOnyx Security Deployment ==="

cd /home/voidpanelc091/voidpanel
source venv/bin/activate

# 1. Set DJANGO_SECRET_KEY if not in /etc/environment
if ! grep -q DJANGO_SECRET_KEY /etc/environment 2>/dev/null; then
    SKEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))")
    echo "DJANGO_SECRET_KEY=\"$SKEY\"" >> /etc/environment
    export DJANGO_SECRET_KEY="$SKEY"
    echo "✅ DJANGO_SECRET_KEY set"
else
    echo "✅ DJANGO_SECRET_KEY already exists"
fi

# 2. Set FERNET_KEY if not in /etc/environment
if ! grep -q FERNET_KEY /etc/environment 2>/dev/null; then
    FKEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
    echo "FERNET_KEY=\"$FKEY\"" >> /etc/environment
    export FERNET_KEY="$FKEY"
    echo "✅ FERNET_KEY set"
else
    echo "✅ FERNET_KEY already exists"
fi

# Source env vars
set -a
source /etc/environment
set +a

# 3. Add server_tokens off to nginx if not already there
if ! grep -q "server_tokens off" /etc/nginx/nginx.conf 2>/dev/null; then
    sed -i '/http {/a\    server_tokens off;' /etc/nginx/nginx.conf
    echo "✅ Nginx server_tokens off added"
else
    echo "✅ Nginx server_tokens already off"
fi

# 4. Test nginx config
nginx -t 2>&1
echo "✅ Nginx config valid"

# 5. Reload nginx
systemctl reload nginx
echo "✅ Nginx reloaded"

# 6. Also add env vars to gunicorn service file if it exists
GUNICORN_SERVICE=$(systemctl list-unit-files | grep -i gunicorn | awk '{print $1}' | head -1)
if [ -n "$GUNICORN_SERVICE" ]; then
    SERVICE_FILE=$(systemctl show "$GUNICORN_SERVICE" -p FragmentPath | cut -d= -f2)
    if [ -f "$SERVICE_FILE" ] && ! grep -q DJANGO_SECRET_KEY "$SERVICE_FILE" 2>/dev/null; then
        # Add to Environment line
        echo "⚠️  Note: Add env vars to $SERVICE_FILE if gunicorn doesn't pick them up"
    fi
    systemctl daemon-reload
    systemctl restart "$GUNICORN_SERVICE"
    echo "✅ Gunicorn service restarted: $GUNICORN_SERVICE"
else
    # Try restarting any gunicorn process
    echo "No gunicorn systemd service found, trying manual restart..."
    pkill -f "gunicorn.*voidpanel" 2>/dev/null || true
    sleep 2
    cd /home/voidpanelc091/voidpanel
    source venv/bin/activate
    set -a; source /etc/environment; set +a
    gunicorn voidpanel.wsgi:application --bind 127.0.0.1:8000 --workers 3 --daemon
    echo "✅ Gunicorn restarted manually"
fi

# 7. Quick test
sleep 2
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/ 2>/dev/null || echo "FAIL")
echo "✅ Site HTTP status: $HTTP_CODE"

echo ""
echo "=== Deployment Complete ==="
