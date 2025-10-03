# Generated migration to fix index names
# This migration handles the transition from auto-generated index names to explicit names

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0016_backup'),
    ]

    operations = [
        # Drop old indexes if they exist, create new ones with explicit names
        # We use RunSQL with IF EXISTS to make this migration idempotent

        migrations.RunSQL(
            # Forward: Drop old indexes (if exist) and create new named indexes
            sql=[
                # InventoryItem indexes
                "DROP INDEX IF EXISTS inventory_i_storage_idx;",
                "DROP INDEX IF EXISTS inventory_i_storage_467982_idx;",
                "CREATE INDEX IF NOT EXISTS inventory_storage_loc_idx ON inventory_inventoryitem (storage_location);",

                "DROP INDEX IF EXISTS inventory_i_name_idx;",
                "DROP INDEX IF EXISTS inventory_i_name_9b5824_idx;",
                "CREATE INDEX IF NOT EXISTS inventory_name_idx ON inventory_inventoryitem (name);",

                "DROP INDEX IF EXISTS inventory_i_created_idx;",
                "DROP INDEX IF EXISTS inventory_i_created_c50f70_idx;",
                "CREATE INDEX IF NOT EXISTS inventory_created_at_idx ON inventory_inventoryitem (created_at);",

                "DROP INDEX IF EXISTS inventory_i_updated_idx;",
                "DROP INDEX IF EXISTS inventory_i_updated_056069_idx;",
                "CREATE INDEX IF NOT EXISTS inventory_updated_at_idx ON inventory_inventoryitem (updated_at);",

                "DROP INDEX IF EXISTS inventory_i_user_na_idx;",
                "DROP INDEX IF EXISTS inventory_i_user_id_cd9f80_idx;",
                "CREATE INDEX IF NOT EXISTS inventory_user_name_idx ON inventory_inventoryitem (user_id, name);",

                # RBElement indexes
                "DROP INDEX IF EXISTS inventory_r_part_id_abc123_idx;",
                "DROP INDEX IF EXISTS inventory_r_part_id_def456_idx;",
                "CREATE INDEX IF NOT EXISTS rbelement_part_color_idx ON inventory_rbelement (part_id, color_id);",

                # Note indexes
                "DROP INDEX IF EXISTS inventory_n_user_id_xyz789_idx;",
                "DROP INDEX IF EXISTS inventory_n_user_id_789abc_idx;",
                "CREATE INDEX IF NOT EXISTS note_user_updated_idx ON inventory_note (user_id, updated_at DESC);",

                # InventoryShare indexes
                "DROP INDEX IF EXISTS inventory_i_token_i_abc123_idx;",
                "DROP INDEX IF EXISTS inventory_i_token_4f0a2f_idx;",
                "CREATE INDEX IF NOT EXISTS invshare_token_active_idx ON inventory_inventoryshare (token, is_active);",

                "DROP INDEX IF EXISTS inventory_i_revoked_share_idx;",
                "DROP INDEX IF EXISTS inventory_i_revoked_f791eb_idx;",
                "CREATE INDEX IF NOT EXISTS invshare_revoked_idx ON inventory_inventoryshare (revoked_at);",

                "DROP INDEX IF EXISTS inventory_i_user_active_idx;",
                "CREATE INDEX IF NOT EXISTS invshare_user_active_idx ON inventory_inventoryshare (user_id, is_active);",

                # InventoryCollab indexes
                "DROP INDEX IF EXISTS inventory_i_revoked_collab_idx;",
                "DROP INDEX IF EXISTS inventory_i_revoked_4aabe3_idx;",
                "CREATE INDEX IF NOT EXISTS invcollab_revoked_idx ON inventory_inventorycollab (revoked_at);",

                "DROP INDEX IF EXISTS inventory_i_owner_collab_idx;",
                "DROP INDEX IF EXISTS inventory_i_owner_c_123456_idx;",
                "CREATE INDEX IF NOT EXISTS invcollab_owner_collab_idx ON inventory_inventorycollab (owner_id, collaborator_id, is_active);",

                # Backup indexes
                "DROP INDEX IF EXISTS inventory_b_backup_t_8a1b2c_idx;",
                "DROP INDEX IF EXISTS inventory_b_backup__07204c_idx;",
                "CREATE INDEX IF NOT EXISTS backup_type_created_idx ON inventory_backup (backup_type, created_at DESC);",

                "DROP INDEX IF EXISTS inventory_b_user_id_3d4e5f_idx;",
                "DROP INDEX IF EXISTS inventory_b_user_id_f4e693_idx;",
                "CREATE INDEX IF NOT EXISTS backup_user_created_idx ON inventory_backup (user_id, created_at DESC);",
            ],
            reverse_sql=[
                # Reverse: just drop the new indexes (we don't recreate old ones)
                "DROP INDEX IF EXISTS inventory_storage_loc_idx;",
                "DROP INDEX IF EXISTS inventory_name_idx;",
                "DROP INDEX IF EXISTS inventory_created_at_idx;",
                "DROP INDEX IF EXISTS inventory_updated_at_idx;",
                "DROP INDEX IF EXISTS inventory_user_name_idx;",
                "DROP INDEX IF EXISTS rbelement_part_color_idx;",
                "DROP INDEX IF EXISTS note_user_updated_idx;",
                "DROP INDEX IF EXISTS invshare_token_active_idx;",
                "DROP INDEX IF EXISTS invshare_revoked_idx;",
                "DROP INDEX IF EXISTS invshare_user_active_idx;",
                "DROP INDEX IF EXISTS invcollab_revoked_idx;",
                "DROP INDEX IF EXISTS invcollab_owner_collab_idx;",
                "DROP INDEX IF EXISTS backup_type_created_idx;",
                "DROP INDEX IF EXISTS backup_user_created_idx;",
            ],
        ),
    ]
