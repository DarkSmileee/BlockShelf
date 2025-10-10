# blockshelf_inventory/settings.py

from pathlib import Path
import os
import environ

# --------------------------------------------------------------------------------------
# Paths & env
# --------------------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    SITE_ID=(int, 1),
    ALLOW_REGISTRATION=(bool, True),
)

# Load .env for local dev; in production rely on real environment variables
environ.Env.read_env(os.path.join(BASE_DIR, ".env"))

# --------------------------------------------------------------------------------------
# Core settings
# --------------------------------------------------------------------------------------
SECRET_KEY = env("DJANGO_SECRET_KEY")  # required
DEBUG = env("DEBUG")

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

# --------------------------------------------------------------------------------------
# Applications
# --------------------------------------------------------------------------------------
INSTALLED_APPS = [
    # Django core
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",

    # In dev, this disables Django’s built-in static server so WhiteNoise serves them.
    # Keep it BEFORE staticfiles.
    "whitenoise.runserver_nostatic",

    # Static files
    "django.contrib.staticfiles",

    # Third-party
    "django.contrib.sites",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "auditlog",

    # Your apps
    "inventory",
]

# --------------------------------------------------------------------------------------
# Middleware
# --------------------------------------------------------------------------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "auditlog.middleware.AuditlogMiddleware",
]

ROOT_URLCONF = "blockshelf_inventory.urls"

# --------------------------------------------------------------------------------------
# Templates
# --------------------------------------------------------------------------------------
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",  # needed by allauth
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "blockshelf_inventory.wsgi.application"

# --------------------------------------------------------------------------------------
# Database (DATABASE_URL in .env; falls back to SQLite)
# e.g. postgres://USER:PASS@HOST:5432/DBNAME
# --------------------------------------------------------------------------------------
DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
    )
}

# --------------------------------------------------------------------------------------
# Caching (shared across workers)
# --------------------------------------------------------------------------------------
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "django_cache",   # table name
        "TIMEOUT": 60 * 60,           # 1 hour (tweak as needed)
    }
}


# --------------------------------------------------------------------------------------
# Password validation
# --------------------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --------------------------------------------------------------------------------------
# Internationalization
# --------------------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = env("TIME_ZONE", default="UTC")
USE_I18N = True
USE_TZ = True

# --------------------------------------------------------------------------------------
# Static files (WhiteNoise)
# --------------------------------------------------------------------------------------
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# Optional: cache headers for WhiteNoise (tweak as needed)
WHITENOISE_MAX_AGE = env.int("WHITENOISE_MAX_AGE", default=60 * 60 * 24 * 7)  # 1 week

# --------------------------------------------------------------------------------------
# Media (user uploads)
# --------------------------------------------------------------------------------------
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# --------------------------------------------------------------------------------------
# Default primary key field type
# --------------------------------------------------------------------------------------
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --------------------------------------------------------------------------------------
# Django-allauth / auth
# --------------------------------------------------------------------------------------
SITE_ID = env("SITE_ID")
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "inventory:dashboard"
LOGOUT_REDIRECT_URL = "login"

AUTHENTICATION_BACKENDS = (
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
)

# django-allauth settings (using new configuration format)
ACCOUNT_LOGIN_METHODS = {"username"}  # Use username for login (not email)
ACCOUNT_EMAIL_VERIFICATION = env("ACCOUNT_EMAIL_VERIFICATION", default="none")  # set 'mandatory' in prod if desired
# Email is optional by default; add 'email*' to ACCOUNT_SIGNUP_FIELDS to make it required
ACCOUNT_SIGNUP_FIELDS = ["username*", "password1*", "password2*"]

SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "APP": {
            "client_id": env("GOOGLE_CLIENT_ID", default="YOUR_GOOGLE_CLIENT_ID"),
            "secret": env("GOOGLE_CLIENT_SECRET", default="YOUR_GOOGLE_CLIENT_SECRET"),
            "key": "",
        },
        "SCOPE": ["profile", "email"],
    }
}

# --------------------------------------------------------------------------------------
# App-specific settings
# --------------------------------------------------------------------------------------
ALLOW_REGISTRATION = env("ALLOW_REGISTRATION")  # set False to disable self sign-up
REBRICKABLE_API_KEY = env("REBRICKABLE_API_KEY", default=None)

# --------------------------------------------------------------------------------------
# Rate Limiting (Security)
# --------------------------------------------------------------------------------------
ENABLE_RATE_LIMITING = env.bool("ENABLE_RATE_LIMITING", default=True)
RATE_LIMIT_LOGIN_ATTEMPTS = env.int("RATE_LIMIT_LOGIN_ATTEMPTS", default=5)
RATE_LIMIT_LOGIN_WINDOW = env.int("RATE_LIMIT_LOGIN_WINDOW", default=900)  # 15 minutes
RATE_LIMIT_SIGNUP_ATTEMPTS = env.int("RATE_LIMIT_SIGNUP_ATTEMPTS", default=10)
RATE_LIMIT_SIGNUP_WINDOW = env.int("RATE_LIMIT_SIGNUP_WINDOW", default=3600)  # 1 hour
RATE_LIMIT_PASSWORD_RESET_ATTEMPTS = env.int("RATE_LIMIT_PASSWORD_RESET_ATTEMPTS", default=3)
RATE_LIMIT_PASSWORD_RESET_WINDOW = env.int("RATE_LIMIT_PASSWORD_RESET_WINDOW", default=3600)  # 1 hour

