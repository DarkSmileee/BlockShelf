from django.conf import settings
from .models import AppConfig
import bleach
import re


def sanitize_text(text: str, allow_basic_formatting: bool = False) -> str:
    """
    Sanitize text input to prevent XSS attacks.

    Args:
        text: The text to sanitize
        allow_basic_formatting: If True, allows basic HTML tags like <b>, <i>, <br>

    Returns:
        Sanitized text string
    """
    if not text:
        return ""

    if allow_basic_formatting:
        # Allow only safe HTML tags
        allowed_tags = ['b', 'i', 'u', 'br', 'p', 'strong', 'em']
        allowed_attrs = {}
    else:
        # Strip all HTML
        allowed_tags = []
        allowed_attrs = {}

    # Clean the text
    cleaned = bleach.clean(
        text,
        tags=allowed_tags,
        attributes=allowed_attrs,
        strip=True
    )

    # Additional validation: limit length to prevent DoS
    max_length = 10000
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length]

    return cleaned.strip()


def sanitize_url(url: str) -> str:
    """
    Sanitize and validate URLs to prevent XSS and open redirect attacks.

    Args:
        url: The URL to sanitize

    Returns:
        Sanitized URL or empty string if invalid
    """
    if not url:
        return ""

    url = url.strip()

    # Only allow http/https protocols
    if not re.match(r'^https?://', url, re.IGNORECASE):
        return ""

    # Remove any potential javascript: or data: URLs
    if re.search(r'(javascript|data|vbscript):', url, re.IGNORECASE):
        return ""

    # Validate URL structure
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        if not parsed.netloc:
            return ""
    except Exception:
        return ""

    # Limit length
    if len(url) > 2048:
        return ""

    return url


class EffectiveConfig:
    def __init__(self, db: AppConfig | None):
        """
        Build an effective, nil-safe configuration by combining values
        from the DB (singleton AppConfig) and Django settings.
        DB values take precedence; settings act as defaults.
        """

        # --- Helpers --------------------------------------------------------
        def _db(field: str, default=None):
            """Safely read a field from db (which may be None)."""
            return getattr(db, field, None) if db is not None else default

        def _first_non_empty(*vals, fallback=None):
            """
            Return the first value that is not None and not an empty string.
            Useful for strings that may be '', None, or set later via GUI.
            """
            for v in vals:
                if v is not None and v != "":
                    return v
            return fallback

        def _clean_str(val) -> str:
            """Ensure a string (never None) and strip whitespace."""
            return (val or "").strip()

        # --- Branding / UI --------------------------------------------------
        self.site_name = _first_non_empty(
            _db("site_name"),
            getattr(settings, "SITE_NAME", "BlockShelf"),
            fallback="BlockShelf",
        )

        # --- Lists / pagination ---------------------------------------------
        self.items_per_page = _first_non_empty(
            _db("items_per_page"),
            getattr(settings, "ITEMS_PER_PAGE", 25),
            fallback=25,
        )

        # --- Auth -----------------------------------------------------------
        allow_reg = _db("allow_registration")
        if allow_reg is None:
            allow_reg = getattr(settings, "ALLOW_REGISTRATION", True)
        self.allow_registration = bool(allow_reg)

        # --- Integrations (optional) ----------------------------------------
        # Rebrickable key can be set later via GUI → treat missing as empty string
        self.rebrickable_api_key = _clean_str(
            _first_non_empty(
                _db("rebrickable_api_key"),
                getattr(settings, "REBRICKABLE_API_KEY", None),
                fallback="",
            )
        )

        # --- Email ----------------------------------------------------------
        self.default_from_email = _first_non_empty(
            _db("default_from_email"),
            getattr(settings, "DEFAULT_FROM_EMAIL", None),
            getattr(settings, "EMAIL_HOST_USER", None),
            fallback="",
        )


def get_effective_config() -> EffectiveConfig:
    db = AppConfig.get_solo()
    return EffectiveConfig(db)
