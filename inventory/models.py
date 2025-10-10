from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.core.cache import cache
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import Q, CheckConstraint
import secrets
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class InventoryItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='inventory_items')
    name = models.CharField(max_length=255)
    part_id = models.CharField(max_length=100, db_index=True)
    color = models.CharField(max_length=100, db_index=True)
    quantity_total = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    quantity_used = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    storage_location = models.CharField(max_length=100, blank=True)
    image_url = models.URLField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name', 'color', 'part_id']
        indexes = [
            # Composite index for common queries (duplicate detection, user inventory)
            models.Index(fields=['user', 'part_id', 'color'], name='inventory_n_user_id_f5c060_idx'),
            # Storage location index for search/filtering
            models.Index(fields=['storage_location'], name='inventory_storage_loc_idx'),
            # Name index for search queries (case-sensitive)
            models.Index(fields=['name'], name='inventory_name_idx'),
            # Created/updated indexes for sorting by date
            models.Index(fields=['created_at'], name='inventory_created_at_idx'),
            models.Index(fields=['updated_at'], name='inventory_updated_at_idx'),
            # User + name for common user inventory views
            models.Index(fields=['user', 'name'], name='inventory_user_name_idx'),
        ]
        constraints = [
            # Ensure quantity_used cannot exceed quantity_total (database-level)
            CheckConstraint(
                check=Q(quantity_used__lte=models.F('quantity_total')),
                name='quantity_used_lte_total',
            ),
            # Prevent duplicate items (same user, part_id, and color)
            models.UniqueConstraint(
                fields=['user', 'part_id', 'color'],
                name='unique_user_part_color',
            ),
        ]

    def clean(self):
        """
        Validate model data before saving.
        Enforces business rules not covered by field validators.
        """
        super().clean()

        # Ensure quantity_used <= quantity_total
        if self.quantity_used is not None and self.quantity_total is not None:
            if self.quantity_used > self.quantity_total:
                raise ValidationError({
                    'quantity_used': f'Quantity used ({self.quantity_used}) cannot exceed quantity total ({self.quantity_total}).'
                })

        # Ensure quantities are non-negative (redundant with validators, but explicit)
        if self.quantity_total is not None and self.quantity_total < 0:
            raise ValidationError({
                'quantity_total': 'Quantity total cannot be negative.'
            })

        if self.quantity_used is not None and self.quantity_used < 0:
            raise ValidationError({
                'quantity_used': 'Quantity used cannot be negative.'
            })

    def save(self, *args, **kwargs):
        """Override save to ensure clean() is called."""
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.part_id}) - {self.color}"

    @property
    def quantity_available(self):
        return max(0, (self.quantity_total or 0) - (self.quantity_used or 0))


# --- Rebrickable catalog (local copy of CSV dumps) ---

