#!/usr/bin/env bash
# SecureMailScope Quick Launcher
cd "$(dirname "$0")/securemailscope" || exit 1
echo "=========================================================="
echo " 🛡️ Starting SecureMailScope SOC Dashboard..."
echo " Open in browser: http://localhost:8090"
echo "=========================================================="
python3 dashboard_app.py
