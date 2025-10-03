"""
Management command to create scheduled backups.
Can be run via cron or systemd timer.

Usage:
    python manage.py create_backups --full-db
    python manage.py create_backups --all-users
    python manage.py create_backups --full-db --all-users
"""

from django.core.management.base import BaseCommand
from inventory.backup_utils import (
    create_full_db_backup,
    create_all_user_backups,
    rotate_backups,
)


class Command(BaseCommand):
    help = 'Create scheduled backups for database and/or user inventories'

    def add_arguments(self, parser):
        parser.add_argument(
            '--full-db',
            action='store_true',
            help='Create a full database backup',
        )
        parser.add_argument(
            '--all-users',
            action='store_true',
            help='Create inventory backups for all users',
        )
        parser.add_argument(
            '--keep',
            type=int,
            default=10,
            help='Number of backups to keep (default: 10)',
        )

    def handle(self, *args, **options):
        full_db = options['full_db']
        all_users = options['all_users']
        keep_count = options['keep']

        if not full_db and not all_users:
            self.stdout.write(
                self.style.ERROR(
                    'Please specify at least one of: --full-db, --all-users'
                )
            )
            return

        # Create full database backup
        if full_db:
            self.stdout.write('Creating full database backup...')
            backup = create_full_db_backup(created_by=None, is_scheduled=True)

            if backup:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ Full DB backup created: {backup.file_path} '
                        f'({backup.file_size / 1024 / 1024:.2f} MB)'
                    )
                )

                # Rotate old backups
                deleted = rotate_backups('full_db', keep_count=keep_count)
                if deleted > 0:
                    self.stdout.write(
                        self.style.WARNING(f'  Deleted {deleted} old backup(s)')
                    )
            else:
                self.stdout.write(
                    self.style.ERROR('✗ Failed to create full DB backup')
                )

        # Create all user inventory backups
        if all_users:
            self.stdout.write('Creating inventory backups for all users...')
            success_count, fail_count = create_all_user_backups(
                created_by=None, is_scheduled=True
            )

            if success_count > 0:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ Created backups for {success_count} user(s)'
                    )
                )

            if fail_count > 0:
                self.stdout.write(
                    self.style.ERROR(f'✗ Failed to create backups for {fail_count} user(s)')
                )

        self.stdout.write(self.style.SUCCESS('Backup process completed'))
