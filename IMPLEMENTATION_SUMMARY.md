# Implementation Summary: Backup System & Sorting Persistence

This document summarizes the features implemented for backup management and sorting persistence.

## Features Implemented

### 1. Backup System

A comprehensive backup system has been added to BlockShelf with the following capabilities:

#### **Backup Types:**
- **Full Database Backups** (Admin only): Complete database backup supporting PostgreSQL, MySQL, and SQLite
- **Per-User Inventory Backups**: JSON exports of individual user inventories

#### **Key Features:**
- ✅ Manual backup creation via web interface
- ✅ Automated backup rotation (keeps 10 most recent by default)
- ✅ Scheduled backups via management command (cron/systemd)
- ✅ Backup download and management
- ✅ Separate admin and user interfaces
- ✅ Backup metadata tracking (size, creation time, creator, type)

#### **User Capabilities:**
- Create manual backup of their own inventory
- Download their inventory backups (JSON format)
- View backup history (last 10 backups)

#### **Admin Capabilities:**
- Create full database backups
- Create backups for all users at once
- Download any backup (full DB or user inventories)
- Delete old backups manually
- View comprehensive backup history
- Trigger backups from Settings → Backups tab

### 2. Sorting Persistence

#### **Implementation:**
- Uses browser localStorage to remember user's last sorting preferences
- Automatically restores sorting when returning to inventory list
- Works across page refreshes and browser sessions
- Does not interfere with search queries or manual sorting changes

#### **Behavior:**
- When user clicks a sort column, preference is saved to localStorage
- On page load without sort parameters, saved preference is restored
- Search queries and manual URL parameters take precedence
- Preferences are per-browser (not synced across devices)

## Files Created

### Models & Migrations
- `inventory/models.py` - Added `Backup` model
- `inventory/migrations/0016_backup.py` - Database migration for Backup model

### Backend Logic
- `inventory/backup_utils.py` - Core backup creation and rotation logic
  - `create_full_db_backup()` - Full database backup
  - `create_user_inventory_backup()` - Per-user JSON backup
  - `rotate_backups()` - Automatic cleanup of old backups
  - `create_all_user_backups()` - Batch backup for all users

- `inventory/management/commands/create_backups.py` - Management command for scheduled backups
  - `--full-db` - Create full database backup
  - `--all-users` - Create backups for all users
  - `--keep N` - Number of backups to keep

### Views & URLs
- `inventory/views/backups.py` - Backup management views
  - `trigger_full_backup()` - Admin: manual full DB backup
  - `trigger_all_user_backups()` - Admin: backup all users
  - `trigger_user_backup()` - User: backup own inventory
  - `download_backup()` - Download backup file (with permission checks)
  - `delete_backup()` - Admin: delete specific backup
  - `list_user_backups()` - API: list user's backups
  - `list_all_backups()` - API: list all backups (admin)

- `inventory/urls.py` - Added backup URL routes
- `inventory/views/__init__.py` - Exported backup views
- `inventory/views/settings.py` - Added `handle_backups_tab()`

### Templates
- `templates/inventory/settings.html` - Added "Backups" tab with:
  - User section: Create & download own inventory backups
  - Admin section: Full DB backups management
  - Admin section: All user backups overview

- `templates/inventory/inventory_list.html` - Added localStorage sorting persistence JavaScript

### Documentation
- `docs/backup_scheduling.md` - Complete guide for:
  - Manual backups (web & CLI)
  - Scheduling with cron
  - Scheduling with systemd timers
  - Docker/Docker Compose integration
  - Backup restoration procedures
  - Security considerations
  - Troubleshooting

## Database Changes

### New Table: `inventory_backup`

| Column | Type | Description |
|--------|------|-------------|
| id | BigInteger | Primary key |
| backup_type | CharField(20) | 'full_db' or 'user_inventory' |
| user_id | ForeignKey | User for inventory backups (null for DB backups) |
| file_path | CharField(500) | Relative path to backup file |
| file_size | BigInteger | File size in bytes |
| created_at | DateTime | Backup creation timestamp |
| created_by_id | ForeignKey | User who triggered backup (null for scheduled) |
| is_scheduled | Boolean | True if created by cron/scheduled task |

**Indexes:**
- `backup_type, -created_at`
- `user_id, -created_at`

## Backup Storage Structure

```
media/
└── backups/
    ├── full_db/
    │   └── db_backup_20231215_020000.sql
    └── user_inventory/
        └── {user_id}/
            └── {username}_inventory_20231215_020000.json
```

## Usage Examples

### Creating Backups (Web Interface)

**Users:**
1. Navigate to Settings → Backups
2. Click "Create Backup Now"
3. Download from the list below

