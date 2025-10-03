# Generated manually for backup system

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('inventory', '0015_rename_inventory_n_user_id_7a8b9c_idx_inventory_n_user_id_f5c060_idx'),
    ]

    operations = [
        migrations.CreateModel(
            name='Backup',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('backup_type', models.CharField(choices=[('full_db', 'Full Database'), ('user_inventory', 'User Inventory')], max_length=20)),
                ('file_path', models.CharField(help_text='Path to backup file relative to MEDIA_ROOT', max_length=500)),
                ('file_size', models.BigIntegerField(help_text='File size in bytes')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('is_scheduled', models.BooleanField(default=False, help_text='True if created by scheduled task, False if manual')),
                ('created_by', models.ForeignKey(help_text='User who triggered the backup', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='backups_created', to=settings.AUTH_USER_MODEL)),
                ('user', models.ForeignKey(blank=True, help_text='User for inventory backups (null for full DB backups)', null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='backup',
            index=models.Index(fields=['backup_type', '-created_at'], name='inventory_b_backup_t_8a1b2c_idx'),
        ),
        migrations.AddIndex(
            model_name='backup',
            index=models.Index(fields=['user', '-created_at'], name='inventory_b_user_id_3d4e5f_idx'),
        ),
    ]
