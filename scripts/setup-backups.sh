#!/bin/bash
# Quick script to set up automatic daily backups

set -e

APP_DIR="/opt/blockshelf"

echo "Setting up BlockShelf automatic backups..."

if [ "$(id -u)" -ne 0 ]; then
    echo "❌ This script must be run as root (use sudo)"
    exit 1
fi

if [ ! -d "$APP_DIR" ]; then
    echo "❌ BlockShelf not found at $APP_DIR"
    exit 1
fi

# Copy backup service and timer files
echo "→ Installing backup timer files..."
cp $APP_DIR/scripts/blockshelf-backup.service /etc/systemd/system/
cp $APP_DIR/scripts/blockshelf-backup.timer /etc/systemd/system/

# Reload systemd
echo "→ Reloading systemd..."
systemctl daemon-reload

# Enable and start timer
echo "→ Enabling and starting timer..."
systemctl enable blockshelf-backup.timer
systemctl start blockshelf-backup.timer

echo ""
echo "✓ Automatic backups configured!"
echo ""
echo "Next backup:"
systemctl list-timers blockshelf-backup.timer --no-pager
echo ""
echo "Check logs: sudo journalctl -u blockshelf-backup.service -f"
echo "Manual trigger: sudo systemctl start blockshelf-backup.service"
echo ""
