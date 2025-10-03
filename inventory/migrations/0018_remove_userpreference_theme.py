# Generated migration to remove theme field from UserPreference

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0017_fix_index_names'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='userpreference',
            name='theme',
        ),
    ]
