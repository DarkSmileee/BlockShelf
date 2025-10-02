# Generated migration for data integrity constraints

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0009_add_performance_indexes'),
    ]

    operations = [
        # Add revoked_at field to InventoryShare
        migrations.AddField(
            model_name='inventoryshare',
            name='revoked_at',
            field=models.DateTimeField(blank=True, help_text='When the share was revoked', null=True),
        ),
        # Add revoked_at field to InventoryCollab
        migrations.AddField(
            model_name='inventorycollab',
            name='revoked_at',
            field=models.DateTimeField(blank=True, help_text='When the collaboration was revoked', null=True),
        ),
        # Add index for revoked_at on InventoryShare
        migrations.AddIndex(
            model_name='inventoryshare',
            index=models.Index(fields=['revoked_at'], name='inventory_i_revoked_share_idx'),
        ),
        # Add index for revoked_at on InventoryCollab
        migrations.AddIndex(
            model_name='inventorycollab',
            index=models.Index(fields=['revoked_at'], name='inventory_i_revoked_collab_idx'),
        ),
        # Add unique constraint on (user, part_id, color) for InventoryItem
        migrations.AddConstraint(
            model_name='inventoryitem',
            constraint=models.UniqueConstraint(
                fields=['user', 'part_id', 'color'],
                name='unique_user_part_color'
            ),
        ),
        # Add check constraint for quantity_used <= quantity_total
        migrations.AddConstraint(
            model_name='inventoryitem',
            constraint=models.CheckConstraint(
                check=models.Q(quantity_used__lte=models.F('quantity_total')),
                name='quantity_used_lte_total'
            ),
        ),
    ]
