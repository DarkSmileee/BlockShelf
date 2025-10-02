# Database Backup & Recovery Strategy

## Overview

BlockShelf uses a comprehensive backup strategy to ensure data safety and enable quick recovery in case of data loss. This document outlines the backup procedures, retention policies, and restoration processes.

---

## Backup Strategy

### Retention Policy

The backup system follows a **Grandfather-Father-Son (GFS)** retention scheme:

| Type | Frequency | Retention | Purpose |
|------|-----------|-----------|---------|
| **Daily** | Every day | 30 days | Quick recovery from recent issues |
| **Weekly** | Every week | 12 weeks (84 days) | Monthly recovery point |
| **Monthly** | Every month | 12 months (365 days) | Long-term archive |

### Supported Databases

- **SQLite** (Development/Small deployments)
- **PostgreSQL** (Production/Large deployments)

---

## Automated Backups

### Setup Cron Job

Add to your crontab (`crontab -e`):

```bash
# Daily backup at 2:00 AM (both SQLite and PostgreSQL)
0 2 * * * /path/to/BlockShelf/scripts/backup_database.sh both >> /var/log/blockshelf_backup.log 2>&1

# Weekly backup verification (Sundays at 3 AM)
0 3 * * 0 /path/to/BlockShelf/scripts/verify_backups.sh >> /var/log/blockshelf_backup.log 2>&1
```

### Backup Locations

```
BlockShelf/
└── backups/
    ├── sqlite/          # Raw SQLite backups (compressed)
    ├── postgres/        # Raw PostgreSQL backups (compressed)
    ├── daily/           # Symbolic links to daily backups
    ├── weekly/          # Symbolic links to weekly backups
    └── monthly/         # Symbolic links to monthly backups
```

---

## Manual Backup

### SQLite

```bash
# Create a backup
./scripts/backup_database.sh sqlite

# Manual backup with custom location
sqlite3 db.sqlite3 ".backup '/path/to/backup/blockshelf_$(date +%Y%m%d).db'"
gzip /path/to/backup/blockshelf_$(date +%Y%m%d).db
```

### PostgreSQL

```bash
# Create a backup
./scripts/backup_database.sh postgres

# Manual backup with pg_dump
pg_dump -h localhost -U blockshelf_user \
        --format=custom \
        --file=blockshelf_$(date +%Y%m%d).sql \
        blockshelf_db
gzip blockshelf_$(date +%Y%m%d).sql
```

---

## Database Restoration

### ⚠️ **WARNING: Restoration will replace current data!**

Always verify you have the correct backup file before proceeding.

### SQLite Restoration

```bash
# Stop the application first
sudo systemctl stop blockshelf

# Restore from backup
./scripts/restore_database.sh backups/sqlite/blockshelf_sqlite_20250102_140530.db.gz sqlite

# Restart application
sudo systemctl start blockshelf
```

### PostgreSQL Restoration

```bash
# Stop the application
sudo systemctl stop blockshelf

# Restore from backup (will prompt for confirmation)
./scripts/restore_database.sh backups/postgres/blockshelf_postgres_20250102_140530.sql.gz postgres

# Run migrations (if needed)
python manage.py migrate

# Restart application
sudo systemctl start blockshelf
```

---

## Backup Verification

### Verify SQLite Backup Integrity

```bash
# Decompress and check integrity
gunzip -c backups/sqlite/blockshelf_sqlite_20250102_140530.db.gz > /tmp/test.db
sqlite3 /tmp/test.db "PRAGMA integrity_check;"
# Should output: ok
```

### Verify PostgreSQL Backup

```bash
# List contents of backup
pg_restore --list backups/postgres/blockshelf_postgres_20250102_140530.sql.gz
```

---

## Disaster Recovery Scenarios

### Scenario 1: Accidental Data Deletion (Recent)

**Recovery Time:** ~5 minutes

1. Identify the last good backup (usually today's or yesterday's daily backup)
2. Stop the application
3. Restore from the daily backup
4. Restart the application

```bash
sudo systemctl stop blockshelf
./scripts/restore_database.sh backups/daily/sqlite_20250102.sql.gz sqlite
sudo systemctl start blockshelf
```

### Scenario 2: Data Corruption (Older Data Needed)

**Recovery Time:** ~10 minutes

1. Identify the last known good backup (weekly or monthly)
2. Stop the application
3. Restore from the appropriate backup
4. Apply any recent data manually (if available from logs/exports)
5. Restart the application

### Scenario 3: Complete Server Failure

**Recovery Time:** ~30 minutes - 2 hours

1. Provision new server
2. Install BlockShelf (see deployment docs)
3. Copy backup files to new server
4. Restore latest backup
5. Verify application functionality

---

## Best Practices

### 1. **Test Restores Regularly**

Schedule quarterly restore tests to ensure backups are working:

```bash
# Test restoration to a temporary database
DATABASE_URL=postgres://user:pass@localhost/blockshelf_test \
./scripts/restore_database.sh backups/monthly/postgres_202501.sql.gz postgres
```

### 2. **Off-Site Backups**

Store backups in multiple locations:

**Option A: Cloud Storage (AWS S3)**

