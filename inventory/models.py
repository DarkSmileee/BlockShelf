from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.core.cache import cache
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import Q
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
            models.Index(fields=['user', 'part_id', 'color']),
        ]

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
        indexes = [models.Index(fields=["part", "color"])]

    def __str__(self):
        return f"{self.element_id} (part {self.part_id}, color {self.color_id})"


# === User preferences (per-user settings) ===

class UserPreference(models.Model):
    THEME_CHOICES = [
        ("system", "System"),
        ("light", "Light"),
        ("dark", "Dark"),
    ]
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="userpreference")
    theme = models.CharField(max_length=10, choices=THEME_CHOICES, default="system")

    # NEW: per-user settings moved from AppConfig
    items_per_page = models.PositiveIntegerField(default=25)
    rebrickable_api_key = models.CharField(max_length=80, blank=True)

    def __str__(self):
        return f"{self.user} prefs"


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_prefs(sender, instance, created, **kwargs):
    if created:
        UserPreference.objects.create(user=instance)


class InventoryShare(models.Model):
    """A shareable view-only link for a user's inventory."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="inventory_shares")
    token = models.SlugField(max_length=64, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True, help_text="Optional expiration date")
    access_count = models.PositiveIntegerField(default=0, help_text="Number of times this link has been accessed")
    last_accessed_at = models.DateTimeField(null=True, blank=True)
    max_access_count = models.PositiveIntegerField(null=True, blank=True, help_text="Optional maximum number of accesses")

    class Meta:
        indexes = [
            models.Index(fields=["user", "is_active"]),
            models.Index(fields=["token", "is_active"]),
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

    class Meta:
        indexes = [
            models.Index(fields=["owner", "collaborator", "is_active"]),
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
