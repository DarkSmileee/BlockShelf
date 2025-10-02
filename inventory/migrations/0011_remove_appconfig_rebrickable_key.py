# Generated migration to remove rebrickable_api_key from AppConfig
from django.db import migrations
class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0010_add_data_integrity_constraints'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='appconfig',
            name='rebrickable_api_key',
        ),
    ]
