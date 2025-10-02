#!/bin/bash

################################################################################
# Database Restore Script for BlockShelf
#
# This script restores databases from compressed backup files.
#
# Usage:
#   ./restore_database.sh <backup_file> [sqlite|postgres]
#
# Examples:
#   ./restore_database.sh backups/sqlite/blockshelf_sqlite_20250102_140530.db.gz sqlite
#   ./restore_database.sh backups/postgres/blockshelf_postgres_20250102_140530.sql.gz postgres
################################################################################

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Load environment variables
if [ -f "$PROJECT_ROOT/.env" ]; then
    export $(grep -v '^#' "$PROJECT_ROOT/.env" | xargs)
fi

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

restore_sqlite() {
    local backup_file="$1"

    if [ ! -f "$backup_file" ]; then
        log_error "Backup file not found: $backup_file"
        return 1
    fi

    log_info "Restoring SQLite database from $backup_file..."

    # Create temporary directory
    local temp_dir=$(mktemp -d)
    trap "rm -rf $temp_dir" EXIT

    # Decompress
    local decompressed="$temp_dir/db.sqlite3"
    gunzip -c "$backup_file" > "$decompressed"

    # Verify database integrity
    if ! sqlite3 "$decompressed" "PRAGMA integrity_check;" | grep -q "ok"; then
        log_error "Backup file is corrupted"
        return 1
    fi

    # Backup current database
    local current_db="$PROJECT_ROOT/db.sqlite3"
    if [ -f "$current_db" ]; then
        local backup_current="$current_db.backup_$(date +%Y%m%d_%H%M%S)"
        log_info "Backing up current database to $backup_current"
        cp "$current_db" "$backup_current"
    fi

    # Restore
    cp "$decompressed" "$current_db"

    log_success "SQLite database restored successfully"
    return 0
}

restore_postgres() {
    local backup_file="$1"

    if [ ! -f "$backup_file" ]; then
        log_error "Backup file not found: $backup_file"
        return 1
    fi

    log_info "Restoring PostgreSQL database from $backup_file..."

    # Parse DATABASE_URL
    if [ -z "${DATABASE_URL:-}" ]; then
        log_error "DATABASE_URL not set"
        return 1
    fi

    local db_url="$DATABASE_URL"

    if [[ $db_url =~ postgres://([^:]+):([^@]+)@([^:]+):([0-9]+)/(.+) ]]; then
        local db_user="${BASH_REMATCH[1]}"
        local db_pass="${BASH_REMATCH[2]}"
        local db_host="${BASH_REMATCH[3]}"
        local db_port="${BASH_REMATCH[4]}"
        local db_name="${BASH_REMATCH[5]}"
    else
        log_error "Could not parse DATABASE_URL"
        return 1
    fi

    export PGPASSWORD="$db_pass"

    # Create temporary directory
    local temp_dir=$(mktemp -d)
    trap "rm -rf $temp_dir" EXIT

    # Decompress
    local decompressed="$temp_dir/backup.sql"
    gunzip -c "$backup_file" > "$decompressed"

    # Confirm restoration
    log_warn "⚠️  WARNING: This will DROP and recreate the database '$db_name'"
    read -p "Are you sure you want to continue? (yes/no): " confirm

    if [ "$confirm" != "yes" ]; then
        log_info "Restore cancelled"
        unset PGPASSWORD
        return 0
    fi

    # Drop and recreate database
    log_info "Dropping existing database..."
    psql -h "$db_host" -p "$db_port" -U "$db_user" -d postgres \
         -c "DROP DATABASE IF EXISTS \"$db_name\";" 2>/dev/null || true

    log_info "Creating new database..."
    psql -h "$db_host" -p "$db_port" -U "$db_user" -d postgres \
         -c "CREATE DATABASE \"$db_name\";" 2>/dev/null

    # Restore from backup
    log_info "Restoring data..."
    pg_restore -h "$db_host" -p "$db_port" -U "$db_user" \
               -d "$db_name" \
               --no-owner --no-privileges \
               "$decompressed" 2>/dev/null

    unset PGPASSWORD

    log_success "PostgreSQL database restored successfully"
    return 0
}

main() {
    if [ $# -lt 1 ]; then
        log_error "Usage: $0 <backup_file> [sqlite|postgres]"
        log_info "Example: $0 backups/sqlite/blockshelf_sqlite_20250102_140530.db.gz sqlite"
        exit 1
    fi

    local backup_file="$1"
    local db_type="${2:-}"

    # Auto-detect database type if not specified
    if [ -z "$db_type" ]; then
        if [[ "$backup_file" =~ sqlite ]]; then
            db_type="sqlite"
        elif [[ "$backup_file" =~ postgres ]]; then
            db_type="postgres"
        else
            log_error "Could not detect database type from filename"
            log_info "Please specify: sqlite or postgres"
            exit 1
        fi
    fi

    log_info "================================"
    log_info "BlockShelf Database Restore"
    log_info "Backup file: $backup_file"
    log_info "Database type: $db_type"
    log_info "================================"

    case "$db_type" in
        sqlite)
            restore_sqlite "$backup_file"
            ;;
        postgres)
            restore_postgres "$backup_file"
            ;;
        *)
            log_error "Invalid database type: $db_type"
            log_info "Must be: sqlite or postgres"
            exit 1
            ;;
    esac
}

main "$@"
