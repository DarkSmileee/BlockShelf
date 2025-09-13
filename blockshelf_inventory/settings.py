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
LOGIN_REDIRECT_URL = "inventory:list"
LOGOUT_REDIRECT_URL = "login"

AUTHENTICATION_BACKENDS = (
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
)

ACCOUNT_AUTHENTICATION_METHOD = "username"
ACCOUNT_EMAIL_VERIFICATION = env("ACCOUNT_EMAIL_VERIFICATION", default="none")  # set 'mandatory' in prod if desired
ACCOUNT_EMAIL_REQUIRED = env.bool("ACCOUNT_EMAIL_REQUIRED", default=False)

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
