"""
Dashboard view with user statistics and overview.
"""

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum, Q, F
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from ..models import InventoryItem
from .helpers import get_owner_from_request


@login_required
def dashboard(request: HttpRequest) -> HttpResponse:
    """
    Dashboard showing user inventory statistics and overview.
    """
    owner = get_owner_from_request(request)

    # Get all items for this user
    items = InventoryItem.objects.filter(user=owner)

    # Basic stats
    total_items = items.count()
    total_quantity = items.aggregate(total=Sum('quantity_total'))['total'] or 0
    total_used = items.aggregate(used=Sum('quantity_used'))['used'] or 0
    total_available = total_quantity - total_used

    # Most common items (by quantity_total)
    top_items = items.order_by('-quantity_total')[:5]

    # Most common colors
    top_colors = (
        items.values('color')
        .annotate(count=Count('id'), total_qty=Sum('quantity_total'))
        .order_by('-total_qty')[:5]
    )

    # Most used items (by quantity_used)
    most_used = items.filter(quantity_used__gt=0).order_by('-quantity_used')[:5]

    # Items by storage location
    locations = (
        items.exclude(storage_location='')
        .values('storage_location')
        .annotate(count=Count('id'))
        .order_by('-count')[:5]
    )

    # Items with low stock (available < 10 and > 0)
    low_stock = items.annotate(
        available=F('quantity_total') - F('quantity_used')
    ).filter(
        Q(quantity_total__gt=0) &
        Q(available__gt=0) &
        Q(available__lte=10)
    ).order_by('available')[:5]

    # Recent additions (last 5)
    recent_items = items.order_by('-created_at')[:5]

    context = {
        'owner_context': owner,
        'total_items': total_items,
        'total_quantity': total_quantity,
        'total_used': total_used,
        'total_available': total_available,
        'top_items': top_items,
        'top_colors': top_colors,
        'most_used': most_used,
        'locations': locations,
        'low_stock': low_stock,
        'recent_items': recent_items,
    }

    return render(request, 'inventory/dashboard.html', context)
