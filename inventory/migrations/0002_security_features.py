# Generated migration for security features
# LoginAttempt model and InventoryShare token field updates

from django.conf import settings
from django.db import migrations, models
import secrets


def generate_secure_token():
    """Generate a cryptographically secure token."""
    return secrets.token_urlsafe(32)


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('inventory', '0001_initial'),
    ]

    operations = [
        # Create LoginAttempt model for security tracking
        migrations.CreateModel(
            name='LoginAttempt',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('username', models.CharField(db_index=True, help_text='Username attempted', max_length=150)),
                ('ip_address', models.GenericIPAddressField(help_text='IP address of the attempt')),
                ('user_agent', models.CharField(blank=True, help_text='User agent string', max_length=500)),
                ('success', models.BooleanField(default=False, help_text='Whether the login was successful')),
                ('timestamp', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('failure_reason', models.CharField(blank=True, help_text='Reason for failure', max_length=200)),
            ],
            options={
                'ordering': ['-timestamp'],
            },
        ),

        # Add indexes for LoginAttempt performance
        migrations.AddIndex(
            model_name='loginattempt',
            index=models.Index(fields=['username', '-timestamp'], name='login_username_time_idx'),
        ),
        migrations.AddIndex(
            model_name='loginattempt',
            index=models.Index(fields=['ip_address', '-timestamp'], name='login_ip_time_idx'),
        ),
        migrations.AddIndex(
            model_name='loginattempt',
            index=models.Index(fields=['success', '-timestamp'], name='login_success_time_idx'),
        ),

        # Update InventoryShare token field for cryptographic security
        # Changes from SlugField to CharField to support longer secure tokens
        migrations.AlterField(
            model_name='inventoryshare',
            name='token',
            field=models.CharField(db_index=True, default=generate_secure_token, max_length=64, unique=True),
        ),
    ]
