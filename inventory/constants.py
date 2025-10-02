"""
Constants for the inventory application.
Centralizes magic numbers and configuration values for better maintainability.
"""

# --------------------------------------------------------------------------------------
# Rate Limiting
# --------------------------------------------------------------------------------------
LOOKUP_LIMIT_PER_MIN = 60         # API lookups per user per minute
LOOKUP_LIMIT_PER_IP = 120         # API lookups per IP per minute (more lenient for shared IPs)
LOOKUP_WINDOW_SECONDS = 60        # Rate limit time window in seconds
LOOKUP_CACHE_TTL = 60 * 60 * 24   # Lookup cache TTL: 1 day

# --------------------------------------------------------------------------------------
# Element ID Detection
# --------------------------------------------------------------------------------------
ELEMENT_ID_MIN_LENGTH = 6         # Minimum length for element ID heuristic

# --------------------------------------------------------------------------------------
# CSV/File Import
# --------------------------------------------------------------------------------------
CSV_IMPORT_MAX_ROWS = 10_000      # Maximum rows for CSV import (user inventory)
REBRICKABLE_MAX_ROWS = 1_000_000  # Maximum rows for Rebrickable bootstrap import

# --------------------------------------------------------------------------------------
# File Upload
# --------------------------------------------------------------------------------------
MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50MB for Rebrickable ZIP files
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB

# --------------------------------------------------------------------------------------
# Batch Processing
# --------------------------------------------------------------------------------------
BULK_UPDATE_BATCH_SIZE_DEFAULT = 50
BULK_UPDATE_BATCH_SIZE_MIN = 1
BULK_UPDATE_BATCH_SIZE_MAX = 500

REBRICKABLE_BATCH_SIZE_DEFAULT = 2000
REBRICKABLE_BATCH_SIZE_MIN = 100
REBRICKABLE_BATCH_SIZE_MAX = 10_000

# --------------------------------------------------------------------------------------
# Cache Keys & TTL
# --------------------------------------------------------------------------------------
REBRICKABLE_JOB_CACHE_TTL = 60 * 60  # 1 hour for Rebrickable import jobs
APPCONFIG_CACHE_TTL = 300            # 5 minutes for AppConfig singleton
LOOKUP_MISS_CACHE_TTL = 300          # 5 minutes for lookup misses

# --------------------------------------------------------------------------------------
# Pagination
# --------------------------------------------------------------------------------------
DEFAULT_ITEMS_PER_PAGE = 25
PUBLIC_SHARE_ITEMS_PER_PAGE = 50

# --------------------------------------------------------------------------------------
# Text Limits
# --------------------------------------------------------------------------------------
MAX_TEXT_LENGTH = 10_000           # Maximum length for sanitized text
MAX_URL_LENGTH = 2048              # Maximum length for URLs

# --------------------------------------------------------------------------------------
# HTTP Timeouts
# --------------------------------------------------------------------------------------
EXTERNAL_API_TIMEOUT = 10          # Timeout for external API requests (seconds)

# --------------------------------------------------------------------------------------
# Logging
# --------------------------------------------------------------------------------------
LOG_MESSAGE_MAX_LENGTH = 200       # Maximum log messages to return in batch operations