**Admins:**
1. Navigate to Settings → Backups
2. Click "Create Full DB Backup" for complete database backup
3. Click "Backup All Users" to create individual backups for all users
4. View and download from the admin sections below

### Creating Backups (Command Line)

```bash
# Daily full database backup (recommended)
python manage.py create_backups --full-db

# Backup all users' inventories
python manage.py create_backups --all-users

# Both at once
python manage.py create_backups --full-db --all-users

# Keep 20 backups instead of 10
python manage.py create_backups --full-db --keep 20
```

### Scheduling Backups (Cron)

Add to crontab (`crontab -e`):

```cron
# Daily at 2 AM
0 2 * * * cd /path/to/BlockShelf && /path/to/venv/bin/python manage.py create_backups --full-db --all-users >> /var/log/blockshelf-backup.log 2>&1
```

### Recommended Backup Schedule

- **Small deployments (<10 users)**: Daily backups (both DB and users)
- **Medium deployments (10-100 users)**: Daily DB + every 6 hours users
- **Large deployments (100+ users)**: Daily DB + every 4 hours users

## Security Considerations

1. **Permission Checks**:
   - Users can only download their own inventory backups
   - Admins can download all backups
   - Full DB backups are admin-only

2. **File System**:
   - Backups stored in `MEDIA_ROOT/backups/`
   - Automatic cleanup prevents disk space issues
   - Physical files deleted when Backup record is deleted

3. **Recommendations**:
   - Set up off-site backup sync (rsync, S3, etc.)
   - Encrypt backups if they contain sensitive data
   - Restrict file system permissions on backup directory
   - Monitor disk usage regularly

## Migration Instructions

To apply these changes to an existing installation:

1. **Run migrations:**
   ```bash
   python manage.py migrate
   ```

2. **Create backup directory:**
   ```bash
   mkdir -p media/backups
   chmod 755 media/backups
   ```

3. **Set up scheduled backups** (optional):
   - See `docs/backup_scheduling.md` for detailed instructions
   - Recommended: Daily cron job at 2 AM

4. **Test the system:**
   - Create a manual backup via web interface
   - Verify the backup file exists in `media/backups/`
   - Try downloading the backup
   - Test the management command

## Database Support

| Database | Full Backup Method | Compression | Notes |
|----------|-------------------|-------------|-------|
| PostgreSQL | pg_dump -Fc | Yes (built-in) | Requires `postgresql-client` |
| MySQL | mysqldump | No | Plain SQL dump |
| SQLite | File copy | No | Simple file copy |

**Requirements:**
- PostgreSQL: `pg_dump` command must be in PATH
- MySQL: `mysqldump` command must be in PATH
- SQLite: No external dependencies

## Sorting Persistence Details

### localStorage Key
- **Key**: `inventory_sort_prefs`
- **Value**: `{"sort": "name", "dir": "asc"}`

### Behavior
1. When user clicks a sort header, the preference is saved
2. On page load without sort params, preference is restored
3. Search queries preserve current sort or use saved preference
4. Manual URL parameters always take precedence

### Compatibility
- Works in all modern browsers with localStorage support
- Gracefully degrades if localStorage is unavailable
- Per-browser storage (not synced across devices)

## Testing Checklist

- [ ] Run database migration: `python manage.py migrate`
- [ ] Create manual backup (user interface)
- [ ] Create manual backup (admin interface)
- [ ] Download user inventory backup
- [ ] Download full DB backup (admin)
- [ ] Test management command: `python manage.py create_backups --full-db`
- [ ] Verify backup rotation (create 15 backups, verify only 10 remain)
- [ ] Test sorting persistence (sort by color, refresh page)
- [ ] Test sorting with search query
- [ ] Verify backup file permissions
- [ ] Check disk space usage

## Future Enhancements (Optional)

Potential improvements for future consideration:

1. **Cloud Storage Integration**: Store backups in S3, Azure Blob, etc.
2. **Incremental Backups**: Only backup changes since last backup
3. **Scheduled Backup UI**: Configure schedule from web interface
4. **Backup Notifications**: Email admins when backup completes/fails
5. **Restore from Backup**: Web interface for restoring backups
6. **Backup Encryption**: Automatic GPG encryption of backup files
7. **Multi-device Sort Sync**: Store sort preferences in database instead of localStorage

## Support

For issues or questions:
1. Check `docs/backup_scheduling.md` for detailed instructions
2. Review logs: `/var/log/blockshelf-backup.log` or `journalctl -u blockshelf-backup`
3. Verify disk space: `df -h` and `du -sh media/backups/`
4. Check file permissions: `ls -la media/backups/`
