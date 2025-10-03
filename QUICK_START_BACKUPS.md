# Quick Start: Backup System

## TL;DR

**For Users:**
- Go to Settings → Backups → Click "Create Backup Now"
- Download your inventory backups anytime

**For Admins:**
- Settings → Backups → "Create Full DB Backup" or "Backup All Users"
- Set up daily cron: `0 2 * * * cd /path/to/BlockShelf && python manage.py create_backups --full-db --all-users`

**For Sorting:**
- Just sort your inventory normally - your preference is automatically saved!
- When you return to the inventory page, your last sort is restored

---

## Setup (First Time Only)

### 1. Apply Database Migration

```bash
cd /path/to/BlockShelf
python manage.py migrate
```

### 2. Create Backup Directory

```bash
mkdir -p media/backups
chmod 755 media/backups
```

### 3. Test Manual Backup

Via web: Settings → Backups → "Create Backup Now"

Via CLI:
```bash
python manage.py create_backups --full-db
```

Verify it worked:
```bash
ls -lh media/backups/full_db/
```

### 4. Schedule Automatic Backups (Recommended)

**Option A: Cron (Simple)**

```bash
crontab -e
```

Add this line (change path to your installation):
```cron
0 2 * * * cd /path/to/BlockShelf && /path/to/venv/bin/python manage.py create_backups --full-db --all-users >> /var/log/blockshelf-backup.log 2>&1
```

**Option B: Docker**

Add to host crontab:
```cron
0 2 * * * docker exec blockshelf_web python manage.py create_backups --full-db --all-users >> /var/log/blockshelf-backup.log 2>&1
```

---

## Common Tasks

### Create a Backup

**Web Interface (easiest):**
1. Login as user or admin
2. Click Settings (gear icon)
3. Click "Backups" tab
4. Click "Create Backup Now"

**Command Line:**
```bash
# Full database backup
python manage.py create_backups --full-db

# All users' inventories
python manage.py create_backups --all-users

# Both
python manage.py create_backups --full-db --all-users
```

### Download a Backup

1. Settings → Backups
2. Find your backup in the list
3. Click "Download"

### Verify Backups Are Running

Check your backups folder:
```bash
ls -lh media/backups/full_db/ | tail -10
du -sh media/backups/*
```

Check cron logs (if using cron):
```bash
tail -f /var/log/blockshelf-backup.log
```

### Restore a Backup

**PostgreSQL:**
```bash
pg_restore -d blockshelf_db media/backups/full_db/db_backup_TIMESTAMP.sql
```

**SQLite:**
```bash
cp media/backups/full_db/db_backup_TIMESTAMP.sqlite3 db.sqlite3
```

**User Inventory:**
- JSON file can be viewed directly
- Or import via inventory import feature

---

## Backup Rotation

Backups are automatically cleaned up. By default, the 10 most recent backups are kept.

To change this:
```bash
# Keep 20 backups instead
python manage.py create_backups --full-db --keep 20
```

To change the default in your cron job:
```cron
0 2 * * * ... python manage.py create_backups --full-db --all-users --keep 15
```

---

## Troubleshooting

### "pg_dump: command not found"

Install PostgreSQL client tools:
```bash
# Ubuntu/Debian
sudo apt install postgresql-client

# RHEL/CentOS
sudo yum install postgresql
```

### "Permission denied"

Fix backup directory permissions:
```bash
chmod 755 media/backups/
chown -R www-data:www-data media/backups/
```

### Backups not running automatically

Check if cron is running:
```bash
sudo systemctl status cron
```

Check cron logs:
```bash
tail -f /var/log/blockshelf-backup.log
```

Verify crontab entry:
```bash
crontab -l | grep blockshelf
```

### Out of disk space

Check disk usage:
```bash
df -h
du -sh media/backups/*
```

Reduce number of backups kept:
```bash
python manage.py create_backups --full-db --keep 5
```

Or manually clean up old backups:
```bash
cd media/backups/full_db/
ls -t | tail -n +6 | xargs rm  # Keep only 5 most recent
```

---

## Recommended Schedules

**Small sites (< 10 users):**
```cron
# Daily at 2 AM
0 2 * * * ... create_backups --full-db --all-users
```

**Medium sites (10-100 users):**
```cron
# Daily DB backup at 2 AM
0 2 * * * ... create_backups --full-db

# User backups every 6 hours
0 */6 * * * ... create_backups --all-users
```

**Large sites (100+ users):**
```cron
# Daily DB backup at 2 AM
0 2 * * * ... create_backups --full-db

# User backups every 4 hours
0 */4 * * * ... create_backups --all-users
```

---

## Security Reminder

- 🔒 Always store backups in a secure location
- 🌍 Consider syncing to off-site storage (S3, rsync, etc.)
- 🔐 Encrypt backups if they contain sensitive data
- 👥 Only admins can download full DB backups
- 📝 Users can only download their own inventory backups

---

## Full Documentation

For complete documentation, see:
- `docs/backup_scheduling.md` - Complete scheduling guide
- `IMPLEMENTATION_SUMMARY.md` - Technical implementation details
