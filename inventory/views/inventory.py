"""
Inventory CRUD operations.
Handles listing, creating, updating, deleting, and importing/exporting inventory items.
"""

import csv
import logging
from typing import Any

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from ..constants import CSV_IMPORT_MAX_ROWS, DEFAULT_ITEMS_PER_PAGE
from ..forms import ImportCSVForm, InventoryItemForm
from ..models import InventoryCollab, InventoryItem, User
from ..utils import get_effective_config
from .helpers import (
    can_delete,
    can_edit,
    detect_excel_type,
    get_owner_from_request,
    normalize_key,
    rows_from_csv_bytes,
    rows_from_xls_bytes,
    rows_from_xlsx_bytes,
    to_int,
    to_str,
)

logger = logging.getLogger(__name__)


@login_required
def inventory_list(request: HttpRequest) -> HttpResponse:
    """
    Display paginated inventory list with search and sorting.
    Consolidated version - removes duplication from views.py:420-458.
    """
    try:
        owner = get_owner_from_request(request)
        query = request.GET.get("q", "").strip()

        # Sorting
        sort_field = request.GET.get("sort", "name")
        direction = request.GET.get("dir", "asc")

        sort_mapping = {
            "name": "name",
            "part": "part_id",
            "color": "color",
            "total": "quantity_total",
            "used": "quantity_used",
            "avail": "quantity_available",
            "loc": "storage_location",
        }

        order_field = sort_mapping.get(sort_field, "name")
        if direction == "desc":
            order_field = f"-{order_field}"

        # Build queryset
        queryset = InventoryItem.objects.filter(user=owner)

        if query:
            queryset = queryset.filter(
                Q(name__icontains=query)
                | Q(part_id__icontains=query)
                | Q(color__icontains=query)
                | Q(storage_location__icontains=query)
            )

        queryset = queryset.order_by(order_field, "id")

        # Pagination
        config = get_effective_config()
        per_page = getattr(config, "items_per_page", DEFAULT_ITEMS_PER_PAGE) or DEFAULT_ITEMS_PER_PAGE
        paginator = Paginator(queryset, per_page)
        page_obj = paginator.get_page(request.GET.get("page"))

        # Permissions
        can_edit_inventory = can_edit(request.user, owner)
        can_delete_inventory = can_delete(request.user, owner)

        # Collaborator dropdown list (optimized to prevent N+1 queries)
        collab_list = []
        if request.user.is_authenticated:
            # Use select_related to fetch owner in a single query
            collabs = (
                InventoryCollab.objects
                .filter(collaborator=request.user, is_active=True, accepted_at__isnull=False)
                .select_related("owner")
                .order_by("owner__username")
            )
            # Extract owners directly from select_related results (no additional queries)
            collab_list = [collab.owner for collab in collabs]

        return render(request, "inventory/inventory_list.html", {
            "page_obj": page_obj,
            "q": query,
            "current_sort": sort_field,
            "current_dir": direction,
            "owner_context": owner,
            "is_own_inventory": request.user == owner,
            "can_edit_inventory": can_edit_inventory,
            "can_delete_inventory": can_delete_inventory,
            "collab_list": collab_list,
            "import_form": ImportCSVForm(),
        })

    except Exception as e:
        logger.exception("Error in inventory_list view")
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect("inventory:list")


@login_required
def add_item(request: HttpRequest) -> HttpResponse:
    """Add a new inventory item (legacy endpoint - redirects to item_create)."""
    return item_create(request)


@login_required
def item_create(request: HttpRequest) -> HttpResponse:
    """Create a new inventory item."""
    try:
        owner = get_owner_from_request(request)

        if not can_edit(request.user, owner):
            return HttpResponseForbidden("You do not have permission to add items here.")

        if request.method == "POST":
            form = InventoryItemForm(request.POST)
            if form.is_valid():
                item = form.save(commit=False)
                item.user = owner
                item.save()
                messages.success(request, "Item added.")
                return redirect(f"{reverse('inventory:list')}?owner={owner.pk}")
        else:
            form = InventoryItemForm()

        return render(request, "inventory/item_form.html", {
            "form": form,
            "owner_context": owner,
        })

    except Exception as e:
        logger.exception("Error in item_create view")
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect("inventory:list")


@login_required
def item_update(request: HttpRequest, pk: int) -> HttpResponse:
    """Update an existing inventory item."""
    try:
        item = get_object_or_404(InventoryItem, pk=pk)
        owner = item.user

        if not can_edit(request.user, owner):
            return HttpResponseForbidden("You do not have permission to edit items here.")

        if request.method == "POST":
            form = InventoryItemForm(request.POST, instance=item)
            if form.is_valid():
                form.save()
                messages.success(request, "Item updated.")
                return redirect(f"{reverse('inventory:list')}?owner={owner.pk}")
        else:
            form = InventoryItemForm(instance=item)

        return render(request, "inventory/item_form.html", {
            "form": form,
            "item": item,
            "owner_context": owner,
        })

    except Exception as e:
        logger.exception("Error in item_update view")
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect("inventory:list")


@login_required
def item_delete(request: HttpRequest, pk: int) -> HttpResponse:
    """Delete an inventory item."""
    try:
        item = get_object_or_404(InventoryItem, pk=pk)
        owner = item.user

        if not can_delete(request.user, owner):
            messages.error(request, "You don't have permission to delete items in this inventory.")
            return redirect(f"{reverse('inventory:list')}?owner={owner.pk}")

        if request.method == "POST":
            item.delete()
            messages.success(request, "Item deleted.")

        return redirect(f"{reverse('inventory:list')}?owner={owner.pk}")

    except Exception as e:
        logger.exception("Error in item_delete view")
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect("inventory:list")


