"""
File upload validation and security utilities.
Provides comprehensive file validation using python-magic for content-type checking.
Optional ClamAV integration for malware scanning.
"""

import logging
import magic
import os
import re
import subprocess
from django.conf import settings
from django.core.exceptions import ValidationError
from typing import BinaryIO, Optional, Tuple

logger = logging.getLogger(__name__)

# Allowed file types with their MIME types and extensions
ALLOWED_FILE_TYPES = {
    'image': {
        'mime_types': [
            'image/jpeg',
            'image/png',
            'image/gif',
            'image/webp',
            'image/bmp',
        ],
        'extensions': ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'],
        'max_size': 10 * 1024 * 1024,  # 10MB
    },
    'spreadsheet': {
        'mime_types': [
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'text/csv',
            'application/csv',
        ],
        'extensions': ['.xls', '.xlsx', '.csv'],
        'max_size': 50 * 1024 * 1024,  # 50MB
    },
    'archive': {
        'mime_types': [
            'application/zip',
            'application/x-zip-compressed',
        ],
        'extensions': ['.zip'],
        'max_size': 50 * 1024 * 1024,  # 50MB (for Rebrickable data)
    },
}

# Dangerous file patterns to block
DANGEROUS_PATTERNS = [
    r'\.exe$',
    r'\.dll$',
    r'\.bat$',
    r'\.cmd$',
    r'\.com$',
    r'\.pif$',
    r'\.scr$',
    r'\.vbs$',
    r'\.js$',
    r'\.jar$',
    r'\.sh$',
    r'\.app$',
    r'\.deb$',
    r'\.rpm$',
    r'\.dmg$',
    r'\.pkg$',
    r'\.bin$',
    r'<script',  # Block files with script tags
    r'<?php',    # Block PHP code
]


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent directory traversal and other attacks.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    # Remove path separators
    filename = os.path.basename(filename)

    # Remove any non-alphanumeric characters except dots, dashes, and underscores
    filename = re.sub(r'[^\w\s\-\.]', '', filename)

    # Replace spaces with underscores
    filename = filename.replace(' ', '_')

    # Limit filename length
    name, ext = os.path.splitext(filename)
    if len(name) > 100:
        name = name[:100]
    filename = name + ext

    return filename


def get_file_mime_type(file_obj: BinaryIO) -> str:
    """
    Get the actual MIME type of a file using python-magic.

    Args:
        file_obj: File object to check

    Returns:
        MIME type string
    """
    try:
        # Read first 2048 bytes for magic detection
        file_obj.seek(0)
        file_header = file_obj.read(2048)
        file_obj.seek(0)

        # Use python-magic to detect actual file type
        mime = magic.from_buffer(file_header, mime=True)
        return mime
    except Exception as e:
        logger.error(f"Error detecting file MIME type: {e}")
        return 'application/octet-stream'


def validate_file_type(filename: str, file_obj: BinaryIO, allowed_categories: Optional[list] = None) -> tuple[bool, str]:
    """
    Validate file type based on extension and actual content.

    Args:
        filename: Original filename
        file_obj: File object to validate
        allowed_categories: List of allowed file categories (e.g., ['image', 'spreadsheet'])

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Default to all categories if not specified
    if allowed_categories is None:
        allowed_categories = list(ALLOWED_FILE_TYPES.keys())

    # Get file extension
    _, ext = os.path.splitext(filename.lower())

    # Check for dangerous patterns
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, filename.lower()) or re.search(pattern, ext):
            return False, f"File type not allowed: {ext}"

    # Check if extension is in allowed list
    extension_valid = False
    mime_valid = False
    category_found = None

    for category in allowed_categories:
        if category not in ALLOWED_FILE_TYPES:
            continue

        config = ALLOWED_FILE_TYPES[category]

        # Check extension
        if ext in config['extensions']:
            extension_valid = True
            category_found = category

            # Check actual MIME type
            detected_mime = get_file_mime_type(file_obj)

            if detected_mime in config['mime_types']:
                mime_valid = True
                break

    if not extension_valid:
        return False, f"File extension {ext} not allowed. Allowed extensions: {', '.join([ext for cat in ALLOWED_FILE_TYPES.values() for ext in cat['extensions']])}"

    if not mime_valid:
        logger.warning(f"File {filename} has mismatched MIME type. Extension: {ext}, Detected: {detected_mime}")
        return False, "File content does not match its extension. This may indicate a security risk."

    return True, ""


def validate_file_size(file_obj: BinaryIO, max_size: Optional[int] = None, file_category: Optional[str] = None) -> tuple[bool, str]:
    """
    Validate file size.

    Args:
        file_obj: File object to validate
        max_size: Maximum size in bytes (overrides category default)
        file_category: File category to use for default max size

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Get file size
    file_obj.seek(0, os.SEEK_END)
    file_size = file_obj.tell()
    file_obj.seek(0)

    # Determine max size
    if max_size is None:
        if file_category and file_category in ALLOWED_FILE_TYPES:
            max_size = ALLOWED_FILE_TYPES[file_category]['max_size']
        else:
            max_size = getattr(settings, 'MAX_UPLOAD_SIZE', 50 * 1024 * 1024)

    if file_size > max_size:
        max_size_mb = max_size / (1024 * 1024)
        file_size_mb = file_size / (1024 * 1024)
        return False, f"File size ({file_size_mb:.2f}MB) exceeds maximum allowed size ({max_size_mb:.2f}MB)"

    if file_size == 0:
        return False, "File is empty"

    return True, ""


