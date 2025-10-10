# BlockShelf Security Features

This document describes the security features implemented in BlockShelf for self-hosted deployments.

## Table of Contents

1. [Overview](#overview)
2. [Critical Security Features](#critical-security-features)
3. [High Priority Security Features](#high-priority-security-features)
4. [Medium Priority Security Features](#medium-priority-security-features)
5. [Configuration](#configuration)
6. [Monitoring & Logging](#monitoring--logging)
7. [Administration](#administration)
8. [Testing](#testing)

## Overview

BlockShelf implements comprehensive security measures specifically designed for self-hosted environments. All security features are server-side implementations that don't require external services.

## Critical Security Features

### 1. Rate Limiting on Authentication Endpoints

**Purpose**: Prevents brute force attacks on authentication endpoints.

**Implementation**:
- Django cache-based rate limiting (no external dependencies)
- Configurable attempt limits and time windows
- Progressive lockout with increasing delays
- Per-IP address tracking

**Configuration** (`.env`):
```env
ENABLE_RATE_LIMITING=True
RATE_LIMIT_LOGIN_ATTEMPTS=5
RATE_LIMIT_LOGIN_WINDOW=900  # 15 minutes
RATE_LIMIT_SIGNUP_ATTEMPTS=10
RATE_LIMIT_SIGNUP_WINDOW=3600  # 1 hour
```

**Protected Endpoints**:
- Login: 5 attempts per 15 minutes
- Signup: 10 attempts per hour
- Password Reset: 3 attempts per hour

**User Experience**:
- Users exceeding limits see a countdown timer
- Clear error messages with retry time
- Progressive delays: 5min → 15min → 1hr → 24hr

**Files**:
- `inventory/decorators/rate_limit.py` - Rate limiting decorator
- `inventory/views/auth.py` - Protected authentication views
- `templates/errors/rate_limit.html` - User-friendly error page

### 2. Content Security Policy (CSP) Headers

**Purpose**: Prevents XSS (Cross-Site Scripting) attacks.

**Implementation**:
- Comprehensive CSP headers in nginx configuration
- Strict default policies with necessary exceptions
- Prevents inline script execution from untrusted sources

**CSP Policy**:
```nginx
Content-Security-Policy: default-src 'self';
    script-src 'self' 'unsafe-inline';
    style-src 'self' 'unsafe-inline';
    img-src 'self' data: https:;
    connect-src 'self';
    font-src 'self' data:;
    object-src 'none';
    base-uri 'self';
    form-action 'self';
    frame-ancestors 'self';
```

**Additional Security Headers**:
- `X-Frame-Options: SAMEORIGIN` - Prevents clickjacking
- `X-Content-Type-Options: nosniff` - Prevents MIME type sniffing
- `Referrer-Policy: strict-origin-when-cross-origin` - Controls referrer information
- `Permissions-Policy` - Restricts browser features (camera, microphone, etc.)
- `X-Permitted-Cross-Domain-Policies: none` - Blocks cross-domain policies

**Files**:
- `nginx/conf.d/blockshelf.conf` - Security headers configuration

### 3. Account Lockout After Failed Login Attempts

**Purpose**: Protects user accounts from brute force attacks.

**Implementation**:
- Database-tracked login attempts
- Progressive lockout schedule based on failure count
- Admin interface for managing lockouts
- Detailed logging of all authentication attempts

**Lockout Schedule**:
- 5-9 failures: 5 minutes lockout
- 10-14 failures: 15 minutes lockout
- 15-19 failures: 1 hour lockout
- 20+ failures: 24 hours lockout

**Configuration** (`.env`):
```env
ENABLE_ACCOUNT_LOCKOUT=True
LOGIN_ATTEMPT_LIMIT=5
LOCKOUT_DURATION_MINUTES=15
```

**Admin Features**:
- View all login attempts in Django admin
- Filter by success/failure, username, IP address
- Clear failed attempts to unlock accounts
- Search and date filtering

**Files**:
- `inventory/models.py` - `LoginAttempt` model
- `inventory/views/auth.py` - Login view with lockout logic
- `inventory/admin.py` - Admin interface for login attempts

## High Priority Security Features

### 4. Row Level Security (RLS) Policies

**Status**: Documentation provided, implementation requires PostgreSQL migration.

**Purpose**: Database-level data isolation to ensure users can only access their own data.

**Implementation Guide**:

Create a PostgreSQL migration:

```sql
-- Enable RLS on user-owned tables
ALTER TABLE inventory_inventoryitem ENABLE ROW LEVEL SECURITY;
ALTER TABLE inventory_note ENABLE ROW LEVEL SECURITY;
ALTER TABLE inventory_inventoryshare ENABLE ROW LEVEL SECURITY;
ALTER TABLE inventory_inventorycollab ENABLE ROW LEVEL SECURITY;

-- Create policies
CREATE POLICY user_inventory_policy ON inventory_inventoryitem
FOR ALL TO PUBLIC
USING (user_id = current_setting('app.current_user_id')::integer);

CREATE POLICY user_note_policy ON inventory_note
FOR ALL TO PUBLIC
USING (user_id = current_setting('app.current_user_id')::integer);

CREATE POLICY user_share_policy ON inventory_inventoryshare
FOR ALL TO PUBLIC
USING (user_id = current_setting('app.current_user_id')::integer);

CREATE POLICY user_collab_policy ON inventory_inventorycollab
FOR ALL TO PUBLIC
USING (owner_id = current_setting('app.current_user_id')::integer
    OR collaborator_id = current_setting('app.current_user_id')::integer);
```

**Note**: RLS requires setting the current user ID in the PostgreSQL session context. This can be implemented in Django middleware.

### 5. Dependency Security

**Purpose**: Keep dependencies secure and up-to-date.

**Implementation**:
- Added missing `protobuf>=4.24.0` dependency
- GitHub Dependabot configuration for automated updates
- Security checking script using `pip-audit`

**Usage**:
```bash
# Check for vulnerabilities
./scripts/check_security.sh

# Or manually
pip install pip-audit
pip-audit --requirement requirements.txt
```

**Files**:
- `.github/dependabot.yml` - Automated dependency updates
- `scripts/check_security.sh` - Security vulnerability scanner
- `requirements.txt` - Updated with secure versions

### 6. File Upload Security

**Purpose**: Prevent malicious file uploads and execution.

**Implementation**:
- Content-type validation using `python-magic`
- Strict file type allowlisting
- File size limits per type
- Content scanning for malicious patterns
- Filename sanitization

**Allowed File Types**:
- **Images**: JPG, PNG, GIF, WebP, BMP (max 10MB)
- **Spreadsheets**: XLS, XLSX, CSV (max 50MB)
- **Archives**: ZIP (max 50MB, for Rebrickable data)

**Blocked Patterns**:
- Executable files (`.exe`, `.dll`, `.bat`, `.sh`, etc.)
- Scripts (`.js`, `.php`, `.vbs`, etc.)
- Files with embedded script tags or PHP code

**Usage**:
```python
from inventory.file_validation import validate_upload

# In your view
try:
    validate_upload(file_obj, filename, allowed_categories=['image', 'spreadsheet'])
except ValidationError as e:
    # Handle error
    pass
```

**Files**:
- `inventory/file_validation.py` - Comprehensive file validation utilities

## Medium Priority Security Features

### 7. Additional Security Headers

**Purpose**: Defense-in-depth approach to prevent various attacks.

**Headers Added**:
- `Permissions-Policy` - Restricts browser features
- `X-Permitted-Cross-Domain-Policies` - Blocks cross-domain policies
- `Referrer-Policy` - Enhanced referrer control
- `HSTS` (HTTPS only) - Enforces HTTPS connections

**Files**:
- `nginx/conf.d/blockshelf.conf` - All security headers

### 8. Shared Inventory Token Security

**Purpose**: Secure inventory sharing with cryptographically strong tokens.

**Implementation**:
- Cryptographically secure tokens using `secrets.token_urlsafe(32)`
- Default 30-day expiration (configurable)
- Token rotation capability
- Access logging and tracking
- Max access count limits

**Configuration** (`.env`):
```env
SHARE_LINK_DEFAULT_EXPIRY_DAYS=30
```

**Features**:
- Automatic expiration after 30 days (default)
- Optional max access count
- Token rotation method for compromised tokens
- Access count tracking
- Last accessed timestamp

**Files**:
- `inventory/models.py` - `InventoryShare` model with secure tokens

### 9. Security Monitoring and Logging

**Purpose**: Track security events for monitoring and incident response.

**Implementation**:
- Structured logging with security event categories
- Separate log files for auth and security events
- Log rotation (10MB files, 5 backups)
- Configurable logging levels

**Log Files**:
- `logs/security.log` - Rate limit violations, security events
- `logs/auth.log` - Login attempts, authentication events

**Configuration** (`.env`):
```env
ENABLE_SECURITY_LOGGING=True
```

**Logged Events**:
- All authentication attempts (success/failure)
- Rate limit violations
- Account lockouts
- File upload attempts
- Shared inventory access
- Failed permission checks

**Files**:
- `blockshelf_inventory/settings.py` - Logging configuration

## Configuration

### Environment Variables

All security features can be configured via environment variables in `.env`:

```env
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
```

### Database Setup

After implementing security features, create migrations and apply them:

```bash
# Create migrations for new models
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Create database cache table (for rate limiting)
python manage.py createcachetable
```

## Monitoring & Logging

### Viewing Security Logs

```bash
# View recent authentication events
tail -f logs/auth.log

# View security events (rate limits, violations)
tail -f logs/security.log

# Search for failed login attempts
grep "FAILED" logs/auth.log

# Search for account lockouts
grep "locked" logs/auth.log
```

### Django Admin

Access the Django admin interface to:
- View all login attempts
- Clear failed attempts to unlock accounts
- Monitor user activity
- Review audit logs

Navigate to: `/admin/inventory/loginattempt/`

## Administration

### Unlocking User Accounts

**Method 1: Django Admin**
1. Go to `/admin/inventory/loginattempt/`
2. Select the user's failed login attempts
3. Choose "Clear failed attempts for selected users" from actions
4. Click "Go"

**Method 2: Django Shell**
```python
from inventory.models import LoginAttempt

# Clear all failed attempts for a username
LoginAttempt.clear_attempts('username')

# Check if account is locked
is_locked, time_remaining = LoginAttempt.is_account_locked('username')
print(f"Locked: {is_locked}, Time remaining: {time_remaining}s")
```

### Rotating Share Tokens

If a share token is compromised:

```python
from inventory.models import InventoryShare

# Get the share
share = InventoryShare.objects.get(token='old_token')

# Rotate to new secure token
share.rotate_token()
```

### Checking Security Status

```bash
# Run security vulnerability check
./scripts/check_security.sh

# Check nginx configuration
nginx -t

# View Django security checklist
python manage.py check --deploy
```

## Testing

### Testing Rate Limiting

```bash
# Test login rate limiting (will be blocked after 5 attempts)
for i in {1..10}; do
    curl -X POST http://localhost/login/ \
        -d "username=test&password=wrong" \
        -H "Content-Type: application/x-www-form-urlencoded"
done
```

### Testing Account Lockout

1. Attempt to login with wrong password 5+ times
2. Verify account is locked with appropriate message
3. Check Django admin for login attempts
4. Clear attempts and verify unlock

### Testing CSP Headers

```bash
# Check security headers
curl -I http://localhost/

# Look for:
# - Content-Security-Policy
# - X-Frame-Options
# - X-Content-Type-Options
# - Referrer-Policy
```

### Testing File Upload

```python
from inventory.file_validation import validate_upload
from django.core.files.uploadedfile import SimpleUploadedFile

# Test with a valid image
with open('test.jpg', 'rb') as f:
    validate_upload(f, 'test.jpg', ['image'])
    # Should succeed

# Test with invalid extension
with open('test.exe', 'rb') as f:
    validate_upload(f, 'test.exe', ['image'])
    # Should raise ValidationError
```

## Best Practices

1. **Keep Dependencies Updated**
   - Run `./scripts/check_security.sh` regularly
   - Review Dependabot PRs promptly
   - Apply security patches quickly

2. **Monitor Logs**
   - Review security logs weekly
   - Set up alerts for suspicious activity
   - Archive old logs for compliance

3. **Regular Security Audits**
   - Run `python manage.py check --deploy` before deployments
   - Review login attempts in admin regularly
   - Test security features after updates

4. **Backup Security**
   - Back up logs before rotation
   - Keep login attempt history
   - Document security incidents

5. **User Education**
   - Inform users about account lockouts
   - Provide contact for unlocking accounts
   - Encourage strong passwords

## Troubleshooting

### Rate Limiting Issues

**Problem**: Legitimate users getting rate limited

**Solutions**:
- Increase `RATE_LIMIT_LOGIN_ATTEMPTS`
- Increase `RATE_LIMIT_LOGIN_WINDOW`
- Clear cache: `python manage.py clear_cache`
- Check for shared IPs (proxies, NAT)

### Account Lockout Issues

**Problem**: Users locked out permanently

**Solutions**:
- Clear failed attempts in Django admin
- Reduce `LOGIN_ATTEMPT_LIMIT`
- Check for automated attacks
- Review security logs

### File Upload Issues

**Problem**: Valid files being rejected

**Solutions**:
- Check file MIME type: `file --mime-type filename`
- Verify file size limits in settings
- Check for corrupted files
- Review validation logs

### CSP Issues

**Problem**: Website features not working

**Solutions**:
- Check browser console for CSP violations
- Adjust CSP policy if needed
- Use CSP report-only mode for testing
- Whitelist necessary external resources

## Security Incident Response

1. **Detect**: Monitor logs for unusual activity
2. **Assess**: Determine severity and impact
3. **Contain**: Block attackers, lock accounts if needed
4. **Eradicate**: Clear malicious data, patch vulnerabilities
5. **Recover**: Restore normal operations
6. **Learn**: Document incident, improve defenses

## Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Django Security Documentation](https://docs.djangoproject.com/en/stable/topics/security/)
- [nginx Security Best Practices](https://www.nginx.com/blog/mitigating-ddos-attacks-with-nginx-and-nginx-plus/)

## Support

For security issues or questions:
1. Check this documentation
2. Review Django admin login attempts
3. Check security logs
4. Open an issue on GitHub (for non-sensitive issues)

**For security vulnerabilities, please report privately to the maintainers.**
