"""
Views package for the inventory application.

This package is organized into logical modules:
- inventory: CRUD operations for inventory items
- sharing: Share links and collaborator management
- api: API endpoints for lookups and imports
- settings: User settings and admin configuration
- helpers: Shared utilities and helper functions
"""

# Import all views to maintain backward compatibility with urls.py
from .inventory import (
    inventory_list,
    add_item,
    item_create,
    item_update,
    item_delete,
    export_csv,
    import_csv,
    check_duplicate,
)

from .sharing import (
    create_share_link,
    revoke_share_link,
    shared_inventory,
    inventory_switcher,
    create_invite,
    revoke_invite,
    accept_invite,
    update_invite,
    purge_invite,
)

from .api import (
    lookup_part,
    reb_bootstrap_prepare,
    reb_bootstrap_run,
    bulk_update_missing_preview,
    bulk_update_missing_batch,
)

from .settings import (
    settings_view,
    delete_all_inventory,
)

from .auth import (
    signup,
    set_theme,
)

from .errors import (
    error_404,
    error_500,
)

from .notes import (
    notes_list,
    note_create,
    note_edit,
    note_delete,
)

from .backups import (
    trigger_full_backup,
    trigger_all_user_backups,
    trigger_user_backup,
    download_backup,
    delete_backup,
    list_user_backups,
    list_all_backups,
    next_backup_time,
)

from .dashboard import (
    dashboard,
)

__all__ = [
    # Inventory
    'inventory_list',
    'add_item',
    'item_create',
    'item_update',
    'item_delete',
    'export_csv',
    'import_csv',
    'check_duplicate',
    # Sharing
    'create_share_link',
    'revoke_share_link',
    'shared_inventory',
    'inventory_switcher',
    'create_invite',
    'revoke_invite',
    'accept_invite',
    'update_invite',
    'purge_invite',
    # API
    'lookup_part',
    'reb_bootstrap_prepare',
    'reb_bootstrap_run',
    'bulk_update_missing_preview',
    'bulk_update_missing_batch',
    # Settings
    'settings_view',
    'delete_all_inventory',
    # Auth
    'signup',
    'set_theme',
    # Notes
    'notes_list',
    'note_create',
    'note_edit',
    'note_delete',
    # Backups
    'trigger_full_backup',
    'trigger_all_user_backups',
    'trigger_user_backup',
    'download_backup',
    'delete_backup',
    'list_user_backups',
    'list_all_backups',
    'next_backup_time',
    # Errors
    'error_404',
    'error_500',
    # Dashboard
    'dashboard',
]
