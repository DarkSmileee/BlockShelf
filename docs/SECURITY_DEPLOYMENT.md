# Security Features Deployment Guide

This guide provides step-by-step instructions for deploying the security features implemented in BlockShelf.

## Prerequisites

- BlockShelf already installed and running
- Database access (PostgreSQL recommended)
- Command line access to the server
- Admin access to Django

## Deployment Steps

### Step 1: Update Dependencies

Install the new security-related dependencies:

```bash
cd /path/to/BlockShelf

# Install python-magic and protobuf
pip install -r requirements.txt

# On Debian/Ubuntu, you may also need:
sudo apt-get install libmagic1
```

### Step 2: Update Environment Variables

Update your `.env` file with the new security settings (see `.env.example` for reference):

```bash
# Add these lines to your .env file
echo "
# Security Settings
ENABLE_RATE_LIMITING=True
RATE_LIMIT_LOGIN_ATTEMPTS=5
RATE_LIMIT_LOGIN_WINDOW=900
RATE_LIMIT_SIGNUP_ATTEMPTS=10
RATE_LIMIT_SIGNUP_WINDOW=3600
RATE_LIMIT_PASSWORD_RESET_ATTEMPTS=3
RATE_LIMIT_PASSWORD_RESET_WINDOW=3600

ENABLE_ACCOUNT_LOCKOUT=True
LOGIN_ATTEMPT_LIMIT=5
LOCKOUT_DURATION_MINUTES=15

SHARE_LINK_DEFAULT_EXPIRY_DAYS=30
ENABLE_SECURITY_LOGGING=True
" >> .env
```

### Step 3: Create Database Migrations

Generate and apply database migrations for the new `LoginAttempt` model:

```bash
# Create migrations
python manage.py makemigrations inventory

# Review the migration file
ls inventory/migrations/

# Apply migrations
python manage.py migrate
```

**Expected Migration:**
The migration should create a new `inventory_loginattempt` table with:
- username (CharField, indexed)
- ip_address (GenericIPAddressField)
- user_agent (CharField)
- success (BooleanField)
- timestamp (DateTimeField, indexed)
- failure_reason (CharField)

### Step 4: Create Cache Table (for Rate Limiting)

BlockShelf uses database-backed caching for rate limiting:

```bash
python manage.py createcachetable
```

This creates a `django_cache` table for storing rate limit data.

### Step 5: Create Logs Directory

Ensure the logs directory exists with proper permissions:

```bash
mkdir -p logs
chmod 755 logs

# If running with a specific user (e.g., www-data)
chown www-data:www-data logs
```

### Step 6: Update Nginx Configuration

If using nginx, reload the configuration to apply the new security headers:

```bash
# Test nginx configuration
nginx -t

# If test passes, reload nginx
systemctl reload nginx
```

### Step 7: Restart Application

Restart the Django application to load new code:

```bash
# If using systemd
systemctl restart blockshelf

# If using Docker
docker-compose restart web

# If using Gunicorn directly
pkill -HUP gunicorn
```

### Step 8: Verify Installation

Run Django's security checks:

```bash
python manage.py check --deploy
```

Check that all security features are working:

```bash
# Check if cache table exists
python manage.py shell -c "from django.core.cache import cache; cache.set('test', 1); print('Cache OK')"

# Check if LoginAttempt model exists
python manage.py shell -c "from inventory.models import LoginAttempt; print('LoginAttempt model OK')"

# Check logs directory
ls -la logs/
```

### Step 9: Test Security Features

#### Test Rate Limiting

Try logging in with wrong credentials 6 times in a row. You should:
1. Be allowed 5 attempts
2. Be blocked on the 6th attempt
3. See a countdown timer for when you can try again

#### Test Account Lockout

1. Fail login 5 times
2. Check Django admin at `/admin/inventory/loginattempt/`
3. Verify login attempts are recorded
4. Try clearing attempts and logging in again

#### Test Security Headers

```bash
curl -I https://your-domain.com/
```

Verify you see these headers:
- `Content-Security-Policy`
- `X-Frame-Options: SAMEORIGIN`
- `X-Content-Type-Options: nosniff`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy`

## Rollback Instructions

If you need to rollback the security features:

### Rollback Migrations

```bash
# List migrations
python manage.py showmigrations inventory

# Rollback to previous migration (replace XXXX with migration number)
python manage.py migrate inventory XXXX

# Example:
python manage.py migrate inventory 0042_previous_migration
```

### Remove Security Settings

Remove the security settings from `.env`:

```bash
# Edit .env and remove the security section
nano .env
```

### Restore Previous Nginx Config

```bash
# Restore backup if you created one
cp nginx/conf.d/blockshelf.conf.bak nginx/conf.d/blockshelf.conf

