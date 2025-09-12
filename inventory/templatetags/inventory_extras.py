from django import template
from urllib.parse import urlparse

register = template.Library()

@register.filter
def element_id_from_url(url):
    """Return a stable last path segment from a URL (simple fallback)."""
    if not url:
        return ""
    path = urlparse(url).path or ""
    parts = [p for p in path.split("/") if p]
    return parts[-1] if parts else ""
