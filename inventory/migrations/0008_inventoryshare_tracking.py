# Generated migration for InventoryShare tracking fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0007_appconfig'),
    ]

    operations = [
        migrations.AddField(
            model_name='inventoryshare',
            name='expires_at',
            field=models.DateTimeField(blank=True, help_text='Optional expiration date', null=True),
        ),
        migrations.AddField(
            model_name='inventoryshare',
            name='access_count',
            field=models.PositiveIntegerField(default=0, help_text='Number of times this link has been accessed'),
        ),
        migrations.AddField(
            model_name='inventoryshare',
            name='last_accessed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='inventoryshare',
            name='max_access_count',
            field=models.PositiveIntegerField(blank=True, help_text='Optional maximum number of accesses', null=True),
        ),
        migrations.AddIndex(
            model_name='inventoryshare',
            index=models.Index(fields=['token', 'is_active'], name='inventory_i_token_i_abc123_idx'),
        ),
    ]
