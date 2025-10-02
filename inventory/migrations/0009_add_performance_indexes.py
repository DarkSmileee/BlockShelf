# Generated manually for database performance improvements

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0008_inventoryshare_tracking'),
    ]

    operations = [
        # Add index for storage_location (search/filtering)
        migrations.AddIndex(
            model_name='inventoryitem',
            index=models.Index(fields=['storage_location'], name='inventory_i_storage_idx'),
        ),
        # Add index for name (search queries)
        migrations.AddIndex(
            model_name='inventoryitem',
            index=models.Index(fields=['name'], name='inventory_i_name_idx'),
        ),
        # Add index for created_at (date sorting)
        migrations.AddIndex(
            model_name='inventoryitem',
            index=models.Index(fields=['created_at'], name='inventory_i_created_idx'),
        ),
        # Add index for updated_at (date sorting)
        migrations.AddIndex(
            model_name='inventoryitem',
            index=models.Index(fields=['updated_at'], name='inventory_i_updated_idx'),
        ),
        # Add composite index for user + name (common user inventory views)
        migrations.AddIndex(
            model_name='inventoryitem',
            index=models.Index(fields=['user', 'name'], name='inventory_i_user_na_idx'),
        ),
    ]