```bash
# Install AWS CLI
apt-get install awscli

# Sync backups to S3 (add to cron after daily backup)
aws s3 sync /path/to/BlockShelf/backups/ s3://your-bucket/blockshelf-backups/ \
    --exclude "*" --include "*.gz" \
    --storage-class STANDARD_IA
```

**Option B: Remote Server (rsync)**

```bash
# Add to cron after daily backup
rsync -avz --delete \
    /path/to/BlockShelf/backups/ \
    backup-server:/backups/blockshelf/
```

### 3. **Monitor Backup Success**

Add monitoring to alert on backup failures:

```bash
# Add to backup_database.sh or create a wrapper
if ! ./scripts/backup_database.sh both; then
    echo "Backup failed!" | mail -s "BlockShelf Backup FAILED" admin@example.com
fi
```

### 4. **Encrypt Sensitive Backups**

For production environments with sensitive data:

```bash
# Encrypt backup with GPG
gpg --symmetric --cipher-algo AES256 backups/postgres/backup.sql.gz

# Decrypt when needed
gpg --decrypt backups/postgres/backup.sql.gz.gpg > backup.sql.gz
```

---

## Migration Between Database Types

### SQLite to PostgreSQL

```bash
# 1. Export from SQLite
python manage.py dumpdata --natural-foreign --natural-primary \
    -e contenttypes -e auth.Permission > data.json

# 2. Update DATABASE_URL to PostgreSQL in .env

# 3. Run migrations
python manage.py migrate

# 4. Import data
python manage.py loaddata data.json
```

### PostgreSQL to SQLite

```bash
# 1. Export from PostgreSQL
python manage.py dumpdata --natural-foreign --natural-primary \
    -e contenttypes -e auth.Permission > data.json

# 2. Update DATABASE_URL to SQLite in .env

# 3. Run migrations
python manage.py migrate

# 4. Import data
python manage.py loaddata data.json
```

---

## Troubleshooting

### "pg_dump: command not found"

```bash
# Install PostgreSQL client tools
sudo apt-get install postgresql-client
```

### "sqlite3: command not found"

```bash
# Install SQLite tools
sudo apt-get install sqlite3
```

### Backup File Too Large

1. **Increase compression:**
   ```bash
   gzip -9 backup.sql  # Maximum compression
   ```

2. **Split large backups:**
   ```bash
   split -b 100M backup.sql.gz backup.sql.gz.part
   ```

### Restore Fails with "Permission Denied"

```bash
# Check file permissions
chmod 644 backups/sqlite/*.gz
chown $USER:$USER backups/sqlite/*.gz
```

---

## Backup Size Estimates

| Database Size | Compressed Backup Size | Backup Time |
|--------------|----------------------|-------------|
| 10 MB | ~2 MB | < 1 second |
| 100 MB | ~20 MB | ~5 seconds |
| 1 GB | ~200 MB | ~30 seconds |
| 10 GB | ~2 GB | ~5 minutes |

*Compression ratio: ~10:1 for typical Django databases*

---

## Security Considerations

1. **Restrict backup directory permissions:**
   ```bash
   chmod 700 backups/
   chown -R www-data:www-data backups/
   ```

2. **Use encrypted connections** for remote backups

3. **Rotate backup encryption keys** annually

4. **Audit backup access logs** regularly

5. **Implement backup integrity checks** (checksums/hashes)

---

## Monitoring & Alerts

### Check Backup Age

```bash
# Alert if latest backup is older than 25 hours
find backups/daily/ -name "*.gz" -mtime +1 -exec \
    echo "WARNING: Backup is older than 24 hours" \;
```

### Monitor Backup Size

```bash
# Alert if backup size changes dramatically
current_size=$(du -s backups/daily/ | cut -f1)
if [ $current_size -lt $((expected_size * 80 / 100)) ]; then
    echo "WARNING: Backup size is unusually small"
fi
```

---

## Compliance & Retention

For regulatory compliance (GDPR, HIPAA, etc.):

1. **Data Retention:** Configure retention policies per legal requirements
2. **Right to be Forgotten:** Implement backup purging procedures
3. **Audit Trails:** Log all backup and restore operations
4. **Access Control:** Limit backup access to authorized personnel only

---

## References

- [PostgreSQL Backup & Restore](https://www.postgresql.org/docs/current/backup.html)
- [SQLite Backup API](https://www.sqlite.org/backup.html)
- [Django Database Backups](https://docs.djangoproject.com/en/stable/topics/db/fixtures/)

---

## Quick Reference

```bash
# Backup both databases
./scripts/backup_database.sh both

# Backup only SQLite
./scripts/backup_database.sh sqlite

# Backup only PostgreSQL
./scripts/backup_database.sh postgres

# Restore SQLite
./scripts/restore_database.sh backups/sqlite/backup.db.gz sqlite

# Restore PostgreSQL
./scripts/restore_database.sh backups/postgres/backup.sql.gz postgres

# List backups
ls -lh backups/daily/
ls -lh backups/weekly/
ls -lh backups/monthly/
```

---

**Last Updated:** 2025-01-02
**Maintained By:** BlockShelf Development Team
