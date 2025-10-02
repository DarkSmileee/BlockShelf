#!/usr/bin/env bash
# Quick deployment script for BlockShelf production updates
# Run this after pushing code changes to GitHub

set -euo pipefail

APP_DIR="/opt/blockshelf"
APP_USER="blockshelf"
SERVICE_NAME="blockshelf"

echo "==> Deploying BlockShelf updates..."

echo "==> Pulling latest code..."
sudo -u $APP_USER git -C "$APP_DIR" pull

echo "==> Cleaning Python cache..."
sudo -u $APP_USER find "$APP_DIR" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
sudo -u $APP_USER find "$APP_DIR" -name "*.pyc" -delete 2>/dev/null || true

echo "==> Running migrations..."
sudo -u $APP_USER bash -lc "cd $APP_DIR && source .venv/bin/activate && python manage.py migrate --noinput"

echo "==> Collecting static files..."
sudo -u $APP_USER bash -lc "cd $APP_DIR && source .venv/bin/activate && python manage.py collectstatic --noinput"

echo "==> Restarting service..."
sudo systemctl restart $SERVICE_NAME

echo "==> Checking service status..."
sudo systemctl status $SERVICE_NAME --no-pager

echo
echo "==> Deployment complete!"
echo "Check logs: sudo journalctl -u $SERVICE_NAME -f"
