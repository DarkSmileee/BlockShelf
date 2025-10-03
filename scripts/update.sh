#!/bin/bash
# BlockShelf Update Script
# Updates an existing BlockShelf installation while preserving data

set -e

APP_DIR="/opt/blockshelf"
APP_USER="blockshelf"
SERVICE_NAME="blockshelf"
ENV_FILE="/etc/blockshelf/.env"

echo "╔════════════════════════════════════════╗"
echo "║      BlockShelf Update Script          ║"
echo "╚════════════════════════════════════════╝"
echo ""

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    echo "❌ This script must be run as root (use sudo)"
    exit 1
fi

# Check if installation exists
if [ ! -d "$APP_DIR" ]; then
    echo "❌ BlockShelf not found at $APP_DIR"
    echo "   Run the install script first:"
    echo "   bash <(curl -fsSL https://raw.githubusercontent.com/DarkSmileee/BlockShelf/main/scripts/install.sh)"
    exit 1
fi

if [ ! -f "$ENV_FILE" ]; then
    echo "❌ Configuration file not found at $ENV_FILE"
    exit 1
fi

echo "→ Stopping BlockShelf service..."
systemctl stop $SERVICE_NAME

echo "→ Backing up current installation..."
BACKUP_DIR="/var/backups/blockshelf"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR
tar -czf "$BACKUP_DIR/blockshelf_pre_update_$TIMESTAMP.tar.gz" \
    -C $APP_DIR \
    --exclude='.venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='staticfiles' \
    --exclude='media' \
    . 2>/dev/null || true
echo "   Backup saved to: $BACKUP_DIR/blockshelf_pre_update_$TIMESTAMP.tar.gz"

echo "→ Pulling latest code from GitHub..."
cd $APP_DIR
sudo -u $APP_USER git fetch origin
sudo -u $APP_USER git reset --hard origin/main

echo "→ Cleaning Python bytecode cache..."
sudo -u $APP_USER find "$APP_DIR" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
sudo -u $APP_USER find "$APP_DIR" -name "*.pyc" -delete 2>/dev/null || true

echo "→ Installing/updating Python dependencies..."
sudo -u $APP_USER $APP_DIR/.venv/bin/pip install --upgrade pip
sudo -u $APP_USER $APP_DIR/.venv/bin/pip install -r $APP_DIR/requirements.txt --upgrade

echo "→ Running database migrations..."
sudo -u $APP_USER bash -c "set -a; source $ENV_FILE; set +a; cd $APP_DIR && $APP_DIR/.venv/bin/python manage.py migrate --noinput"

echo "→ Collecting static files..."
sudo -u $APP_USER bash -c "set -a; source $ENV_FILE; set +a; cd $APP_DIR && $APP_DIR/.venv/bin/python manage.py collectstatic --noinput"

echo "→ Starting BlockShelf service..."
systemctl start $SERVICE_NAME

echo "→ Checking service status..."
sleep 2
if systemctl is-active --quiet $SERVICE_NAME; then
    echo "✓ Service is running"
else
    echo "⚠️  Service may have failed to start"
    systemctl status $SERVICE_NAME --no-pager -l || true
fi

echo ""
echo "✓ Update complete!"
echo ""
echo "Useful commands:"
echo "  Check status:  sudo systemctl status $SERVICE_NAME"
echo "  View logs:     sudo journalctl -u $SERVICE_NAME -n 50"
echo "  Restart:       sudo systemctl restart $SERVICE_NAME"
echo ""
