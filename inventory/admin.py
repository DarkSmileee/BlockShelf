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
    list_display = ("site_name", "allow_registration", "items_per_page")