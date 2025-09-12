from django.db import migrations, models
from django.conf import settings

class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0002_userpreference'),
    ]

    operations = [
        migrations.CreateModel(
            name='InventoryShare',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token', models.SlugField(max_length=64, unique=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='inventory_shares', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddIndex(
            model_name='inventoryshare',
            index=models.Index(fields=['user', 'is_active'], name='inventory_user_is_active_idx'),
        ),
    ]
