#!/usr/bin/env bash
# Quick deployment script for BlockShelf production updates
# Run this after pushing code changes to GitHub

set -euo pipefail

APP_DIR="/opt/blockshelf"
APP_USER="blockshelf"
SERVICE_NAME="blockshelf"
ENV_FILE="/etc/blockshelf/.env"

echo "==> Deploying BlockShelf updates..."

echo "==> Pulling latest code..."
sudo -u $APP_USER git -C "$APP_DIR" pull

echo "==> Cleaning Python cache..."
sudo -u $APP_USER find "$APP_DIR" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
sudo -u $APP_USER find "$APP_DIR" -name "*.pyc" -delete 2>/dev/null || true

echo "==> Running migrations..."
sudo -u $APP_USER bash -c "set -a; source $ENV_FILE; set +a; cd $APP_DIR && .venv/bin/python manage.py migrate --noinput"

echo "==> Collecting static files..."
sudo -u $APP_USER bash -c "set -a; source $ENV_FILE; set +a; cd $APP_DIR && .venv/bin/python manage.py collectstatic --noinput"

echo "==> Restarting service..."
sudo systemctl restart $SERVICE_NAME

echo "==> Waiting for service to start..."
sleep 2

echo "==> Checking service status..."
if sudo systemctl is-active --quiet $SERVICE_NAME; then
    echo "✓ Service is running"
    sudo systemctl status $SERVICE_NAME --no-pager --lines=5
else
    echo "✗ Service failed to start!"
    echo "Recent logs:"
    sudo journalctl -u $SERVICE_NAME -n 20 --no-pager
    exit 1
fi

echo
echo "==> Deployment complete!"
echo "View logs: sudo journalctl -u $SERVICE_NAME -f"
