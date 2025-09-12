from django.db import migrations, models
from django.conf import settings
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0004_merge_20250905_1727'),
    ]

    operations = [
        migrations.CreateModel(
            name='InventoryCollab',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('invited_email', models.EmailField(blank=True, max_length=254)),
                ('token', models.SlugField(default=None, max_length=64, unique=True)),
                ('can_edit', models.BooleanField(default=True)),
                ('can_delete', models.BooleanField(default=False)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('accepted_at', models.DateTimeField(blank=True, null=True)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='owned_collabs', to=settings.AUTH_USER_MODEL)),
                ('collaborator', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='collabs', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddIndex(
            model_name='inventorycollab',
            index=models.Index(fields=['owner', 'collaborator', 'is_active'], name='inventory_owner_collab_active_idx'),
        ),
        migrations.AddConstraint(
            model_name='inventorycollab',
            constraint=models.UniqueConstraint(
                fields=('owner', 'collaborator'),
                condition=models.Q(('collaborator__isnull', False), ('is_active', True)),
                name='uniq_active_owner_collaborator',
            ),
        ),
    ]
