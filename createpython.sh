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
SERVICE_FILE="/etc/systemd/system/${PROJECT_NAME}.service"

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

# Upgrade pip and install uWSGI
echo "Upgrading pip and installing uWSGI..."
pip install --upgrade pip
pip install uwsgi

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
deactivate

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

# Create systemd service for uWSGI with project name
echo "Creating uWSGI systemd service as $SERVICE_FILE..."
sudo bash -c "cat > $SERVICE_FILE" << EOL
[Unit]
Description=uWSGI Emperor service for $PROJECT_NAME
After=network.target

[Service]
ExecStartPre=/bin/rm -f $PROJECT_DIR/${PROJECT_NAME}.sock
ExecStart=$VENV_DIR/bin/uwsgi --ini $UWSGI_INI
Restart=always
User=www-data
Group=www-data
UMask=007

[Install]
WantedBy=multi-user.target
EOL
sudo chown -R www-data:www-data $PROJECT_DIR



