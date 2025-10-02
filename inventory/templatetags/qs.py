from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.simple_tag(takes_context=True)
def qs_replace(context, **kwargs):
    """
    Build a querystring by replacing/adding keys in current request.GET.
    Usage: {{ request.path }}{% qs_replace page=2 sort='name' %}

    Pass None to remove a key: {% qs_replace page=None %}
    """
    request = context.get("request")
    if request is None:
        return ""
    q = request.GET.copy()
    for k, v in kwargs.items():
        if v is None:
            q.pop(k, None)
        else:
            q[k] = v
    return ("?" + q.urlencode()) if q else ""

@register.simple_tag
def next_dir(current_sort, current_dir, field):
    """
    Return 'asc' or 'desc' for the next click on a column header.
    """
    if (current_sort or "") == field:
        return "desc" if (current_dir or "asc") == "asc" else "asc"
    return "asc"

@register.simple_tag
def sort_icon(current_sort, current_dir, field):
    """
    Print a styled sort indicator when this column is the active sort.
    """
    if (current_sort or "") != field:
        return ""

    # Use CSS-styled arrow with better visual appearance
    arrow_class = "sort-asc" if (current_dir or "asc") == "asc" else "sort-desc"
    return mark_safe(f'<span class="sort-icon {arrow_class}"></span>')
