from .utils import get_effective_config

def app_settings(request):
    cfg = get_effective_config()
    return {
        "ALLOW_SELF_REG": bool(cfg.allow_registration),
    }
