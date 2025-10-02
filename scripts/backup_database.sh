#!/bin/bash

################################################################################
# Database Backup Script for BlockShelf
#
# This script creates timestamped backups of both PostgreSQL and SQLite databases.
# It also manages backup retention (keeps last 30 daily, 12 weekly, 12 monthly).
#
# Usage:
#   ./backup_database.sh [sqlite|postgres|both]
#
# Cron example (daily at 2 AM):
#   0 2 * * * /path/to/BlockShelf/scripts/backup_database.sh both >> /var/log/blockshelf_backup.log 2>&1
################################################################################

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_ROOT="${BACKUP_ROOT:-$PROJECT_ROOT/backups}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
DATE_DAY=$(date +"%Y%m%d")
DATE_WEEK=$(date +"%Y_W%U")  # Year_WeekNumber
DATE_MONTH=$(date +"%Y%m")

# Load environment variables from .env
if [ -f "$PROJECT_ROOT/.env" ]; then
    export $(grep -v '^#' "$PROJECT_ROOT/.env" | xargs)
fi

# Retention policy (days)
DAILY_RETENTION=30
WEEKLY_RETENTION=84   # 12 weeks
MONTHLY_RETENTION=365 # 12 months

# Create backup directories
mkdir -p "$BACKUP_ROOT"/{sqlite,postgres,daily,weekly,monthly}

################################################################################
# Logging Functions
################################################################################

log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $*"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $*"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $*"
}

################################################################################
# SQLite Backup Functions
################################################################################

backup_sqlite() {
    log_info "Starting SQLite backup..."

    local db_path="$PROJECT_ROOT/db.sqlite3"

    if [ ! -f "$db_path" ]; then
        log_warn "SQLite database not found at $db_path"
        return 1
    fi

    local backup_file="$BACKUP_ROOT/sqlite/blockshelf_sqlite_${TIMESTAMP}.db"

    # Use sqlite3 .backup command for consistent backup
    if command -v sqlite3 &> /dev/null; then
        sqlite3 "$db_path" ".backup '$backup_file'" 2>/dev/null || {
            log_error "SQLite backup command failed"
            return 1
        }
    else
        # Fallback to simple copy (less safe but works)
        cp "$db_path" "$backup_file"
    fi

    # Compress the backup
    gzip -f "$backup_file"
    local compressed_file="${backup_file}.gz"

    if [ -f "$compressed_file" ]; then
        local size=$(du -h "$compressed_file" | cut -f1)
        log_success "SQLite backup completed: $compressed_file ($size)"

        # Create symbolic links for daily/weekly/monthly backups
        create_retention_links "$compressed_file" "sqlite"

        return 0
    else
        log_error "SQLite backup file not created"
        return 1
    fi
}

################################################################################
# PostgreSQL Backup Functions
################################################################################

