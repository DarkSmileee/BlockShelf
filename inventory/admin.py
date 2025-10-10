from django.contrib import admin
from django.contrib.auth import get_user_model
from django.utils.html import format_html
from auditlog.registry import auditlog
from .models import InventoryItem, InventoryShare, UserPreference, Note
from .models import RBPart, RBColor, RBElement
from .models import InventoryCollab
from .models import AppConfig, LoginAttempt

# Register models with auditlog for security audit trail
# This tracks all create, update, and delete operations on these models
auditlog.register(get_user_model(), exclude_fields=['password', 'last_login'])
auditlog.register(InventoryItem, exclude_fields=['created_at', 'updated_at'])
auditlog.register(InventoryCollab, exclude_fields=['created_at'])
auditlog.register(InventoryShare, exclude_fields=['created_at'])
auditlog.register(UserPreference)
auditlog.register(AppConfig)

@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ('user', 'name', 'part_id', 'color', 'quantity_total', 'quantity_used', 'storage_location', 'created_at')
    list_filter = ('user', 'color', 'created_at')
    search_fields = ('name', 'part_id', 'color', 'storage_location')

@admin.register(RBPart)
class RBPartAdmin(admin.ModelAdmin):
    list_display = ("part_num", "name", "part_cat_id", "image_url")
    search_fields = ("part_num", "name")

@admin.register(RBColor)
class RBColorAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "rgb", "is_trans")
    search_fields = ("name",)

@admin.register(RBElement)
class RBElementAdmin(admin.ModelAdmin):
    list_display = ("element_id", "part", "color")
    list_select_related = ("part", "color")
    search_fields = ("element_id", "part__part_num", "part__name", "color__name")
    
@admin.register(InventoryCollab)
class InventoryCollabAdmin(admin.ModelAdmin):
    list_display = ("owner", "collaborator", "invited_email", "is_active", "can_edit", "can_delete", "created_at")
    readonly_fields = ("token", "created_at", "accepted_at")

@admin.register(UserPreference)
class UserPreferenceAdmin(admin.ModelAdmin):
    list_display = ("user", "items_per_page", "rebrickable_api_key")
    search_fields = ("user__username", "user__email")

@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "updated_at")
    list_filter = ("user", "created_at", "updated_at")
    search_fields = ("title", "description", "user__username")
    readonly_fields = ("created_at", "updated_at")

@admin.register(AppConfig)
class AppConfigAdmin(admin.ModelAdmin):
    """
    Defensive admin for the AppConfig singleton.

    - Avoids admin.E108 by detecting which model fields actually exist.
    - Displays an 'Items per page' column via a safe getter if the field exists.
    - Doesn't mark site settings fields as readonly so they can be edited in the admin UI.
    """

    # Show site-wide admin settings
    list_display = ("site_name", "allow_registration", "default_from_email")
    readonly_fields = ()


@admin.register(LoginAttempt)
class LoginAttemptAdmin(admin.ModelAdmin):
    """
    Admin interface for viewing and managing login attempts.
    Allows admins to monitor security and unlock accounts.
    """
    list_display = ('username', 'ip_address', 'success_badge', 'timestamp', 'failure_reason')
    list_filter = ('success', 'timestamp')
    search_fields = ('username', 'ip_address', 'user_agent')
    readonly_fields = ('username', 'ip_address', 'user_agent', 'success', 'timestamp', 'failure_reason')
    date_hierarchy = 'timestamp'
    ordering = ('-timestamp',)

    # Disable add permission (records are auto-created)
    def has_add_permission(self, request):
        return False

    # Disable change permission (records should not be modified)
    def has_change_permission(self, request, obj=None):
        return False

    def success_badge(self, obj):
        """Display success status with color badge."""
        if obj.success:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ SUCCESS</span>'
            )
        return format_html(
            '<span style="color: red; font-weight: bold;">✗ FAILED</span>'
        )
    success_badge.short_description = 'Status'

    actions = ['clear_failed_attempts']

    @admin.action(description='Clear failed attempts for selected users')
    def clear_failed_attempts(self, request, queryset):
        """Clear failed login attempts for selected usernames."""
        usernames = queryset.values_list('username', flat=True).distinct()
        total_cleared = 0
        for username in usernames:
            count = LoginAttempt.clear_attempts(username)
            total_cleared += count

        self.message_user(
            request,
            f'Cleared {total_cleared} failed login attempts for {len(usernames)} users.'
        )