# Or manually remove the security headers from the config
nano nginx/conf.d/blockshelf.conf

# Reload nginx
nginx -t && systemctl reload nginx
```

## Monitoring Post-Deployment

### Check Logs

```bash
# Monitor authentication events
tail -f logs/auth.log

# Monitor security events
tail -f logs/security.log

# Check for errors in Django logs
journalctl -u blockshelf -f
```

### Monitor Login Attempts

Access Django admin regularly to review login attempts:

1. Navigate to `/admin/inventory/loginattempt/`
2. Filter by failed attempts
3. Look for patterns (same IP, same username, etc.)
4. Take action if suspicious activity is detected

### Performance Monitoring

Monitor database and cache performance:

```bash
# Check database size
python manage.py dbshell -c "SELECT pg_size_pretty(pg_database_size(current_database()));"

# Check cache table size
python manage.py dbshell -c "SELECT COUNT(*) FROM django_cache;"

# Clean old cache entries (automatically handled by Django, but can be forced)
python manage.py shell -c "from django.core.cache import cache; cache.clear()"
```

## Maintenance

### Regular Tasks

**Daily:**
- Check security logs for anomalies
- Review failed login attempts

**Weekly:**
- Run security vulnerability check: `./scripts/check_security.sh`
- Clean up old LoginAttempt records (older than 90 days)

**Monthly:**
- Review and update dependencies
- Check for Dependabot PRs
- Review CSP policy effectiveness
- Rotate credentials if necessary

### Cleaning Old Data

Create a Django management command to clean old login attempts:

```bash
python manage.py shell
```

```python
from inventory.models import LoginAttempt
from django.utils import timezone
from datetime import timedelta

# Delete login attempts older than 90 days
cutoff = timezone.now() - timedelta(days=90)
deleted = LoginAttempt.objects.filter(timestamp__lt=cutoff).delete()
print(f"Deleted {deleted[0]} old login attempts")
```

## Troubleshooting

### Issue: Migrations Fail

**Error**: `Table 'inventory_loginattempt' already exists`

**Solution**: The table may have been created manually. You can fake the migration:
```bash
python manage.py migrate inventory --fake
```

### Issue: Cache Not Working

**Error**: Rate limiting not working

**Solution**: Ensure cache table exists:
```bash
python manage.py createcachetable
python manage.py shell -c "from django.core.cache import cache; cache.set('test', 1); print(cache.get('test'))"
```

### Issue: Logs Not Being Created

**Error**: Security logs not appearing

**Solution**: Check permissions and directory existence:
```bash
mkdir -p logs
chmod 755 logs
chown www-data:www-data logs  # Use your app user
```

### Issue: All Users Getting Rate Limited

**Error**: Users behind proxy/NAT all share same IP

**Solution**: Configure X-Forwarded-For header in nginx and ensure Django trusts it:
```python
# settings.py
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
```

### Issue: CSP Blocking Functionality

**Error**: Features not working due to CSP

**Solution**:
1. Check browser console for CSP violations
2. Adjust CSP policy in nginx config if needed
3. Use CSP report-only mode for testing:
```nginx
add_header Content-Security-Policy-Report-Only "..." always;
```

## Security Hardening Checklist

After deployment, verify these security measures:

- [ ] HTTPS enabled (if applicable)
- [ ] DEBUG=False in production
- [ ] Strong SECRET_KEY set
- [ ] Database credentials secured
- [ ] Rate limiting active and tested
- [ ] Account lockout functional
- [ ] CSP headers present
- [ ] Security logging enabled
- [ ] Logs directory secured (not web-accessible)
- [ ] Dependencies up to date
- [ ] Dependabot enabled
- [ ] Admin panel secured (strong passwords, 2FA if available)
- [ ] Regular backups configured
- [ ] Monitoring in place

## Support

If you encounter issues during deployment:

1. Check the logs: `logs/auth.log` and `logs/security.log`
2. Run: `python manage.py check --deploy`
3. Review the main security documentation: `docs/SECURITY.md`
4. Check Django admin for login attempt records
5. Open an issue on GitHub with:
   - Deployment environment (Docker, systemd, etc.)
   - Python and Django versions
   - Error messages from logs
   - Steps to reproduce

## Next Steps

After successful deployment:

1. **Monitor** - Watch logs for first few days
2. **Test** - Have users test login flows
3. **Adjust** - Fine-tune rate limits based on usage
4. **Document** - Update your runbook with any customizations
5. **Train** - Educate admins on using the security features

For detailed usage and administration, see `docs/SECURITY.md`.
