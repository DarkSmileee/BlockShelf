# Initial migration for BlockShelf inventory app
# Generated to match current model state

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
import inventory.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Rebrickable catalog models
        migrations.CreateModel(
            name='RBColor',
            fields=[
                ('id', models.IntegerField(primary_key=True, serialize=False)),
                ('name', models.CharField(db_index=True, max_length=120)),
                ('rgb', models.CharField(blank=True, max_length=6)),
                ('is_trans', models.BooleanField(default=False)),
            ],
            options={
                'verbose_name': 'RB Color',
                'verbose_name_plural': 'RB Colors',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='RBPart',
            fields=[
                ('part_num', models.CharField(max_length=50, primary_key=True, serialize=False)),
                ('name', models.CharField(db_index=True, max_length=255)),
                ('part_cat_id', models.IntegerField(blank=True, null=True)),
                ('image_url', models.URLField(blank=True)),
            ],
            options={
                'verbose_name': 'RB Part',
                'verbose_name_plural': 'RB Parts',
                'ordering': ['part_num'],
            },
        ),
        migrations.CreateModel(
            name='RBElement',
            fields=[
                ('element_id', models.CharField(max_length=50, primary_key=True, serialize=False)),
                ('part', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='elements', to='inventory.rbpart')),
                ('color', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='elements', to='inventory.rbcolor')),
            ],
            options={
                'verbose_name': 'RB Element',
                'verbose_name_plural': 'RB Elements',
                'indexes': [
                    models.Index(fields=['part', 'color'], name='rbelement_part_color_idx'),
                ],
            },
        ),

        # User preferences
        migrations.CreateModel(
            name='UserPreference',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('items_per_page', models.PositiveIntegerField(default=25)),
                ('rebrickable_api_key', models.CharField(blank=True, max_length=80)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='userpreference', to=settings.AUTH_USER_MODEL)),
            ],
        ),

        # App configuration (singleton)
        migrations.CreateModel(
            name='AppConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('singleton_id', models.PositiveSmallIntegerField(default=1, editable=False, unique=True)),
                ('site_name', models.CharField(blank=True, default='BlockShelf', max_length=80)),
                ('items_per_page', models.PositiveIntegerField(default=25)),
                ('allow_registration', models.BooleanField(default=True)),
                ('default_from_email', models.EmailField(blank=True, max_length=254)),
            ],
            options={
                'verbose_name': 'App configuration',
                'verbose_name_plural': 'App configuration',
            },
        ),

        # Inventory items
        migrations.CreateModel(
            name='InventoryItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('part_id', models.CharField(db_index=True, max_length=100)),
                ('color', models.CharField(db_index=True, max_length=100)),
                ('quantity_total', models.IntegerField(default=0, validators=[django.core.validators.MinValueValidator(0)])),
                ('quantity_used', models.IntegerField(default=0, validators=[django.core.validators.MinValueValidator(0)])),
                ('storage_location', models.CharField(blank=True, max_length=100)),
                ('image_url', models.URLField(blank=True)),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='inventory_items', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['name', 'color', 'part_id'],
                'indexes': [
                    models.Index(fields=['user', 'part_id', 'color'], name='inventory_n_user_id_f5c060_idx'),
                    models.Index(fields=['storage_location'], name='inventory_storage_loc_idx'),
                    models.Index(fields=['name'], name='inventory_name_idx'),
                    models.Index(fields=['created_at'], name='inventory_created_at_idx'),
                    models.Index(fields=['updated_at'], name='inventory_updated_at_idx'),
                    models.Index(fields=['user', 'name'], name='inventory_user_name_idx'),
                ],
                'constraints': [
                    models.CheckConstraint(
                        check=models.Q(quantity_used__lte=models.F('quantity_total')),
                        name='quantity_used_lte_total',
                    ),
                    models.UniqueConstraint(
                        fields=['user', 'part_id', 'color'],
                        name='unique_user_part_color',
                    ),
                ],
            },
        ),

        # Notes
        migrations.CreateModel(
            name='Note',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('description', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notes', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-updated_at'],
                'indexes': [
                    models.Index(fields=['user', '-updated_at'], name='note_user_updated_idx'),
                ],
            },
        ),

        # Inventory shares
        migrations.CreateModel(
            name='InventoryShare',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token', models.SlugField(max_length=64, unique=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('expires_at', models.DateTimeField(blank=True, help_text='Optional expiration date', null=True)),
                ('revoked_at', models.DateTimeField(blank=True, help_text='When the share was revoked', null=True)),
                ('access_count', models.PositiveIntegerField(default=0, help_text='Number of times this link has been accessed')),
                ('last_accessed_at', models.DateTimeField(blank=True, null=True)),
                ('max_access_count', models.PositiveIntegerField(blank=True, help_text='Optional maximum number of accesses', null=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='inventory_shares', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'indexes': [
                    models.Index(fields=['user', 'is_active'], name='invshare_user_active_idx'),
                    models.Index(fields=['token', 'is_active'], name='invshare_token_active_idx'),
                    models.Index(fields=['revoked_at'], name='invshare_revoked_idx'),
                ],
            },
        ),

        # Inventory collaboration
        migrations.CreateModel(
            name='InventoryCollab',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('invited_email', models.EmailField(blank=True, max_length=254)),
                ('token', models.SlugField(default=inventory.models._invite_token, max_length=64, unique=True)),
                ('can_edit', models.BooleanField(default=True)),
                ('can_delete', models.BooleanField(default=False)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('accepted_at', models.DateTimeField(blank=True, null=True)),
                ('revoked_at', models.DateTimeField(blank=True, help_text='When the collaboration was revoked', null=True)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='owned_collabs', to=settings.AUTH_USER_MODEL)),
                ('collaborator', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='collabs', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'indexes': [
                    models.Index(fields=['owner', 'collaborator', 'is_active'], name='invcollab_owner_collab_idx'),
                    models.Index(fields=['revoked_at'], name='invcollab_revoked_idx'),
                ],
                'constraints': [
                    models.UniqueConstraint(
                        condition=models.Q(('collaborator__isnull', False), ('is_active', True)),
                        fields=['owner', 'collaborator'],
                        name='uniq_active_owner_collaborator',
                    ),
                ],
            },
        ),

        # Backup system
        migrations.CreateModel(
            name='Backup',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('backup_type', models.CharField(choices=[('full_db', 'Full Database'), ('user_inventory', 'User Inventory')], max_length=20)),
                ('file_path', models.CharField(help_text='Path to backup file relative to MEDIA_ROOT', max_length=500)),
                ('file_size', models.BigIntegerField(help_text='File size in bytes')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('is_scheduled', models.BooleanField(default=False, help_text='True if created by scheduled task, False if manual')),
                ('user', models.ForeignKey(blank=True, help_text='User for inventory backups (null for full DB backups)', null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='backups_created', to=settings.AUTH_USER_MODEL, help_text='User who triggered the backup')),
            ],
            options={
                'ordering': ['-created_at'],
                'indexes': [
                    models.Index(fields=['backup_type', '-created_at'], name='backup_type_created_idx'),
                    models.Index(fields=['user', '-created_at'], name='backup_user_created_idx'),
                ],
            },
        ),
    ]
