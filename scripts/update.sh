#!/usr/bin/env bash
# BlockShelf Quick Update Script
# Updates code, clears cache, runs migrations, restarts service
# Safe to run multiple times

set -euo pipefail

APP_DIR="/opt/blockshelf"
APP_USER="blockshelf"
SERVICE_NAME="blockshelf"
ENV_FILE="/etc/blockshelf/.env"

echo "╔════════════════════════════════════════╗"
echo "║     BlockShelf Update Script           ║"
echo "╚════════════════════════════════════════╝"
echo

# Check if running on production server
if [ ! -d "$APP_DIR" ]; then
    echo "Error: BlockShelf not found at $APP_DIR"
    echo "Please run the installer first:"
    echo "  bash <(curl -fsSL https://raw.githubusercontent.com/DarkSmileee/BlockShelf/main/scripts/install_blockshelf.sh)"
    exit 1
fi

if [ ! -f "$ENV_FILE" ]; then
    echo "Error: Environment file not found at $ENV_FILE"
    echo "Please check your installation."
    exit 1
fi

echo "→ Pulling latest code from GitHub..."
sudo -u $APP_USER git -C "$APP_DIR" pull
echo "  ✓ Code updated"
echo

echo "→ Cleaning Python bytecode cache..."
sudo -u $APP_USER find "$APP_DIR" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
sudo -u $APP_USER find "$APP_DIR" -name "*.pyc" -delete 2>/dev/null || true
echo "  ✓ Cache cleared"
echo

echo "→ Running database migrations..."
sudo -u $APP_USER bash -c "set -a; source $ENV_FILE; set +a; cd $APP_DIR && .venv/bin/python manage.py migrate --noinput"
echo "  ✓ Migrations complete"
echo

echo "→ Collecting static files..."
sudo -u $APP_USER bash -c "set -a; source $ENV_FILE; set +a; cd $APP_DIR && .venv/bin/python manage.py collectstatic --noinput" 2>&1 | grep -v "^0 static files copied" || true
echo "  ✓ Static files ready"
echo

echo "→ Restarting BlockShelf service..."
sudo systemctl restart $SERVICE_NAME
sleep 3

echo "→ Checking service status..."
if sudo systemctl is-active --quiet $SERVICE_NAME; then
    echo "  ✓ Service is running"
    echo
    sudo systemctl status $SERVICE_NAME --no-pager --lines=0 | head -3
else
    echo "  ✗ Service failed to start!"
    echo
    echo "Recent logs:"
    sudo journalctl -u $SERVICE_NAME -n 30 --no-pager
    exit 1
fi

echo
echo "╔════════════════════════════════════════╗"
echo "║      Update Complete! ✓                ║"
echo "╚════════════════════════════════════════╝"
echo
echo "Service status:  sudo systemctl status $SERVICE_NAME"
echo "View logs:       sudo journalctl -u $SERVICE_NAME -f"
echo "Application:     http://localhost:8000"
echo
