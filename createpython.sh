#!/bin/bash

# Check if all required arguments are provided
if [ "$#" -ne 3 ]; then
    echo "Usage: $0 <USER> <PROJECT_DIR> <PROJECT_NAME>"
    exit 1
fi

# Assign command-line arguments to variables
USER=$1
PROJECT_DIR=$2
PROJECT_NAME=$3

# Set additional variables based on input
VENV_DIR="$PROJECT_DIR/venv"
UWSGI_INI="$PROJECT_DIR/${PROJECT_NAME}.ini"

# Use a namespaced service name to prevent conflicts with reserved panel services
# (e.g. if user names their app "voidpanel" it won't overwrite the panel service)
SERVICE_NAME="app-${USER}-${PROJECT_NAME}"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

WEB_USER="www-data"
if ! id -u www-data &>/dev/null && id -u nginx &>/dev/null; then WEB_USER="nginx"; fi

# Create project directory
echo "Creating project directory..."
sudo mkdir -p $PROJECT_DIR


# Navigate to project directory
cd $PROJECT_DIR

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv $VENV_DIR

# Activate virtual environment
source $VENV_DIR/bin/activate

# Upgrade pip and install uWSGI using venv's pip directly (don't rely on activation)
echo "Upgrading pip and installing uWSGI..."
$VENV_DIR/bin/pip install --upgrade pip
$VENV_DIR/bin/pip install uwsgi

# Create a simple WSGI application file
echo "Creating a simple WSGI application..."
cat << EOF > $PROJECT_DIR/app.py
def application(environ, start_response):
    status = '200 OK'
    headers = [('Content-type', 'text/plain; charset=utf-8')]
    start_response(status, headers)
    return [b"Hello, world! This is a test WSGI application."]
EOF

# Deactivate virtual environment
deactivate 2>/dev/null || true

# Create uWSGI INI file using project name
cat << EOF > $UWSGI_INI
[uwsgi]
chdir = $PROJECT_DIR
module = app
callable = application
home = $VENV_DIR
master = true
processes = 5
socket = $PROJECT_DIR/${PROJECT_NAME}.sock
chmod-socket = 664
vacuum = true
die-on-term = true
EOF

# Create systemd service for uWSGI with namespaced service name
echo "Creating uWSGI systemd service as $SERVICE_FILE..."
sudo bash -c "cat > $SERVICE_FILE" << EOL
[Unit]
Description=uWSGI service for $USER/$PROJECT_NAME
After=network.target

[Service]
ExecStartPre=/bin/rm -f $PROJECT_DIR/${PROJECT_NAME}.sock
ExecStart=$VENV_DIR/bin/uwsgi --ini $UWSGI_INI
Restart=always
User=$WEB_USER
Group=$WEB_USER
UMask=007

[Install]
WantedBy=multi-user.target
EOL
# Set ownership: user owns the files, WEB_USER is group (for Nginx/uWSGI access)
sudo chown -R $USER:$WEB_USER $PROJECT_DIR

# Set base permissions (750 = owner rwx, group r-x, others none)
sudo chmod -R 750 $PROJECT_DIR
sudo chmod g+ws $PROJECT_DIR

# Explicitly ensure venv executables have +x AFTER chmod -R 750
# (chmod -R 750 on files sets rwxr-x--- which already has +x for owner, but be explicit)
sudo chmod +x $VENV_DIR/bin/pip $VENV_DIR/bin/pip3 $VENV_DIR/bin/pip3.10 $VENV_DIR/bin/uwsgi $VENV_DIR/bin/python $VENV_DIR/bin/python3 2>/dev/null || true
