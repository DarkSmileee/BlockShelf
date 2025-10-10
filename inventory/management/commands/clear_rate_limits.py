"""
Management command to clear all rate limiting and account lockout cache entries.
Useful for startup or manual reset.
"""

from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.conf import settings


class Command(BaseCommand):
    help = 'Clear all rate limiting and account lockout cache entries'

    def add_arguments(self, parser):
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output',
        )

    def handle(self, *args, **options):
        verbose = options.get('verbose', False)

        # Get all cache keys pattern (depends on cache backend)
        # For database cache, we need to query the cache table
        try:
            # Clear rate limit keys
            rate_limit_prefixes = [
                'login:',
                'signup:',
                'password_reset:',
                'account_lockout:',
            ]

            cleared_count = 0
            
            # For database cache backend
            if hasattr(cache, '_table'):
                from django.db import connection
                with connection.cursor() as cursor:
                    for prefix in rate_limit_prefixes:
                        cursor.execute(
                            f"DELETE FROM {cache._table} WHERE cache_key LIKE %s",
                            [f"%{prefix}%"]
                        )
                        deleted = cursor.rowcount
                        cleared_count += deleted
                        if verbose and deleted > 0:
                            self.stdout.write(f"Cleared {deleted} entries for prefix: {prefix}")
            
            # For other cache backends, try to clear by known patterns
            else:
                # This is a fallback - not all cache backends support pattern deletion
                # We'll just clear the entire cache to be safe
                cache.clear()
                if verbose:
                    self.stdout.write("Cleared entire cache (backend doesn't support pattern deletion)")
                cleared_count = "all"

            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully cleared {cleared_count} rate limiting cache entries'
                )
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error clearing cache: {str(e)}')
            )
            raise
