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

User = get_user_model()


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


class InventoryShare(models.Model):
    """A shareable view-only link for a user's inventory."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="inventory_shares")
    token = models.SlugField(max_length=64, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True, help_text="Optional expiration date")
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

    def __str__(self):
        return f"Share({self.user_id}, {self.token}, active={self.is_active})"


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