class RBColor(models.Model):
    id = models.IntegerField(primary_key=True)        # rebrickable color id
    name = models.CharField(max_length=120, db_index=True)
    rgb = models.CharField(max_length=6, blank=True)  # e.g. 'FF0000'
    is_trans = models.BooleanField(default=False)

    class Meta:
        verbose_name = "RB Color"
        verbose_name_plural = "RB Colors"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} (#{self.id})"


class RBPart(models.Model):
    # parts.csv
    part_num = models.CharField(max_length=50, primary_key=True)  # e.g. '3001'
    name = models.CharField(max_length=255, db_index=True)
    part_cat_id = models.IntegerField(null=True, blank=True)
    # not in dumps; we fill from API when first needed
    image_url = models.URLField(blank=True)

    class Meta:
        verbose_name = "RB Part"
        verbose_name_plural = "RB Parts"
        ordering = ["part_num"]

    def __str__(self):
        return f"{self.part_num} – {self.name}"


class RBElement(models.Model):
    # elements.csv
    element_id = models.CharField(max_length=50, primary_key=True)  # element ID (color-specific)
    part = models.ForeignKey(RBPart, on_delete=models.CASCADE, related_name="elements")
    color = models.ForeignKey(RBColor, on_delete=models.CASCADE, related_name="elements")

    class Meta:
        verbose_name = "RB Element"
        verbose_name_plural = "RB Elements"
        indexes = [models.Index(fields=["part", "color"], name='rbelement_part_color_idx')]

    def __str__(self):
        return f"{self.element_id} (part {self.part_id}, color {self.color_id})"


# === User preferences (per-user settings) ===

class UserPreference(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="userpreference")
    items_per_page = models.PositiveIntegerField(default=25)
    rebrickable_api_key = models.CharField(max_length=80, blank=True)

    def __str__(self):
        return f"{self.user} prefs"


class Note(models.Model):
    """User notes - simple notepad functionality."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notes")
    title = models.CharField(max_length=200)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['user', '-updated_at'], name='note_user_updated_idx'),
        ]

    def __str__(self):
        return f"{self.user.username}: {self.title}"


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_prefs(sender, instance, created, **kwargs):
    """Create UserPreference automatically when a new user is created."""
    if created:
        UserPreference.objects.create(user=instance)


# Cache invalidation signals for UserPreference
@receiver(post_save, sender=UserPreference)
def invalidate_user_preference_cache(sender, instance, **kwargs):
    """
    Invalidate cache when UserPreference is saved.
    This ensures per-user settings are always fresh.
    """
    # Clear any user-specific caches if needed
    cache_key = f"user_prefs:{instance.user.id}"
    cache.delete(cache_key)


def _generate_secure_share_token():
    """Generate a cryptographically secure token for inventory sharing."""
    return secrets.token_urlsafe(32)


class InventoryShare(models.Model):
    """A shareable view-only link for a user's inventory."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="inventory_shares")
    token = models.CharField(max_length=64, unique=True, default=_generate_secure_share_token, db_index=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True, help_text="Optional expiration date (default 30 days)")
    revoked_at = models.DateTimeField(null=True, blank=True, help_text="When the share was revoked")
    access_count = models.PositiveIntegerField(default=0, help_text="Number of times this link has been accessed")
    last_accessed_at = models.DateTimeField(null=True, blank=True)
    max_access_count = models.PositiveIntegerField(null=True, blank=True, help_text="Optional maximum number of accesses")

    class Meta:
        indexes = [
            models.Index(fields=["user", "is_active"], name='invshare_user_active_idx'),
            models.Index(fields=["token", "is_active"], name='invshare_token_active_idx'),
            models.Index(fields=["revoked_at"], name='invshare_revoked_idx'),
        ]

    def is_expired(self):
        """Check if the share link has expired."""
        if not self.is_active:
            return True
        if self.expires_at and timezone.now() > self.expires_at:
            return True
        if self.max_access_count and self.access_count >= self.max_access_count:
            return True
        return False

    def revoke(self):
        """Revoke this share link."""
        self.is_active = False
        self.revoked_at = timezone.now()
        self.save(update_fields=['is_active', 'revoked_at'])

    def record_access(self):
        """Record an access to this share link."""
        self.access_count = models.F('access_count') + 1
        self.last_accessed_at = timezone.now()
        self.save(update_fields=['access_count', 'last_accessed_at'])
        self.refresh_from_db()  # Refresh to get the actual count value

    def rotate_token(self):
        """
        Rotate the sharing token to a new secure value.
        Useful for security purposes if a token may have been compromised.
        """
        self.token = _generate_secure_share_token()
        self.save(update_fields=['token'])
        logger.info(f"Share token rotated for user {self.user_id}")

    def save(self, *args, **kwargs):
        """
        Override save to set default expiration if not provided.
        """
        # Set default expiration to 30 days if not specified and not yet set
        if not self.pk and self.expires_at is None:
            from django.conf import settings
            from datetime import timedelta
            default_days = getattr(settings, 'SHARE_LINK_DEFAULT_EXPIRY_DAYS', 30)
            self.expires_at = timezone.now() + timedelta(days=default_days)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Share({self.user_id}, {self.token[:8]}..., active={self.is_active})"


# --- COLLABORATION / INVITES -----------------------------------------------

def _invite_token():
    # url-safe and short enough for a slug
    return secrets.token_urlsafe(24)


class InventoryCollab(models.Model):
    """
    A row represents both an invite (pending) and the finalized collaboration (active).
    - When pending: collaborator is NULL, invited_email is set, accepted_at is NULL.
    - When accepted: collaborator is the user, invited_email may remain for history, accepted_at is set.
    """
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="owned_collabs"
    )
    collaborator = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True,
        related_name="collabs"
    )
    invited_email = models.EmailField(blank=True)
    token = models.SlugField(max_length=64, unique=True, default=_invite_token)

    can_edit = models.BooleanField(default=True)
    can_delete = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True, help_text="When the collaboration was revoked")

    class Meta:
        indexes = [
            models.Index(fields=["owner", "collaborator", "is_active"], name='invcollab_owner_collab_idx'),
            models.Index(fields=["revoked_at"], name='invcollab_revoked_idx'),
        ]
        # Prevent duplicate *active* collaborations (owner + collaborator)
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "collaborator"],
                condition=Q(collaborator__isnull=False, is_active=True),
                name="uniq_active_owner_collaborator",
            )
        ]

    @property
    def status(self) -> str:
        if not self.is_active:
            return "revoked"
        if self.accepted_at:
            return "active"
        return "pending"

    def mark_accepted(self, user):
        if user == self.owner:
            raise ValueError("Owner cannot accept their own invite.")
        self.collaborator = user
        self.accepted_at = timezone.now()
        self.is_active = True
        self.save(update_fields=["collaborator", "accepted_at", "is_active"])

    def revoke(self):
        """Revoke this collaboration."""
        self.is_active = False
        self.revoked_at = timezone.now()
        self.save(update_fields=['is_active', 'revoked_at'])

    def __str__(self):
        who = self.collaborator or self.invited_email or "pending"
        return f"{self.owner} → {who} [{self.status}]"