backup_postgres() {
    log_info "Starting PostgreSQL backup..."

    # Extract database credentials from DATABASE_URL
    # Format: postgres://USER:PASSWORD@HOST:PORT/DBNAME
    if [ -z "${DATABASE_URL:-}" ]; then
        log_warn "DATABASE_URL not set, skipping PostgreSQL backup"
        return 1
    fi

    # Parse DATABASE_URL
    local db_url="$DATABASE_URL"

    # Extract components using regex
    if [[ $db_url =~ postgres://([^:]+):([^@]+)@([^:]+):([0-9]+)/(.+) ]]; then
        local db_user="${BASH_REMATCH[1]}"
        local db_pass="${BASH_REMATCH[2]}"
        local db_host="${BASH_REMATCH[3]}"
        local db_port="${BASH_REMATCH[4]}"
        local db_name="${BASH_REMATCH[5]}"
    else
        log_error "Could not parse DATABASE_URL format"
        return 1
    fi

    local backup_file="$BACKUP_ROOT/postgres/blockshelf_postgres_${TIMESTAMP}.sql"

    # Set password for pg_dump
    export PGPASSWORD="$db_pass"

    # Create backup with pg_dump
    if pg_dump -h "$db_host" -p "$db_port" -U "$db_user" \
               --format=custom \
               --file="$backup_file" \
               "$db_name" 2>/dev/null; then

        # Compress the backup
        gzip -f "$backup_file"
        local compressed_file="${backup_file}.gz"

        if [ -f "$compressed_file" ]; then
            local size=$(du -h "$compressed_file" | cut -f1)
            log_success "PostgreSQL backup completed: $compressed_file ($size)"

            # Create symbolic links for daily/weekly/monthly backups
            create_retention_links "$compressed_file" "postgres"

            unset PGPASSWORD
            return 0
        else
            log_error "PostgreSQL backup file not created"
            unset PGPASSWORD
            return 1
        fi
    else
        log_error "pg_dump command failed"
        unset PGPASSWORD
        return 1
    fi
}

################################################################################
# Retention Management
################################################################################

create_retention_links() {
    local backup_file="$1"
    local db_type="$2"

    # Daily backup (keep for 30 days)
    local daily_link="$BACKUP_ROOT/daily/${db_type}_${DATE_DAY}.sql.gz"
    ln -sf "$backup_file" "$daily_link"

    # Weekly backup (keep for 12 weeks)
    local weekly_link="$BACKUP_ROOT/weekly/${db_type}_${DATE_WEEK}.sql.gz"
    ln -sf "$backup_file" "$weekly_link"

    # Monthly backup (keep for 12 months)
    local monthly_link="$BACKUP_ROOT/monthly/${db_type}_${DATE_MONTH}.sql.gz"
    ln -sf "$backup_file" "$monthly_link"
}

cleanup_old_backups() {
    log_info "Cleaning up old backups..."

    # Remove daily backups older than retention period
    find "$BACKUP_ROOT/daily" -type f -mtime +$DAILY_RETENTION -delete 2>/dev/null || true
    find "$BACKUP_ROOT/daily" -type l -mtime +$DAILY_RETENTION -delete 2>/dev/null || true

    # Remove weekly backups older than retention period
    find "$BACKUP_ROOT/weekly" -type f -mtime +$WEEKLY_RETENTION -delete 2>/dev/null || true
    find "$BACKUP_ROOT/weekly" -type l -mtime +$WEEKLY_RETENTION -delete 2>/dev/null || true

    # Remove monthly backups older than retention period
    find "$BACKUP_ROOT/monthly" -type f -mtime +$MONTHLY_RETENTION -delete 2>/dev/null || true
    find "$BACKUP_ROOT/monthly" -type l -mtime +$MONTHLY_RETENTION -delete 2>/dev/null || true

    # Remove orphaned files in main backup directories
    find "$BACKUP_ROOT/sqlite" -type f -mtime +$MONTHLY_RETENTION -delete 2>/dev/null || true
    find "$BACKUP_ROOT/postgres" -type f -mtime +$MONTHLY_RETENTION -delete 2>/dev/null || true

    log_success "Cleanup completed"
}

################################################################################
# Main Execution
################################################################################

main() {
    local mode="${1:-both}"

    log_info "================================"
    log_info "BlockShelf Database Backup"
    log_info "Mode: $mode"
    log_info "Timestamp: $TIMESTAMP"
    log_info "================================"

    local success=0
    local failed=0

    case "$mode" in
        sqlite)
            if backup_sqlite; then
                ((success++))
            else
                ((failed++))
            fi
            ;;
        postgres)
            if backup_postgres; then
                ((success++))
            else
                ((failed++))
            fi
            ;;
        both)
            if backup_sqlite; then
                ((success++))
            else
                ((failed++))
            fi

            if backup_postgres; then
                ((success++))
            else
                ((failed++))
            fi
            ;;
        *)
            log_error "Invalid mode: $mode"
            log_info "Usage: $0 [sqlite|postgres|both]"
            exit 1
            ;;
    esac

    # Cleanup old backups
    cleanup_old_backups

    # Summary
    log_info "================================"
    log_info "Backup Summary:"
    log_info "  Successful: $success"
    log_info "  Failed: $failed"
    log_info "================================"

    if [ $failed -eq 0 ]; then
        log_success "All backups completed successfully!"
        exit 0
    else
        log_warn "Some backups failed. Check logs above."
        exit 1
    fi
}

# Run main function
main "$@"
