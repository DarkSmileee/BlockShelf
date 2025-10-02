#!/bin/bash
set -e

APP_DIR="/opt/blockshelf"
APP_USER="blockshelf"
SERVICE_NAME="blockshelf"
ENV_FILE="/etc/blockshelf/.env"

echo "╔════════════════════════════════════════╗"
echo "║   BlockShelf Force Update Script      ║"
echo "╚════════════════════════════════════════╝"
echo ""

echo "→ Cleaning up migration conflicts..."
sudo -u $APP_USER git -C "$APP_DIR" clean -fd inventory/migrations/

echo "→ Pulling latest code from GitHub..."
sudo -u $APP_USER git -C "$APP_DIR" pull

echo "→ Cleaning Python bytecode cache..."
sudo -u $APP_USER find "$APP_DIR" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
sudo -u $APP_USER find "$APP_DIR" -name "*.pyc" -delete 2>/dev/null || true

echo "→ Running database migrations..."
sudo -u $APP_USER bash -c "set -a; source $ENV_FILE; set +a; cd $APP_DIR && $APP_DIR/.venv/bin/python manage.py migrate --noinput"

echo "→ Collecting static files..."
sudo -u $APP_USER bash -c "set -a; source $ENV_FILE; set +a; cd $APP_DIR && $APP_DIR/.venv/bin/python manage.py collectstatic --noinput"

echo "→ Restarting BlockShelf service..."
sudo systemctl restart $SERVICE_NAME

echo "→ Checking service status..."
sleep 2
sudo systemctl status $SERVICE_NAME --no-pager -l

echo ""
echo "✓ Update complete!"
echo "  Check logs: sudo journalctl -u $SERVICE_NAME -n 50"
