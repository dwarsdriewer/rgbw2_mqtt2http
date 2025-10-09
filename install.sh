#!/usr/bin/env bash
# ============================================================
# Installationsskript für eine persistente Python-App mit venv
# ============================================================

set -e

# Check if running with sudo
if [ "$EUID" -ne 0 ]; then
    echo "This script must be run with sudo"
    exit 1
fi

# Check for required system packages
check_package() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "Required package '$1' is not installed. Please install it with:"
        echo "sudo apt-get install $2"
        exit 1
    fi
}

check_package python3 "python3"
check_package git "git"

# Get the directory where the install script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_NAME="rgbw2srv"
APP_DIR="$SCRIPT_DIR"
ENV_DIR="$APP_DIR/config"
SERVICE_FILE="/etc/systemd/system/$APP_NAME.service"
PYTHON_BIN="/usr/bin/python3"
SECRET_DEFAULT="ÄndereMich123!"

echo "=== $APP_NAME Setup wird gestartet ==="

# Create a system user for running the service
if id "$APP_NAME" &>/dev/null; then
    echo "User $APP_NAME already exists."
else
    echo "Creating system user $APP_NAME..."
    sudo useradd --system --no-create-home --shell /usr/sbin/nologin "$APP_NAME"
fi

# Create config directory if it doesn't exist
sudo mkdir -p "$ENV_DIR"
sudo chown root:$APP_NAME "$ENV_DIR"
sudo chmod 750 "$ENV_DIR"

apt-get update -y
apt-get install -y python3-venv

if [ ! -d "$APP_DIR/venv" ]; then
    sudo -u "$APP_NAME" "$PYTHON_BIN" -m venv "$APP_DIR/venv"
    
    # Set ownership and permissions of the venv directory
    sudo chown -R "$APP_NAME:$APP_NAME" "$APP_DIR/venv"
    sudo chmod 750 "$APP_DIR/venv"
    
    # Install required Python packages
    if [ -f "$APP_DIR/requirements.txt" ]; then
        echo "Installing Python requirements..."
        sudo -u "$APP_NAME" "$APP_DIR/venv/bin/pip" install -r "$APP_DIR/requirements.txt"
    else
        echo "Warning: requirements.txt not found in $APP_DIR"
        exit 1
    fi
fi

# Check if service.py exists in the script directory
if [ ! -f "$SCRIPT_DIR/service.py" ]; then
    echo "Error: service.py not found in $SCRIPT_DIR"
    exit 1
fi

if [ ! -f "$ENV_DIR/env" ]; then
    sudo tee "$ENV_DIR/env" > /dev/null <<EOF
MY_SECRET="$SECRET_DEFAULT"
EOF
    sudo chown root:$APP_NAME "$ENV_DIR/env"
    sudo chmod 640 "$ENV_DIR/env"  # root can read/write, service user can only read
fi

# Create systemd service file
SERVICE_FILE="/etc/systemd/system/$APP_NAME.service"

sudo tee "$SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=$APP_NAME Python Service
After=network.target

[Service]
Type=simple
User=$APP_NAME
Group=$APP_NAME
WorkingDirectory=$APP_DIR
EnvironmentFile=$ENV_DIR/env
ExecStart=$APP_DIR/venv/bin/python $APP_DIR/service.py
Restart=always
RestartSec=5

# Security settings
NoNewPrivileges=true
ProtectSystem=full
ProtectHome=read-only
PrivateTmp=true
ReadOnlyDirectories=/
ReadWriteDirectories=$APP_DIR/venv
StandardOutput=journal
StandardError=journal
Restart=always
RestartSec=5
NoNewPrivileges=true
ProtectSystem=full
ProtectHome=true
PrivateTmp=true
StandardOutput=journal
StandardError=journal
[Install]
WantedBy=multi-user.target
EOF

# Reload systemd daemon and enable service
sudo systemctl daemon-reload
sudo systemctl enable "$APP_NAME.service"
sudo systemctl start "$APP_NAME.service"

echo "=== Installation completed ==="
echo "To check service status: sudo systemctl status $APP_NAME.service"
echo "To view logs: sudo journalctl -u $APP_NAME.service"