# Backup Scheduling Guide

This document explains how to schedule automated backups for BlockShelf.

## Overview

BlockShelf includes a backup system that can create:
1. **Full database backups** - Complete backup of all data
2. **Per-user inventory backups** - JSON exports of individual user inventories

Backups are automatically rotated, keeping the 10 most recent backups by default.

## Manual Backups

### Via Web Interface
- **Users**: Go to Settings → Backups → "Create Backup Now"
- **Admins**: Go to Settings → Backups → "Create Full DB Backup" or "Backup All Users"

### Via Command Line
```bash
# Create full database backup
python manage.py create_backups --full-db

# Create backups for all users
python manage.py create_backups --all-users

# Create both
python manage.py create_backups --full-db --all-users

# Specify how many backups to keep (default: 10)
python manage.py create_backups --full-db --keep 7
```

## Scheduled Backups

### Option 1: Cron (Linux/Unix)

Edit your crontab:
```bash
crontab -e
```

Add one of these schedules:

**Daily backups at 2 AM:**
```cron
0 2 * * * cd /path/to/BlockShelf && /path/to/venv/bin/python manage.py create_backups --full-db --all-users >> /var/log/blockshelf-backup.log 2>&1
```

**Every 6 hours:**
```cron
0 */6 * * * cd /path/to/BlockShelf && /path/to/venv/bin/python manage.py create_backups --full-db --all-users >> /var/log/blockshelf-backup.log 2>&1
```

**Daily at 2 AM (full DB) + Every 4 hours (user inventories):**
```cron
0 2 * * * cd /path/to/BlockShelf && /path/to/venv/bin/python manage.py create_backups --full-db >> /var/log/blockshelf-backup.log 2>&1
0 */4 * * * cd /path/to/BlockShelf && /path/to/venv/bin/python manage.py create_backups --all-users >> /var/log/blockshelf-backup.log 2>&1
```

### Option 2: Systemd Timer (Modern Linux)

Create a service file: `/etc/systemd/system/blockshelf-backup.service`
```ini
[Unit]
Description=BlockShelf Backup Service
After=network.target

[Service]
Type=oneshot
User=www-data
WorkingDirectory=/path/to/BlockShelf
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/python manage.py create_backups --full-db --all-users
StandardOutput=journal
StandardError=journal
```

Create a timer file: `/etc/systemd/system/blockshelf-backup.timer`
```ini
[Unit]
Description=BlockShelf Backup Timer
Requires=blockshelf-backup.service

[Timer]
# Run daily at 2 AM
OnCalendar=daily
OnCalendar=02:00
Persistent=true

[Install]
WantedBy=timers.target
```

Enable and start the timer:
```bash
sudo systemctl daemon-reload
sudo systemctl enable blockshelf-backup.timer
sudo systemctl start blockshelf-backup.timer

# Check status
sudo systemctl status blockshelf-backup.timer
sudo systemctl list-timers
```

### Option 3: Docker/Docker Compose

If running in Docker, add a cron container or use the host's cron to run:

```bash
# Add to host crontab
0 2 * * * docker exec blockshelf_web python manage.py create_backups --full-db --all-users >> /var/log/blockshelf-backup.log 2>&1
```

Or create a separate cron service in `docker-compose.yml`:

```yaml
services:
  backup:
    image: your-blockshelf-image
    depends_on:
      - db
    volumes:
      - ./media:/app/media
    environment:
      - DATABASE_URL=postgresql://...
    command: >
      sh -c "
        while true; do
          python manage.py create_backups --full-db --all-users
          sleep 86400
        done
      "
```

## Backup Rotation

The backup system automatically keeps the 10 most recent backups. You can customize this:

```bash
# Keep 7 backups
python manage.py create_backups --full-db --keep 7

# Keep 20 backups
python manage.py create_backups --all-users --keep 20
```

## Backup Storage

Backups are stored in `MEDIA_ROOT/backups/`:
- `backups/full_db/` - Database backups
- `backups/user_inventory/{user_id}/` - Per-user inventory backups

### Storage Considerations

**SQLite:**
- Full DB backup = copy of entire `.sqlite3` file
- Typically 10-100 MB depending on data

**PostgreSQL:**
- Full DB backup = compressed custom format (pg_dump -Fc)
- Typically 50-80% smaller than SQLite

**MySQL:**
- Full DB backup = SQL dump
- Similar size to PostgreSQL

**User Inventory:**
- JSON format
- Typically 10-500 KB per user depending on inventory size

### Recommended Schedule

- **Small deployments (1-10 users):** Daily full DB backup + daily user backups
- **Medium deployments (10-100 users):** Daily full DB backup + every 6 hours user backups
- **Large deployments (100+ users):** Daily full DB backup + every 4 hours user backups

## Restoring from Backup

### Full Database Restore

**PostgreSQL:**
```bash
pg_restore -h localhost -U postgres -d blockshelf_db backups/full_db/db_backup_20231215_020000.sql
```

**MySQL:**
```bash
mysql -u root -p blockshelf_db < backups/full_db/db_backup_20231215_020000.sql
```

**SQLite:**
```bash
cp backups/full_db/db_backup_20231215_020000.sqlite3 db.sqlite3
```

### User Inventory Restore

User inventory backups are JSON files that can be imported via the web interface:
1. Go to Inventory → Import CSV / Excel
2. Convert JSON to CSV if needed, or modify the import to support JSON

Or use Django shell:
```python
import json
from inventory.models import InventoryItem, User

user = User.objects.get(username='john')
with open('backups/user_inventory/1/john_inventory_20231215_020000.json') as f:
    data = json.load(f)
    for item_data in data['items']:
        InventoryItem.objects.create(
            user=user,
            name=item_data['name'],
            part_id=item_data['part_id'],
            # ... other fields
        )
```

## Monitoring

### Check Last Backup

Via web interface: Settings → Backups (shows recent backups)

Via command line:
```bash
# List recent backups
ls -lh media/backups/full_db/ | tail -10

# Check backup sizes
du -sh media/backups/*
```

### Backup Logs

If using cron, check the log file:
```bash
tail -f /var/log/blockshelf-backup.log
```

If using systemd:
```bash
journalctl -u blockshelf-backup.service -f
```

## Security Considerations

1. **Backup Storage**: Keep backups in a secure location with restricted permissions
2. **Off-site Backups**: Copy backups to remote storage (S3, rsync, etc.)
3. **Encryption**: Consider encrypting backups containing sensitive data
4. **Access Control**: Ensure only admins can download full DB backups

### Example: Sync Backups to Remote Storage

```bash
# Add to cron after backup creation
rsync -avz /path/to/BlockShelf/media/backups/ user@backup-server:/backups/blockshelf/
```

## Troubleshooting

### "pg_dump: command not found"
Install PostgreSQL client tools:
```bash
# Ubuntu/Debian
sudo apt install postgresql-client

# RHEL/CentOS
sudo yum install postgresql
```

### "Permission denied" errors
Ensure the backup directory is writable:
```bash
chmod 755 media/backups/
chown -R www-data:www-data media/backups/
```

### Large backup files
- Enable compression for database backups (PostgreSQL custom format is already compressed)
- Consider backing up only user inventories more frequently
- Adjust rotation to keep fewer backups

### Out of disk space
- Monitor disk usage: `df -h`
- Reduce `--keep` parameter
- Move old backups to archive storage
- Set up automated cleanup of old backups
