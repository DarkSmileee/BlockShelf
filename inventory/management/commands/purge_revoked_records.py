"""
Management command to purge old revoked records for data retention compliance.

This command removes old revoked InventoryShare and InventoryCollab records
that have been inactive for a specified retention period.

Usage:
    python manage.py purge_revoked_records --days 90 --dry-run
    python manage.py purge_revoked_records --days 365
    python manage.py purge_revoked_records --shares-only --days 30
    python manage.py purge_revoked_records --collabs-only --days 180
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from datetime import timedelta
from inventory.models import InventoryShare, InventoryCollab


class Command(BaseCommand):
    help = 'Purge old revoked InventoryShare and InventoryCollab records for data retention compliance'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=90,
            help='Number of days to retain revoked records (default: 90)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )
        parser.add_argument(
            '--shares-only',
            action='store_true',
            help='Only purge revoked InventoryShare records',
        )
        parser.add_argument(
            '--collabs-only',
            action='store_true',
            help='Only purge revoked InventoryCollab records',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed information about records being purged',
        )

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']
        shares_only = options['shares_only']
        collabs_only = options['collabs_only']
        verbose = options['verbose']

        # Validate arguments
        if days < 1:
            raise CommandError('--days must be at least 1')

        if shares_only and collabs_only:
            raise CommandError('Cannot specify both --shares-only and --collabs-only')

        # Calculate cutoff date
        cutoff_date = timezone.now() - timedelta(days=days)

        self.stdout.write(
            self.style.WARNING(
                f"{'[DRY RUN] ' if dry_run else ''}Purging revoked records older than {days} days "
                f"(before {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')})"
            )
        )
        self.stdout.write('')

        total_deleted = 0

        # Purge InventoryShare records
        if not collabs_only:
            shares_deleted = self._purge_shares(cutoff_date, dry_run, verbose)
            total_deleted += shares_deleted

        # Purge InventoryCollab records
        if not shares_only:
            collabs_deleted = self._purge_collabs(cutoff_date, dry_run, verbose)
            total_deleted += collabs_deleted

        # Summary
        self.stdout.write('')
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"[DRY RUN] Would delete {total_deleted} record(s) in total"
                )
            )
            self.stdout.write(
                self.style.NOTICE(
                    "Run without --dry-run to actually delete these records"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully deleted {total_deleted} record(s) in total"
                )
            )

    def _purge_shares(self, cutoff_date, dry_run, verbose):
        """Purge old revoked InventoryShare records."""
        # Find revoked shares older than cutoff
        old_shares = InventoryShare.objects.filter(
            is_active=False,
            revoked_at__isnull=False,
            revoked_at__lt=cutoff_date
        )

        count = old_shares.count()

        if count == 0:
            self.stdout.write(
                self.style.NOTICE(
                    "No revoked InventoryShare records found older than cutoff date"
                )
            )
            return 0

        self.stdout.write(
            self.style.WARNING(
                f"Found {count} revoked InventoryShare record(s) to purge"
            )
        )

        if verbose:
            for share in old_shares[:10]:  # Show first 10
                self.stdout.write(
                    f"  - Share ID {share.id}: user={share.user.username}, "
                    f"revoked={share.revoked_at.strftime('%Y-%m-%d')}, "
                    f"accesses={share.access_count}"
                )
            if count > 10:
                self.stdout.write(f"  ... and {count - 10} more")

        if not dry_run:
            deleted_count, _ = old_shares.delete()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Deleted {deleted_count} InventoryShare record(s)"
                )
            )
            return deleted_count
        else:
            self.stdout.write(
                self.style.NOTICE(
                    f"[DRY RUN] Would delete {count} InventoryShare record(s)"
                )
            )
            return count

    def _purge_collabs(self, cutoff_date, dry_run, verbose):
        """Purge old revoked InventoryCollab records."""
        # Find revoked collaborations older than cutoff
        old_collabs = InventoryCollab.objects.filter(
            is_active=False,
            revoked_at__isnull=False,
            revoked_at__lt=cutoff_date
        )

        count = old_collabs.count()

        if count == 0:
            self.stdout.write(
                self.style.NOTICE(
                    "No revoked InventoryCollab records found older than cutoff date"
                )
            )
            return 0

        self.stdout.write(
            self.style.WARNING(
                f"Found {count} revoked InventoryCollab record(s) to purge"
            )
        )

        if verbose:
            for collab in old_collabs[:10]:  # Show first 10
                collaborator_name = (
                    collab.collaborator.username if collab.collaborator
                    else collab.invited_email or 'pending'
                )
                self.stdout.write(
                    f"  - Collab ID {collab.id}: owner={collab.owner.username}, "
                    f"collaborator={collaborator_name}, "
                    f"revoked={collab.revoked_at.strftime('%Y-%m-%d')}"
                )
            if count > 10:
                self.stdout.write(f"  ... and {count - 10} more")

        if not dry_run:
            deleted_count, _ = old_collabs.delete()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Deleted {deleted_count} InventoryCollab record(s)"
                )
            )
            return deleted_count
        else:
            self.stdout.write(
                self.style.NOTICE(
                    f"[DRY RUN] Would delete {count} InventoryCollab record(s)"
                )
            )
            return count