# --------------------------------------------------------------------------------------
# Account Lockout (Security)
# --------------------------------------------------------------------------------------
ENABLE_ACCOUNT_LOCKOUT = env.bool("ENABLE_ACCOUNT_LOCKOUT", default=True)
LOGIN_ATTEMPT_LIMIT = env.int("LOGIN_ATTEMPT_LIMIT", default=5)
LOCKOUT_DURATION_MINUTES = env.int("LOCKOUT_DURATION_MINUTES", default=15)

# --------------------------------------------------------------------------------------
# Sharing & Collaboration (Security)
# --------------------------------------------------------------------------------------
SHARE_LINK_DEFAULT_EXPIRY_DAYS = env.int("SHARE_LINK_DEFAULT_EXPIRY_DAYS", default=30)

# --------------------------------------------------------------------------------------
# Security Logging
# --------------------------------------------------------------------------------------
ENABLE_SECURITY_LOGGING = env.bool("ENABLE_SECURITY_LOGGING", default=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {name} {module} {process:d} {thread:d} - {message}',
            'style': '{',
        },
        'security': {
            'format': '[SECURITY] {asctime} {name} - {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'security_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'security.log',
            'maxBytes': 10 * 1024 * 1024,  # 10MB
            'backupCount': 5,
            'formatter': 'security',
        },
        'auth_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'auth.log',
            'maxBytes': 10 * 1024 * 1024,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'django.security': {
            'handlers': ['security_file', 'console'] if ENABLE_SECURITY_LOGGING else ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'inventory.views.auth': {
            'handlers': ['auth_file', 'console'] if ENABLE_SECURITY_LOGGING else ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'inventory.decorators.rate_limit': {
            'handlers': ['security_file', 'console'] if ENABLE_SECURITY_LOGGING else ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'inventory.models': {
            'handlers': ['auth_file', 'console'] if ENABLE_SECURITY_LOGGING else ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Create logs directory if it doesn't exist
import os
logs_dir = BASE_DIR / 'logs'
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)

# File upload limits (security)
DATA_UPLOAD_MAX_MEMORY_SIZE = env.int("DATA_UPLOAD_MAX_MEMORY_SIZE", default=10 * 1024 * 1024)  # 10MB
FILE_UPLOAD_MAX_MEMORY_SIZE = env.int("FILE_UPLOAD_MAX_MEMORY_SIZE", default=10 * 1024 * 1024)  # 10MB
MAX_UPLOAD_SIZE = env.int("MAX_UPLOAD_SIZE", default=50 * 1024 * 1024)  # 50MB for Rebrickable ZIP files

# --------------------------------------------------------------------------------------
# File Upload Security - ClamAV Integration (Optional)
# --------------------------------------------------------------------------------------
ENABLE_CLAMAV_SCAN = env.bool("ENABLE_CLAMAV_SCAN", default=False)  # Requires ClamAV installation

# --------------------------------------------------------------------------------------
# Email
# --------------------------------------------------------------------------------------
EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="noreply@example.com")

# Add your app context processor
TEMPLATES[0]["OPTIONS"]["context_processors"].append(
    "inventory.context_processors.app_settings"
)

ACCOUNT_ADAPTER = "inventory.adapters.AccountAdapter"

# --------------------------------------------------------------------------------------
# Security (good defaults; can be overridden via env)
# --------------------------------------------------------------------------------------
# In production (DEBUG=False) enforce secure cookies and optionally HSTS/redirects.
if not DEBUG:
    SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
    SESSION_COOKIE_SECURE = env.bool("SESSION_COOKIE_SECURE", default=True)
    CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE", default=True)
    SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=60 * 60 * 24 * 30)  # 30 days
    SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", default=True)
    SECURE_HSTS_PRELOAD = env.bool("SECURE_HSTS_PRELOAD", default=True)
    SECURE_REFERRER_POLICY = env("SECURE_REFERRER_POLICY", default="same-origin")
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# --------------------------------------------------------------------------------------
# Sentry Integration (optional, environment-based)
# --------------------------------------------------------------------------------------
SENTRY_DSN = env("SENTRY_DSN", default=None)
SENTRY_ENVIRONMENT = env("SENTRY_ENVIRONMENT", default="production")
SENTRY_TRACES_SAMPLE_RATE = env.float("SENTRY_TRACES_SAMPLE_RATE", default=0.1)
SENTRY_PROFILES_SAMPLE_RATE = env.float("SENTRY_PROFILES_SAMPLE_RATE", default=0.1)

if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=SENTRY_ENVIRONMENT,
        integrations=[
            DjangoIntegration(),
            LoggingIntegration(
                level=None,  # Capture all logs
                event_level="ERROR",  # Send errors and above as events
            ),
        ],
        # Performance monitoring
        traces_sample_rate=SENTRY_TRACES_SAMPLE_RATE,
        # Profiling
        profiles_sample_rate=SENTRY_PROFILES_SAMPLE_RATE,
        # Send PII (personally identifiable information)
        send_default_pii=False,
        # Release tracking
        release=env("SENTRY_RELEASE", default=None),
        # Before send callback to filter sensitive data
        before_send=lambda event, hint: event if not DEBUG else None,
    )
