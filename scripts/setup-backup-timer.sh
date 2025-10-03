#!/bin/bash
# Setup automatic daily backups using systemd timer

set -e

echo "Setting up BlockShelf automatic backup system..."

# Copy systemd files to system directory
sudo cp blockshelf-backup.service /etc/systemd/system/
sudo cp blockshelf-backup.timer /etc/systemd/system/

# Reload systemd to recognize new files
sudo systemctl daemon-reload

# Enable and start the timer
sudo systemctl enable blockshelf-backup.timer
sudo systemctl start blockshelf-backup.timer

# Show timer status
echo ""
echo "Backup timer installed and activated!"
echo "Next scheduled run:"
systemctl list-timers blockshelf-backup.timer --no-pager

echo ""
echo "To manually trigger a backup:"
echo "  sudo systemctl start blockshelf-backup.service"
echo ""
echo "To check backup logs:"
echo "  sudo journalctl -u blockshelf-backup.service -f"
echo ""
echo "To disable automatic backups:"
echo "  sudo systemctl stop blockshelf-backup.timer"
echo "  sudo systemctl disable blockshelf-backup.timer"
