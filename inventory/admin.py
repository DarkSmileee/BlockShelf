from django.contrib import admin
from .models import InventoryItem
from .models import RBPart, RBColor, RBElement
from .models import InventoryCollab
from .models import AppConfig

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
    
@admin.register(AppConfig)
class AppConfigAdmin(admin.ModelAdmin):
    """
    Defensive admin for the AppConfig singleton.

    - Avoids admin.E108 by detecting which model fields actually exist.
    - Displays an 'Items per page' column via a safe getter if the field exists.
    - Doesn't mark site settings fields as readonly so they can be edited in the admin UI.
    """

    # Show a sensible default set, including a getter for items-per-page
    list_display = ("site_name", "get_items_per_page", "allow_registration", "default_from_email")

    # Do not hard-code readonly fields here (user must be able to edit them):
    # If you previously had readonly_fields = (...), remove those names here.
    readonly_fields = ()

    def get_items_per_page(self, obj):
        return getattr(obj, "items_per_page", "—")
    get_items_per_page.short_description = "Items per page"
    get_items_per_page.admin_order_field = "items_per_page" 

    def get_fields(self, request, obj=None):
        """
        Build the field list for the admin form dynamically so we don't reference
        non-existent fields (which causes admin.E108 at startup).
        """
        # candidate field names in the order we want them shown
        candidates = [
            "site_name",
            "allow_registration",
            "default_from_email",
            "items_per_page",
            "rebrickable_api_key",
        ]

        fields = []
        for name in candidates:
            # Only include the field if the model actually defines it.
            try:
                # Use _meta to check model field existence in a robust way
                AppConfig._meta.get_field(name)
                fields.append(name)
            except Exception:
                # Not a DB field — skip it
                continue

        # Fallback: if no candidate fields detected (unlikely), just return the default
        if not fields:
            return super().get_fields(request, obj)
        return fields

    def get_readonly_fields(self, request, obj=None):
        # Keep everything editable by default. If you want certain fields read-only
        # for non-staff users, add logic here.
        return tuple()
