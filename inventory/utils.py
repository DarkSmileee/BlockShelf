from django.conf import settings
from .models import AppConfig

class EffectiveConfig:
    def __init__(self, db):
        # Branding / UI
        self.site_name = db.site_name or getattr(settings, "SITE_NAME", "BlockShelf")
        # Lists / pagination
        self.items_per_page = db.items_per_page or getattr(settings, "ITEMS_PER_PAGE", 25)
        # Auth
        self.allow_registration = (
            db.allow_registration
            if db is not None
            else getattr(settings, "ALLOW_REGISTRATION", True)
        )
        # Integrations
        self.rebrickable_api_key = (db.rebrickable_api_key or getattr(settings, "REBRICKABLE_API_KEY", "")).strip()
        # Email
        self.default_from_email = (
            db.default_from_email
            or getattr(settings, "DEFAULT_FROM_EMAIL", getattr(settings, "EMAIL_HOST_USER", ""))
        )

def get_effective_config() -> EffectiveConfig:
    db = AppConfig.get_solo()
    return EffectiveConfig(db)
