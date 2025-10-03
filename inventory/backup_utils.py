"""
Backup utility functions for creating and managing backups.
Supports both full database backups and per-user inventory backups.
"""

import json
import logging
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connection

from .models import Backup, InventoryItem

User = get_user_model()
logger = logging.getLogger(__name__)


def get_backup_dir():
    """Get or create the backup directory."""
    backup_dir = Path(settings.MEDIA_ROOT) / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


def create_full_db_backup(created_by: Optional[User] = None, is_scheduled: bool = False) -> Optional[Backup]:
    """
    Create a full database backup.
    Supports PostgreSQL, MySQL, and SQLite.

    Args:
        created_by: User who triggered the backup (None for scheduled)
        is_scheduled: True if this is a scheduled backup

    Returns:
        Backup instance or None if failed
    """
    db_config = settings.DATABASES['default']
    engine = db_config['ENGINE']

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = get_backup_dir() / "full_db"
    backup_dir.mkdir(parents=True, exist_ok=True)

    try:
        if 'postgresql' in engine:
            filename = f"db_backup_{timestamp}.sql"
            backup_path = backup_dir / filename

            # Use pg_dump
            cmd = [
                'pg_dump',
                '-h', db_config.get('HOST', 'localhost'),
                '-p', str(db_config.get('PORT', 5432)),
                '-U', db_config['USER'],
                '-d', db_config['NAME'],
                '-F', 'c',  # Custom format (compressed)
                '-f', str(backup_path)
            ]

            env = os.environ.copy()
            if db_config.get('PASSWORD'):
                env['PGPASSWORD'] = db_config['PASSWORD']

            subprocess.run(cmd, env=env, check=True, capture_output=True)

        elif 'mysql' in engine:
            filename = f"db_backup_{timestamp}.sql"
            backup_path = backup_dir / filename

            # Use mysqldump
            cmd = [
                'mysqldump',
                '-h', db_config.get('HOST', 'localhost'),
                '-P', str(db_config.get('PORT', 3306)),
                '-u', db_config['USER'],
                db_config['NAME'],
            ]

            if db_config.get('PASSWORD'):
                cmd.insert(4, f"-p{db_config['PASSWORD']}")

            with open(backup_path, 'w') as f:
                subprocess.run(cmd, stdout=f, check=True, capture_output=False)

        elif 'sqlite' in engine:
            filename = f"db_backup_{timestamp}.sqlite3"
            backup_path = backup_dir / filename

            # Copy SQLite database file
            import shutil
            db_path = db_config['NAME']
            shutil.copy2(db_path, backup_path)

        else:
            logger.error(f"Unsupported database engine: {engine}")
            return None

        # Get file size
        file_size = backup_path.stat().st_size

        # Create Backup record
        relative_path = f"backups/full_db/{filename}"
        backup = Backup.objects.create(
            backup_type='full_db',
            file_path=relative_path,
            file_size=file_size,
            created_by=created_by,
            is_scheduled=is_scheduled
        )

        logger.info(f"Full DB backup created: {backup_path} ({file_size} bytes)")
        return backup

    except Exception as e:
        logger.error(f"Failed to create full DB backup: {e}")
        return None


def create_user_inventory_backup(user: User, created_by: Optional[User] = None, is_scheduled: bool = False) -> Optional[Backup]:
    """
    Create a backup of a specific user's inventory as JSON.

    Args:
        user: User whose inventory to backup
        created_by: User who triggered the backup (can be admin or the user themselves)
        is_scheduled: True if this is a scheduled backup

    Returns:
        Backup instance or None if failed
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = get_backup_dir() / "user_inventory" / str(user.id)
    backup_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{user.username}_inventory_{timestamp}.json"
    backup_path = backup_dir / filename

    try:
        # Get all inventory items for the user
        items = InventoryItem.objects.filter(user=user).order_by('name', 'part_id', 'color')

        # Serialize to JSON
        backup_data = {
            'user': user.username,
            'user_id': user.id,
            'backup_date': datetime.now().isoformat(),
            'item_count': items.count(),
            'items': [
                {
                    'name': item.name,
                    'part_id': item.part_id,
                    'color': item.color,
                    'quantity_total': item.quantity_total,
                    'quantity_used': item.quantity_used,
                    'storage_location': item.storage_location,
                    'image_url': item.image_url,
                    'notes': item.notes,
                    'created_at': item.created_at.isoformat(),
                    'updated_at': item.updated_at.isoformat(),
                }
                for item in items
            ]
        }

        # Write to file
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False)

        # Get file size
        file_size = backup_path.stat().st_size

        # Create Backup record
        relative_path = f"backups/user_inventory/{user.id}/{filename}"
        backup = Backup.objects.create(
            backup_type='user_inventory',
            user=user,
            file_path=relative_path,
            file_size=file_size,
            created_by=created_by,
            is_scheduled=is_scheduled
        )

        logger.info(f"User inventory backup created for {user.username}: {backup_path} ({file_size} bytes)")
        return backup

    except Exception as e:
        logger.error(f"Failed to create user inventory backup for {user.username}: {e}")
        return None


def rotate_backups(backup_type: str, user: Optional[User] = None, keep_count: int = 10):
    """
    Delete old backups, keeping only the most recent ones.

    Args:
        backup_type: 'full_db' or 'user_inventory'
        user: User for inventory backups (None for full DB backups)
        keep_count: Number of backups to keep
    """
    query = Backup.objects.filter(backup_type=backup_type)

    if backup_type == 'user_inventory' and user:
        query = query.filter(user=user)
    elif backup_type == 'full_db':
        query = query.filter(user__isnull=True)

    # Get backups to delete (oldest ones beyond keep_count)
    old_backups = query.order_by('-created_at')[keep_count:]

    deleted_count = 0
    for backup in old_backups:
        try:
            backup.delete()  # This will also delete the physical file
            deleted_count += 1
        except Exception as e:
            logger.error(f"Failed to delete backup {backup.id}: {e}")

    if deleted_count > 0:
        logger.info(f"Rotated {deleted_count} old {backup_type} backups")

    return deleted_count


def create_all_user_backups(created_by: Optional[User] = None, is_scheduled: bool = False):
    """
    Create inventory backups for all users.

    Args:
        created_by: User who triggered the backup
        is_scheduled: True if this is a scheduled backup

    Returns:
        Tuple of (success_count, fail_count)
    """
    users = User.objects.filter(is_active=True)
    success_count = 0
    fail_count = 0

    for user in users:
        backup = create_user_inventory_backup(user, created_by, is_scheduled)
        if backup:
            success_count += 1
            # Rotate old backups for this user
            rotate_backups('user_inventory', user=user, keep_count=10)
        else:
            fail_count += 1

    logger.info(f"Created backups for {success_count} users, {fail_count} failed")
    return success_count, fail_count