def scan_with_clamav(file_obj: BinaryIO, filename: str) -> Tuple[bool, str]:
    """
    Scan file with ClamAV antivirus (if available).
    Falls back gracefully if ClamAV is not installed.

    Args:
        file_obj: File object to scan
        filename: Filename for logging

    Returns:
        Tuple of (is_safe, error_message)
    """
    # Check if ClamAV scanning is enabled
    if not getattr(settings, 'ENABLE_CLAMAV_SCAN', False):
        return True, ""  # Skip if disabled

    try:
        # Check if clamscan is available
        result = subprocess.run(
            ['which', 'clamscan'],
            capture_output=True,
            timeout=5
        )

        if result.returncode != 0:
            logger.debug("ClamAV not installed, skipping virus scan")
            return True, ""  # Not installed, skip

        # Write file to temporary location for scanning
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            file_obj.seek(0)
            temp_file.write(file_obj.read())
            temp_path = temp_file.name
            file_obj.seek(0)

        try:
            # Scan with ClamAV
            result = subprocess.run(
                ['clamscan', '--no-summary', temp_path],
                capture_output=True,
                text=True,
                timeout=30
            )

            # Check result
            if result.returncode == 0:
                logger.info(f"ClamAV: File {filename} is clean")
                return True, ""
            elif result.returncode == 1:
                # Virus found
                logger.error(f"ClamAV: Malware detected in {filename}: {result.stdout}")
                return False, "Malware detected in uploaded file"
            else:
                # Error occurred
                logger.warning(f"ClamAV: Error scanning {filename}: {result.stderr}")
                # Don't block upload on scan errors, but log it
                return True, ""

        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_path)
            except:
                pass

    except subprocess.TimeoutExpired:
        logger.error(f"ClamAV scan timeout for {filename}")
        return True, ""  # Don't block on timeout
    except Exception as e:
        logger.error(f"Error running ClamAV scan for {filename}: {e}")
        return True, ""  # Don't block on errors


def scan_file_content(file_obj: BinaryIO, filename: str) -> Tuple[bool, str]:
    """
    Scan file content for malicious patterns.
    Includes optional ClamAV scanning if enabled.

    Args:
        file_obj: File object to scan
        filename: Filename for logging

    Returns:
        Tuple of (is_safe, error_message)
    """
    try:
        file_obj.seek(0)
        # Read first 10KB for scanning (don't load entire file)
        content = file_obj.read(10240)
        file_obj.seek(0)

        # Convert bytes to string for pattern matching (ignore decode errors)
        try:
            content_str = content.decode('utf-8', errors='ignore').lower()
        except:
            content_str = str(content).lower()

        # Check for dangerous patterns in content
        dangerous_content = [
            b'<script',
            b'<?php',
            b'<%',  # ASP
            b'#!/',  # Shebang
            b'<?xml version',  # Potentially dangerous XML
            b'\x4d\x5a',  # MZ header (Windows executables)
            b'\x7f\x45\x4c\x46',  # ELF header (Linux executables)
        ]

        for pattern in dangerous_content:
            if pattern in content:
                logger.warning(f"Suspicious content detected in file {filename}: {pattern}")
                return False, "File contains potentially malicious content"

        # Run ClamAV scan if enabled
        is_safe, error = scan_with_clamav(file_obj, filename)
        if not is_safe:
            return False, error

        return True, ""
    except Exception as e:
        logger.error(f"Error scanning file content for {filename}: {e}")
        return False, "Error scanning file content"


def validate_upload(file_obj: BinaryIO, filename: str, allowed_categories: Optional[list] = None) -> None:
    """
    Comprehensive file upload validation.

    Args:
        file_obj: File object to validate
        filename: Original filename
        allowed_categories: List of allowed file categories

    Raises:
        ValidationError: If file fails validation
    """
    # Sanitize filename
    safe_filename = sanitize_filename(filename)

    # Validate file type
    is_valid, error = validate_file_type(safe_filename, file_obj, allowed_categories)
    if not is_valid:
        raise ValidationError(error)

    # Determine category for size validation
    _, ext = os.path.splitext(safe_filename.lower())
    category = None
    for cat, config in ALLOWED_FILE_TYPES.items():
        if ext in config['extensions']:
            category = cat
            break

    # Validate file size
    is_valid, error = validate_file_size(file_obj, file_category=category)
    if not is_valid:
        raise ValidationError(error)

    # Scan content for malicious patterns
    is_safe, error = scan_file_content(file_obj, safe_filename)
    if not is_safe:
        raise ValidationError(error)

    logger.info(f"File {safe_filename} passed all security validations")
