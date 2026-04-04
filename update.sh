#!/bin/bash
# VoidPanel v2.0 - Production Safe Upgrade Script
# Run this on your live server: /var/www/panel/update.sh

PROJECT_DIR="/var/www/panel"
VENV_DIR="$PROJECT_DIR/venv"
LOG_FILE="/var/log/voidpanel_update.log"

# Colors for status
GREEN='\033[0;32m'
CYAN='\033[0;36m'
RED='\033[0;31m'
RESET='\033[0m'

status_msg() { echo -e "${CYAN}[+] $1...${RESET}"; }
success_msg() { echo -e "${GREEN}[✔] $1${RESET}"; }
error_msg() { echo -e "${RED}[!] $1${RESET}"; }

# Check for root
if [[ $EUID -ne 0 ]]; then
   error_msg "This script must be run as root" 
   exit 1
fi

exec > >(tee -i "$LOG_FILE") 2>&1

status_msg "Capturing Database Backup"
cp "$PROJECT_DIR/db.sqlite3" "$PROJECT_DIR/db.sqlite3.bak_$(date +%F_%T)"
success_msg "Backup created at $PROJECT_DIR/db.sqlite3.bak_..."

status_msg "Pulling Latest Code from GitHub (v2.0 branch)"
cd "$PROJECT_DIR"
git fetch origin
git reset --hard origin/v2.0

status_msg "Activating Virtual Environment"
source "$VENV_DIR/bin/activate"

status_msg "Installing New Dependencies"
pip install --upgrade pip
pip install -r requirements.txt || pip install django uwsgi psutil pexpect requests mysql-connector-python huggingface_hub djangorestframework django-cors-headers

status_msg "Synchronizing Database Models"
python manage.py migrate

status_msg "Updating Static Assets"
python manage.py collectstatic --noinput

status_msg "Recycling Production Services"
systemctl restart uwsgi
systemctl restart nginx

success_msg "VoidPanel v2.0 Upgrade Successful!"
echo -e "Review logs at: $LOG_FILE"