@login_required
def export_csv(request: HttpRequest) -> HttpResponse:
    """Export current user's inventory to CSV."""
    try:
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="inventory.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'name', 'part_id', 'color', 'quantity_total', 'quantity_used',
            'storage_location', 'image_url', 'notes'
        ])

        for item in InventoryItem.objects.filter(user=request.user).order_by('name'):
            writer.writerow([
                item.name,
                item.part_id,
                item.color,
                item.quantity_total,
                item.quantity_used,
                item.storage_location,
                item.image_url,
                (item.notes or '').replace('\n', ' ').strip(),
            ])

        return response

    except Exception as e:
        logger.exception("Error in export_csv view")
        messages.error(request, f"Export failed: {str(e)}")
        return redirect("inventory:list")


@login_required
def import_csv(request: HttpRequest) -> HttpResponse:
    """Import inventory items from CSV/Excel file."""
    if request.method != "POST":
        return redirect("inventory:list")

    try:
        form = ImportCSVForm(request.POST, request.FILES)
        if not form.is_valid():
            messages.error(request, "Invalid file upload.")
            return redirect("inventory:list")

        upload = form.cleaned_data['file']
        raw = upload.read()
        file_type = detect_excel_type(upload.name, raw)

        # Parse file based on type
        try:
            if file_type == "xlsx":
                rows = rows_from_xlsx_bytes(raw)
            elif file_type == "xls":
                rows = rows_from_xls_bytes(raw)
            else:
                rows = rows_from_csv_bytes(raw)
        except Exception as e:
            logger.exception("Error parsing uploaded file")
            messages.error(request, f"Could not read file: {str(e)}")
            return redirect("inventory:list")

        # Convert to list and validate row count
        rows = list(rows)

        if len(rows) > CSV_IMPORT_MAX_ROWS:
            messages.error(
                request,
                f"File contains too many rows ({len(rows)}). Maximum allowed is {CSV_IMPORT_MAX_ROWS}."
            )
            return redirect("inventory:list")

        # Process rows
        added, updated, skipped, dupe_keys = process_import_rows(request.user, rows)

        # Build success message
        msg = f"Import complete: {added} added, {updated} updated, {skipped} skipped."
        if dupe_keys:
            msg += f" (Note: {dupe_keys} duplicate key set(s) existed; updated the first match.)"

        messages.success(request, msg)
        return redirect("inventory:list")

    except Exception as e:
        logger.exception("Error in import_csv view")
        messages.error(request, f"Import failed: {str(e)}")
        return redirect("inventory:list")


def process_import_rows(user: User, rows: list[dict[str, Any]]) -> tuple[int, int, int, int]:
    """
    Process imported CSV rows and create/update inventory items.
    Returns (added, updated, skipped, duplicate_keys_count).
    """
    added = updated = skipped = dupe_keys = 0

    with transaction.atomic():
        for row in rows:
            data = {normalize_key(k): v for k, v in row.items()}

            # Skip empty rows
            if not any(v not in ("", None) for v in data.values()):
                continue

            # Extract fields
            name = to_str(data.get('name'))
            part_id = to_str(data.get('part_id'))
            color = to_str(data.get('color'))
            quantity_total = to_int(data.get('quantity_total'), 0)
            quantity_used = to_int(data.get('quantity_used'), 0)
            location = to_str(data.get('storage_location'))
            image_url = to_str(data.get('image_url'))
            notes = to_str(data.get('notes'))

            # Skip if no part_id or name
            if not part_id and not name:
                skipped += 1
                continue

            # Check for existing item
            queryset = InventoryItem.objects.filter(
                user=user,
                part_id=part_id,
                color=color,
            )

            if not queryset.exists():
                # Create new item
                InventoryItem.objects.create(
                    user=user,
                    part_id=part_id,
                    color=color,
                    name=name or 'Unknown',
                    quantity_total=quantity_total,
                    quantity_used=quantity_used,
                    storage_location=location,
                    image_url=image_url,
                    notes=notes,
                )
                added += 1
            else:
                # Update existing item
                if queryset.count() > 1:
                    dupe_keys += 1

                obj = queryset.order_by('id').first()

                if name:
                    obj.name = name
                if data.get('quantity_total') not in (None, ''):
                    obj.quantity_total = quantity_total
                if data.get('quantity_used') not in (None, ''):
                    obj.quantity_used = quantity_used
                if location:
                    obj.storage_location = location
                if image_url:
                    obj.image_url = image_url
                if notes:
                    if obj.notes and notes not in obj.notes:
                        obj.notes = (obj.notes + "\n" + notes).strip()
                    else:
                        obj.notes = notes or obj.notes

                obj.save()
                updated += 1

    return added, updated, skipped, dupe_keys


@login_required
def check_duplicate(request: HttpRequest) -> JsonResponse:
    """Check if a duplicate inventory item exists (same part_id + color)."""
    try:
        part_id = (request.GET.get("part_id") or "").strip()
        color = (request.GET.get("color") or "").strip()
        exclude_pk = request.GET.get("exclude")

        queryset = InventoryItem.objects.filter(
            user=request.user,
            part_id__iexact=part_id,
            color__iexact=color,
        )

        if exclude_pk:
            queryset = queryset.exclude(pk=exclude_pk)

        exists = queryset.exists()
        data = {"exists": exists}

        if exists:
            data["count"] = queryset.count()
            data["items"] = list(
                queryset.values("id", "name", "quantity_total", "quantity_used", "storage_location")[:3]
            )

        return JsonResponse(data)

    except Exception as e:
        logger.exception("Error in check_duplicate view")
        return JsonResponse({"error": str(e)}, status=500)
