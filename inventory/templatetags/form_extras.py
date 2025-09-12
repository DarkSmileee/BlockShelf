from django import template
import re

register = template.Library()

@register.filter(name="add_class")
def add_class(field, css):
    """
    Add CSS classes to a BoundField's widget in templates.
    If the value isn't a BoundField (e.g., it's already a string), return it unchanged.
    """
    if hasattr(field, "as_widget") and hasattr(getattr(field, "field", None), "widget"):
        widget = field.field.widget
        existing = widget.attrs.get("class", "")
        classes = f"{existing} {css}".strip()
        return field.as_widget(attrs={**widget.attrs, "class": classes})
    return field

@register.filter(name="add_attrs")
def add_attrs(field, attrs_str):
    """
    Add arbitrary HTML attrs to a BoundField's widget from a string like:
      "placeholder:Search..., data-role:picker, class:extra-class"
    If the value isn't a BoundField, return it unchanged.
    """
    if not (hasattr(field, "as_widget") and hasattr(getattr(field, "field", None), "widget")):
        return field

    attrs = {}
    for pair in [p.strip() for p in attrs_str.split(",") if p.strip()]:
        if ":" in pair:
            k, v = pair.split(":", 1)
            attrs[k.strip()] = v.strip()

    widget = field.field.widget
    merged = {**widget.attrs, **attrs}
    if "class" in widget.attrs and "class" in attrs:
        merged["class"] = f'{widget.attrs.get("class","")} {attrs["class"]}'.strip()

    return field.as_widget(attrs=merged)

# NEW: grab element id from a Rebrickable "elements" image url
# e.g. https://cdn.rebrickable.com/media/parts/elements/6003003.jpg -> "6003003"
@register.filter(name="element_id_from_url")
def element_id_from_url(url: str) -> str:
    if not url:
        return ""
    m = re.search(r"/elements/(\d+)\.jpg", str(url))
    return m.group(1) if m else ""
