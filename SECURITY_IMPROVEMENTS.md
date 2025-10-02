# BlockShelf Security Improvements

This document outlines the critical security enhancements implemented to improve the security posture of the BlockShelf application.

## Summary of Changes

All **critical security fixes** from the security audit have been implemented:

### ✅ 1. Invite Token Exposure (FIXED)
**Issue**: Invite tokens were fully visible in the settings UI, allowing anyone with temporary screen access to copy invite links.

**Solution**:
- Obfuscated invite tokens in the UI (shows only last 8 characters: `•••••••••••••abc12345`)
- Added secure copy button with visual feedback
- Full URL only accessible via clipboard copy
- Location: `templates/inventory/settings.html` (lines 337-355)

### ✅ 2. File Upload Size Limits (FIXED)
**Issue**: No file size validation could lead to DoS attacks through memory exhaustion.

**Solution**:
- Added `DATA_UPLOAD_MAX_MEMORY_SIZE` = 10MB for CSV/Excel imports
- Added `FILE_UPLOAD_MAX_MEMORY_SIZE` = 10MB default
- Added `MAX_UPLOAD_SIZE` = 50MB for Rebrickable ZIP files
- Server-side validation in forms and views
- Location: `blockshelf_inventory/settings.py` (lines 198-201), `inventory/forms.py` (lines 50-68), `inventory/views.py` (lines 810-818)

### ✅ 3. External API Data Sanitization (FIXED)
**Issue**: HTML scraped from BrickLink and data from Rebrickable API was stored without sanitization, risking XSS attacks.

**Solution**:
- Added `bleach>=6.0` dependency for HTML sanitization
- Created `sanitize_text()` and `sanitize_url()` utility functions
- Applied sanitization to all BrickLink scraped data
- Applied sanitization to all Rebrickable API responses
- Limits text length to 10,000 characters to prevent DoS
- Only allows http/https protocols in URLs
- Location: `requirements.txt` (line 11), `inventory/utils.py` (lines 7-82), `inventory/views.py` (multiple locations)

### ✅ 4. Collaborator Permission Escalation (FIXED)
**Issue**: When accepting duplicate invites, permissions were OR'd together, potentially granting unintended elevated permissions.

**Solution**:
- Changed logic to use NEW invite's permissions only (not OR logic)
- Owner must revoke old invite and create new one to change permissions
- Added informative message to user when permissions are updated
- Location: `inventory/views.py` (lines 1252-1259)

### ✅ 5. Share Link Expiration & Access Tracking (FIXED)
**Issue**: Share links had no expiration, access limits, or tracking, allowing unlimited unmonitored access.

**Solution**:
- Added optional `expires_at` field for time-based expiration
- Added `access_count` to track number of accesses
- Added `last_accessed_at` to record last access time
- Added optional `max_access_count` for access-based limits
- Auto-deactivates expired links on access attempt
- Shows statistics in settings UI (created date, access count, last access)
- Created expired share template with user-friendly message
- Location: `inventory/models.py` (lines 122-151), `inventory/views.py` (lines 1134-1144), `templates/inventory/share_expired.html`, `templates/inventory/settings.html` (lines 235-252)

### ✅ 6. IP-based Rate Limiting (FIXED)
**Issue**: Rate limiting only checked user ID, allowing bypass via multiple accounts or cookie clearing.

**Solution**:
- Added dual rate limiting: per-user (60/min) AND per-IP (120/min)
- IP extraction handles reverse proxy headers (`X-Forwarded-For`, `X-Real-IP`)
- Both limits must pass for request to succeed
- Prevents abuse from shared IPs while maintaining security
- Location: `inventory/views.py` (lines 241-296)

## Database Migrations Required

After pulling these changes, run:

```bash
python manage.py migrate
```

This will apply migration `0008_inventoryshare_tracking` which adds:
- `expires_at` (DateTimeField, nullable)
- `access_count` (PositiveIntegerField, default=0)
- `last_accessed_at` (DateTimeField, nullable)
- `max_access_count` (PositiveIntegerField, nullable)
- Index on `(token, is_active)` for faster lookups

## Dependencies Added

```bash
pip install -r requirements.txt
```

New dependency:
- `bleach>=6.0` - HTML sanitization library

## Configuration Changes

### Environment Variables (Optional)

These can be added to your `.env` file to customize limits:

```bash
# File upload limits (bytes)
DATA_UPLOAD_MAX_MEMORY_SIZE=10485760  # 10MB
FILE_UPLOAD_MAX_MEMORY_SIZE=10485760  # 10MB
MAX_UPLOAD_SIZE=52428800              # 50MB
```

### Rate Limiting Constants

Located in `inventory/views.py` (lines 241-243):
- `LOOKUP_LIMIT_PER_MIN = 60` - Max API lookups per user per minute
- `LOOKUP_LIMIT_PER_IP = 120` - Max API lookups per IP per minute
- `LOOKUP_WINDOW_SECONDS = 60` - Rate limit window

Adjust these values based on your needs and API quotas.

## Security Best Practices Implemented

1. **Defense in Depth**: Multiple layers of validation (client-side hints, server-side enforcement, database constraints)
2. **Principle of Least Privilege**: Permissions default to most restrictive, explicit grants required
3. **Input Validation**: All external data sanitized before storage
4. **Output Encoding**: HTML/URL sanitization prevents XSS
5. **Rate Limiting**: Both user and IP-based to prevent abuse
6. **Audit Trail**: Access tracking for shared links
7. **Secure Defaults**: All security features enabled by default

## Testing Recommendations

After deployment, verify:

1. **Invite Tokens**: Check that tokens are obfuscated in settings UI
2. **File Uploads**: Try uploading files >10MB, should be rejected
3. **External Data**: Verify scraped names don't contain HTML tags
4. **Permissions**: Accept duplicate invite, verify permissions update correctly
5. **Share Links**: Access shared inventory multiple times, verify counter increments
6. **Rate Limits**: Make 61+ API lookups in one minute, should be blocked

## Rollback Plan

If issues arise, you can rollback the database migration:

```bash
python manage.py migrate inventory 0007_appconfig
```

Note: This will drop the new `InventoryShare` fields, so any tracking data will be lost.

## Future Security Enhancements (Recommended)

These were identified in the audit but not yet implemented (medium priority):

1. **Audit Logging**: Track who deleted items, when shares were accessed
2. **Email Notifications**: Alert owners when share links are accessed
3. **CAPTCHA**: Add to registration/login to prevent automated attacks
4. **2FA Support**: Multi-factor authentication for sensitive accounts
5. **Content Security Policy**: HTTP headers to prevent XSS
6. **Subresource Integrity**: Verify CDN resources haven't been tampered with

## Support

For questions or issues related to these security improvements:
- Open an issue on GitHub
- Review the original security audit document
- Check Django security documentation: https://docs.djangoproject.com/en/stable/topics/security/

---

**Last Updated**: 2025-10-02
**Version**: 1.0
**Implemented By**: Security Audit Response Team
