from django.urls import path
from . import views
from .views.health import health_check, liveness_check, readiness_check, metrics

app_name = "inventory"

urlpatterns = [
    # Health checks (for load balancers and monitoring)
    path("health/", health_check, name="health"),
    path("health/liveness/", liveness_check, name="liveness"),
    path("health/readiness/", readiness_check, name="readiness"),
    path("health/metrics/", metrics, name="metrics"),

    # Dashboard (home page)
    path("", views.dashboard, name="dashboard"),

    # Inventory CRUD
    path("inventory/", views.inventory_list, name="list"),
    path("add/", views.item_create, name="add"),
    path("<int:pk>/edit/", views.item_update, name="edit"),
    path("<int:pk>/delete/", views.item_delete, name="delete"),

    # Import / Export
    path("export_csv/", views.export_csv, name="export_csv"),
    path("import/", views.import_csv, name="import_csv"),

    # Lookup
    path("lookup/", views.lookup_part, name="lookup_part"),

    # Settings + Bulk update (new flow)
    path("settings/", views.settings_view, name="settings"),
    path("settings/delete-all/", views.delete_all_inventory, name="delete_all_inventory"),
    path("bulk-update/preview/", views.bulk_update_missing_preview, name="bulk_update_preview"),
    path("bulk-update/batch/", views.bulk_update_missing_batch, name="bulk_update_batch"),
    path('theme/', views.set_theme, name='set_theme'),

    # Sharing
    path('share/<slug:token>/', views.shared_inventory, name='shared_inventory'),
    path('settings/share/create/', views.create_share_link, name='create_share_link'),
    path('settings/share/revoke/', views.revoke_share_link, name='revoke_share_link'),
    
    # Invite flow
    path("settings/invite/create/", views.create_invite, name="create_invite"),
    path("settings/invite/<int:pk>/revoke/", views.revoke_invite, name="revoke_invite"),
    path("invite/accept/<slug:token>/", views.accept_invite, name="accept_invite"),

    # Page listing inventories you can view (your own + invited)
    path("inventories/", views.inventory_switcher, name="inventory_switcher"),
    
    path("settings/invite/<int:pk>/update/", views.update_invite, name="update_invite"),
    path("settings/invite/<int:pk>/purge/", views.purge_invite, name="purge_invite"),
    path("settings/reb/bootstrap/prepare/", views.reb_bootstrap_prepare, name="reb_bootstrap_prepare"),
    path("settings/reb/bootstrap/run/",     views.reb_bootstrap_run,     name="reb_bootstrap_run"),

    # Notes
    path("notes/", views.notes_list, name="notes_list"),
    path("notes/new/", views.note_create, name="note_create"),
    path("notes/<int:pk>/edit/", views.note_edit, name="note_edit"),
    path("notes/<int:pk>/delete/", views.note_delete, name="note_delete"),

    # Backups
    path("backups/trigger/full/", views.trigger_full_backup, name="trigger_full_backup"),
    path("backups/trigger/all-users/", views.trigger_all_user_backups, name="trigger_all_user_backups"),
    path("backups/trigger/my-inventory/", views.trigger_user_backup, name="trigger_user_backup"),
    path("backups/<int:backup_id>/download/", views.download_backup, name="download_backup"),
    path("backups/<int:backup_id>/delete/", views.delete_backup, name="delete_backup"),
    path("backups/list/user/", views.list_user_backups, name="list_user_backups"),
    path("backups/list/all/", views.list_all_backups, name="list_all_backups"),
]
