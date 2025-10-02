# Generated migration to add items_per_page and rebrickable_api_key to UserPreference
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0011_remove_appconfig_rebrickable_key'),
    ]

    operations = [
        migrations.AddField(
            model_name='userpreference',
            name='items_per_page',
            field=models.PositiveIntegerField(default=25),
        ),
        migrations.AddField(
            model_name='userpreference',
            name='rebrickable_api_key',
            field=models.CharField(blank=True, max_length=80),
        ),
    ]