# === Singleton AppConfig (now: site-wide admin settings only) ===

class AppConfig(models.Model):
    """
    Singleton-style site configuration editable from the UI.
    Now only holds *site-wide* settings (admin-only).
    """
    singleton_id = models.PositiveSmallIntegerField(default=1, unique=True, editable=False)

    # General (kept)
    site_name = models.CharField(max_length=80, default="BlockShelf", blank=True)
    items_per_page = models.PositiveIntegerField(default=25)

    # Auth/Registration (admin)
    allow_registration = models.BooleanField(default=True)

    # Email (admin)
    default_from_email = models.EmailField(blank=True)

    class Meta:
        verbose_name = "App configuration"
        verbose_name_plural = "App configuration"

    def __str__(self):
        return "Site configuration"

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(singleton_id=1)
        return obj

    # lightweight cache helpers
    @classmethod
    def get_cached(cls):
        cfg = cache.get("appconfig_solo")
        if cfg is None:
            cfg = cls.get_solo()
            cache.set("appconfig_solo", cfg, 300)
        return cfg

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        cache.delete("appconfig_solo")


# === BACKUP SYSTEM ===

class Backup(models.Model):
    """
    Tracks backup files for the system.
    Supports full database backups (admin) and per-user inventory backups.
    """
    BACKUP_TYPE_CHOICES = [
        ('full_db', 'Full Database'),
        ('user_inventory', 'User Inventory'),
    ]

    backup_type = models.CharField(max_length=20, choices=BACKUP_TYPE_CHOICES)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="User for inventory backups (null for full DB backups)"
    )
    file_path = models.CharField(max_length=500, help_text="Path to backup file relative to MEDIA_ROOT")
    file_size = models.BigIntegerField(help_text="File size in bytes")
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='backups_created',
        help_text="User who triggered the backup"
    )
    is_scheduled = models.BooleanField(
        default=False,
        help_text="True if created by scheduled task, False if manual"
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['backup_type', '-created_at'], name='backup_type_created_idx'),
            models.Index(fields=['user', '-created_at'], name='backup_user_created_idx'),
        ]

    def __str__(self):
        if self.backup_type == 'user_inventory':
            return f"Inventory backup for {self.user.username} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
        return f"Full DB backup - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

    def delete(self, *args, **kwargs):
        """Override delete to also remove the physical file."""
        import os
        from django.conf import settings as django_settings

        file_full_path = os.path.join(django_settings.MEDIA_ROOT, self.file_path)
        if os.path.exists(file_full_path):
            try:
                os.remove(file_full_path)
            except Exception as e:
                logger.error(f"Failed to delete backup file {file_full_path}: {e}")

        super().delete(*args, **kwargs)


# === LOGIN ATTEMPT TRACKING (Security) ===

class LoginAttempt(models.Model):
    """
    Track login attempts for security monitoring and account lockout.
    Used to implement progressive account lockout after failed login attempts.
    """
    username = models.CharField(max_length=150, db_index=True, help_text="Username attempted")
    ip_address = models.GenericIPAddressField(help_text="IP address of the attempt")
    user_agent = models.CharField(max_length=500, blank=True, help_text="User agent string")
    success = models.BooleanField(default=False, help_text="Whether the login was successful")
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    failure_reason = models.CharField(
        max_length=200,
        blank=True,
        help_text="Reason for failure (invalid password, account locked, etc.)"
    )

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['username', '-timestamp'], name='login_username_time_idx'),
            models.Index(fields=['ip_address', '-timestamp'], name='login_ip_time_idx'),
            models.Index(fields=['success', '-timestamp'], name='login_success_time_idx'),
        ]

    def __str__(self):
        status = "SUCCESS" if self.success else "FAILED"
        return f"{status} - {self.username} from {self.ip_address} at {self.timestamp}"

    @classmethod
    def record_attempt(cls, username: str, ip_address: str, success: bool,
                      user_agent: str = '', failure_reason: str = '') -> 'LoginAttempt':
        """
        Record a login attempt.

        Args:
            username: The username attempted
            ip_address: IP address of the attempt
            success: Whether the login was successful
            user_agent: User agent string
            failure_reason: Reason for failure if applicable

        Returns:
            The created LoginAttempt instance
        """
        attempt = cls.objects.create(
            username=username,
            ip_address=ip_address,
            success=success,
            user_agent=user_agent[:500],  # Truncate to field length
            failure_reason=failure_reason[:200]
        )

        # Clear lockout cache on successful login
        if success:
            lockout_cache_key = f"account_lockout:{username}"
            cache.delete(lockout_cache_key)

        logger.info(
            f"Login attempt recorded: {username} from {ip_address} - "
            f"{'SUCCESS' if success else 'FAILED'}"
        )
        return attempt

    @classmethod
    def get_recent_failures(cls, username: str, minutes: int = 60) -> int:
        """
        Get count of failed login attempts for a username within the specified time window.

        Args:
            username: The username to check
            minutes: Time window in minutes to check (default 60)

        Returns:
            Count of failed attempts
        """
        from django.utils import timezone
        from datetime import timedelta

        cutoff_time = timezone.now() - timedelta(minutes=minutes)
        return cls.objects.filter(
            username=username,
            success=False,
            timestamp__gte=cutoff_time
        ).count()

    @classmethod
    def get_lockout_duration(cls, username: str) -> int:
        """
        Calculate lockout duration based on number of failed attempts.
        Implements progressive lockout: 5min, 15min, 1hr, 24hr.

        Args:
            username: The username to check

        Returns:
            Lockout duration in seconds (0 if not locked)
        """
        # Get recent failures in the last 24 hours
        failures_24h = cls.get_recent_failures(username, minutes=60 * 24)

        if failures_24h < 5:
            return 0  # Not locked

        # Progressive lockout schedule (in seconds)
        # 5-9 failures: 5 minutes
        # 10-14 failures: 15 minutes
        # 15-19 failures: 1 hour
        # 20+ failures: 24 hours
        if failures_24h < 10:
            return 300  # 5 minutes
        elif failures_24h < 15:
            return 900  # 15 minutes
        elif failures_24h < 20:
            return 3600  # 1 hour
        else:
            return 86400  # 24 hours

    @classmethod
    def is_account_locked(cls, username: str) -> tuple[bool, int]:
        """
        Check if an account is currently locked due to failed login attempts.
        Uses caching to prevent recalculation on every request.

        Args:
            username: The username to check

        Returns:
            Tuple of (is_locked, time_remaining_seconds)
        """
        from django.utils import timezone

        # Create a cache key for this username's lockout
        lockout_cache_key = f"account_lockout:{username}"

        # Check if we have a cached lockout with expiry
        cached_lockout = cache.get(lockout_cache_key)
        if cached_lockout:
            # cached_lockout is the unix timestamp when lockout expires
            time_remaining = int(cached_lockout - timezone.now().timestamp())
            if time_remaining > 0:
                return True, time_remaining
            else:
                # Lockout expired, clear cache
                cache.delete(lockout_cache_key)
                return False, 0

        # No cached lockout, check if we need to create one
        # Get the most recent failed attempt
        last_failure = cls.objects.filter(
            username=username,
            success=False
        ).order_by('-timestamp').first()

        if not last_failure:
            return False, 0

        # Calculate lockout duration based on failure count
        lockout_duration = cls.get_lockout_duration(username)

        if lockout_duration == 0:
            return False, 0

        # Check if still within lockout period
        time_since_failure = (timezone.now() - last_failure.timestamp).total_seconds()
        time_remaining = int(lockout_duration - time_since_failure)

        if time_remaining > 0:
            # Cache the lockout expiry time
            lockout_expiry = timezone.now().timestamp() + time_remaining
            cache.set(lockout_cache_key, lockout_expiry, time_remaining)
            return True, time_remaining
        else:
            return False, 0

    @classmethod
    def clear_attempts(cls, username: str) -> int:
        """
        Clear all failed login attempts for a username.
        Useful for admin unlocking accounts.

        Args:
            username: The username to clear attempts for

        Returns:
            Number of attempts cleared
        """
        count = cls.objects.filter(username=username, success=False).count()
        cls.objects.filter(username=username, success=False).delete()

        # Clear lockout cache
        lockout_cache_key = f"account_lockout:{username}"
        cache.delete(lockout_cache_key)

        logger.info(f"Cleared {count} failed login attempts for {username}")
        return count
