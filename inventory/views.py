# --- Standard library
import csv
import io
import os
import gzip
import zipfile
import shutil
import tempfile
import time
import re
import urllib.parse
from io import BytesIO
from html import unescape
import logging
import traceback

# --- Third-party
import requests

# --- Django
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth import login as auth_login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from django.core.cache import cache
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import F, ExpressionWrapper, IntegerField, Q
from django.http import (
    Http404,
    HttpResponse,
    HttpResponseForbidden,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.crypto import get_random_string
from django.views.decorators.http import require_GET, require_POST

# --- Local (project)
from .models import (
    InventoryItem,
    InventoryShare,
    InventoryCollab,
    RBPart,
    RBColor,
    RBElement,
    AppConfig,
    UserPreference,
)
from .forms import (
    ProfileForm,
    InventoryItemForm,
    ImportCSVForm,
    InviteCollaboratorForm,
    InventoryImportForm,
    AppConfigForm,
    UserSettingsForm,
)
from .utils import get_effective_config

logger = logging.getLogger(__name__)
User = get_user_model()

# -------------------------------------------------------------------------------------------------
# Small JSON helpers
# -------------------------------------------------------------------------------------------------
def _json_ok(**payload):
    d = {"ok": True}
    d.update(payload)
    return JsonResponse(d)

def _json_err(msg, status=400):
    return JsonResponse({"ok": False, "error": msg}, status=status)


# -------------------------------------------------------------------------------------------------
# Helpers (paths, csv handling)
# -------------------------------------------------------------------------------------------------
def _tmpdir():
    return tempfile.mkdtemp(prefix="rebrickable_")

def _count_csv_rows(path: str) -> int:
    opener = gzip.open if path.lower().endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        try:
            next(reader)  # header
        except StopIteration:
            return 0
        return sum(1 for _ in reader)

def _extract_reb_csvs_from_zip(zip_path: str, dest_dir: str) -> dict:
    found = {}
    targets = {"colors.csv": "colors", "parts.csv": "parts", "elements.csv": "elements"}
    with zipfile.ZipFile(zip_path) as z:
        for zinfo in z.infolist():
            base = os.path.basename(zinfo.filename).lower()
            if base in targets:
                out = os.path.join(dest_dir, base)
                with z.open(zinfo) as src, open(out, "wb") as dst:
                    shutil.copyfileobj(src, dst)
                found[targets[base]] = out
    return found


# -------------------------------------------------------------------------------------------------
# Owner/collab helpers & error handlers
# -------------------------------------------------------------------------------------------------
def _get_owner_from_request(request):
    owner = request.user
    oid = request.GET.get("owner")
    if not oid:
        return owner
    try:
        candidate = User.objects.get(pk=oid)
    except User.DoesNotExist:
        raise Http404("Owner not found")

    if request.user.is_authenticated and (candidate == request.user):
        return candidate

    ok = InventoryCollab.objects.filter(
        owner=candidate,
        collaborator=request.user,
        is_active=True,
        accepted_at__isnull=False,
    ).exists()
    if not ok:
        raise Http404("Not allowed to view this inventory")
    return candidate

def _get_collab_record(viewer, owner):
    if not viewer.is_authenticated or viewer == owner:
        return None
    return InventoryCollab.objects.filter(
        owner=owner, collaborator=viewer, is_active=True, accepted_at__isnull=False
    ).first()

def _can_edit(viewer, owner):
    if viewer == owner:
        return True
    rel = _get_collab_record(viewer, owner)
    return bool(rel and rel.can_edit)

def _can_delete(viewer, owner):
    if viewer == owner:
        return True
    rel = _get_collab_record(viewer, owner)
    return bool(rel and rel.can_delete)

def _viewer_per_page(user) -> int:
    """Per-page value for the *viewer* (not the inventory owner)."""
    try:
        return max(1, min(500, user.userpreference.items_per_page))
    except Exception:
        cfg = get_effective_config()
        # fallback to a sane default if prefs missing
        return 25


# -------------------------------------------------------------------------------------------------
# Inventory pages
# -------------------------------------------------------------------------------------------------
@login_required
def inventory_list(request):
    owner = _get_owner_from_request(request)
    q = request.GET.get("q", "").strip()

    # sort mapping
    sort = request.GET.get("sort", "name")
    direction = request.GET.get("dir", "asc")
    mapping = {
        "name": "name",
        "part": "part_id",
        "color": "color",
        "total": "quantity_total",
        "used": "quantity_used",
        "avail": "quantity_available",
        "loc": "storage_location",
    }
    order = mapping.get(sort, "name")
    if direction == "desc":
        order = f"-{order}"

    qs = InventoryItem.objects.filter(user=owner)
    if q:
        qs = qs.filter(
            Q(name__icontains=q)
            | Q(part_id__icontains=q)
            | Q(color__icontains=q)
            | Q(storage_location__icontains=q)
        )
    qs = qs.order_by(order, "id")

    # NEW: use viewer's preference for per-page
    per_page = _viewer_per_page(request.user)
    paginator = Paginator(qs, per_page)
    page_obj = paginator.get_page(request.GET.get("page"))

    # permissions
    can_edit = _can_edit(request.user, owner)
    can_delete = _can_delete(request.user, owner)

    # inventories this user can access (for the dropdown)
    collab_list = []
    if request.user.is_authenticated:
        collab_list = list(
            InventoryCollab.objects
            .filter(collaborator=request.user, is_active=True, accepted_at__isnull=False)
            .select_related("owner")
            .order_by("owner__username")
            .values_list("owner", flat=True)
        )
        collab_list = list(User.objects.filter(id__in=collab_list).order_by("username"))

    return render(request, "inventory/inventory_list.html", {
        "page_obj": page_obj,
        "q": q,
        "current_sort": sort,
        "current_dir": direction,
        "owner_context": owner,
        "is_own_inventory": request.user == owner,
        "can_edit_inventory": can_edit,
        "can_delete_inventory": can_delete,
        "collab_list": collab_list,
        "import_form": ImportCSVForm(),
    })


@login_required
def add_item(request):
    owner = _get_owner_from_request(request)
    if not _can_edit(request.user, owner):
        return HttpResponseForbidden("You do not have permission to add items here.")

    if request.method == "POST":
        form = InventoryItemForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.user = owner  # save into the owner's inventory
            item.save()
            messages.success(request, "Item added.")
            return redirect(f"{reverse('inventory:list')}?owner={owner.pk}")
    else:
        form = InventoryItemForm()

    return render(request, "inventory/item_form.html", {
        "form": form,
        "owner_context": owner,
    })


@login_required
def item_create(request):
    owner = _get_owner_from_request(request)
    if not _can_edit(request.user, owner):
        return HttpResponseForbidden("You do not have permission to add items here.")

    if request.method == 'POST':
        form = InventoryItemForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.user = owner
            item.save()
            messages.success(request, 'Item added.')
            return redirect(f"{reverse('inventory:list')}?owner={owner.pk}")
    else:
        form = InventoryItemForm()

    return render(request, 'inventory/item_form.html', {'form': form, 'owner_context': owner})


@login_required
def item_update(request, pk):
    item = get_object_or_404(InventoryItem, pk=pk)
    owner = item.user
    if not _can_edit(request.user, owner):
        return HttpResponseForbidden("You do not have permission to edit items here.")

    if request.method == 'POST':
        form = InventoryItemForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, 'Item updated.')
            return redirect(f"{reverse('inventory:list')}?owner={owner.pk}")
    else:
        form = InventoryItemForm(instance=item)
    return render(request, 'inventory/item_form.html', {'form': form, 'item': item, 'owner_context': owner})


@login_required
def item_delete(request, pk):
    item = get_object_or_404(InventoryItem, pk=pk)
    owner = item.user

    if not _can_delete(request.user, owner):
        messages.error(request, "You don’t have permission to delete items in this inventory.")
        return redirect(f"{reverse('inventory:list')}?owner={owner.pk}")

    if request.method == "POST":
        item.delete()
        messages.success(request, "Item deleted.")
        return redirect(f"{reverse('inventory:list')}?owner={owner.pk}")

    return redirect(f"{reverse('inventory:list')}?owner={owner.pk}")


# -------------------------------------------------------------------------------------------------
# Export / Import current user's inventory
# -------------------------------------------------------------------------------------------------
@login_required
def export_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="inventory.csv"'
    writer = csv.writer(response)
    writer.writerow(['name', 'part_id', 'color', 'quantity_total', 'quantity_used',
                     'storage_location', 'image_url', 'notes'])
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


# -------------------------------------------------------------------------------------------------
# Settings
# -------------------------------------------------------------------------------------------------
@login_required
def settings_view(request):
    """
    Tabs:
      - account  : profile + password
      - sharing  : read-only public link
      - invite   : collaborators
      - site     : per-user settings (items_per_page, rebrickable API, theme)
      - admin    : admin-only site settings (allow_registration, default_from_email)
      - danger   : destructive actions (existing)
    """
    tab = (request.GET.get("tab") or "site").lower()
    # Backward-compat: old ?tab=config -> admin
    if tab == "config":
        return redirect(f"{reverse('inventory:settings')}?tab=admin")

    ctx = {
        "active_tab": tab,
        "item_count": InventoryItem.objects.filter(user=request.user).count(),
    }

    # Account tab
    if tab == "account":
        if request.method == "POST":
            action = request.POST.get("action")
            if action in ("save_profile", "update_profile"):
                profile_form = ProfileForm(request.POST, instance=request.user)
                password_form = PasswordChangeForm(user=request.user)
                if profile_form.is_valid():
                    profile_form.save()
                    messages.success(request, "Profile updated.")
                    return redirect(f"{reverse('inventory:settings')}?tab=account")
                messages.error(request, "Please correct the errors below.")
                ctx.update({"profile_form": profile_form, "password_form": password_form})
                return render(request, "inventory/settings.html", ctx)

            elif action == "change_password":
                profile_form = ProfileForm(instance=request.user)
                password_form = PasswordChangeForm(user=request.user, data=request.POST)
                if password_form.is_valid():
                    user = password_form.save()
                    update_session_auth_hash(request, user)
                    messages.success(request, "Password changed.")
                    return redirect(f"{reverse('inventory:settings')}?tab=account")
                messages.error(request, "Please correct the errors below.")
                ctx.update({"profile_form": profile_form, "password_form": password_form})
                return render(request, "inventory/settings.html", ctx)

            return redirect(f"{reverse('inventory:settings')}?tab=account")

        ctx.update({
            "profile_form": ProfileForm(instance=request.user),
            "password_form": PasswordChangeForm(user=request.user),
        })
        return render(request, "inventory/settings.html", ctx)

    # Sharing tab
    if tab == "sharing":
        share = InventoryShare.objects.filter(user=request.user, is_active=True).first()
        share_url = None
        if share:
            share_url = request.build_absolute_uri(
                reverse("inventory:shared_inventory", args=[share.token])
            )
        ctx.update({"share_url": share_url})
        return render(request, "inventory/settings.html", ctx)

    # Invite tab
    if tab == "invite":
        ctx.update({
            "invite_form": InviteCollaboratorForm(),
            "invites": InventoryCollab.objects.filter(owner=request.user).order_by("-created_at"),
        })
        return render(request, "inventory/settings.html", ctx)

    # NEW: per-user settings tab
    if tab == "site":
        prefs, _ = UserPreference.objects.get_or_create(user=request.user)
        if request.method == "POST":
            form = UserSettingsForm(request.POST, instance=prefs)
            if form.is_valid():
                form.save()
                messages.success(request, "Your settings were saved.")
                return redirect(f"{reverse('inventory:settings')}?tab=site")
            messages.error(request, "Please correct the errors below.")
        else:
            form = UserSettingsForm(instance=prefs)
        ctx.update({"user_settings_form": form})
        return render(request, "inventory/settings.html", ctx)

    # Admin tab (site-wide settings)
    if tab == "admin":
        if not request.user.is_staff:
            return HttpResponseForbidden("Admins only.")
        cfg = AppConfig.get_solo()
        if request.method == "POST":
            form = AppConfigForm(request.POST, instance=cfg)
            if form.is_valid():
                form.save()
                messages.success(request, "Site settings saved.")
                return redirect(f"{reverse('inventory:settings')}?tab=admin")
            messages.error(request, "Please correct the errors below.")
        else:
            form = AppConfigForm(instance=cfg)
        # You can surface flags in the template (e.g., Google OAuth availability)
        google_ready = bool(
            getattr(settings, "SOCIALACCOUNT_PROVIDERS", {})
            .get("google", {})
            .get("APP", {})
            .get("client_id")
        )
        ctx.update({"appconfig_form": form, "google_ready": google_ready})
        return render(request, "inventory/settings.html", ctx)

    # default / danger tab handled by your template
    return render(request, "inventory/settings.html", ctx)


# -------------------------------------------------------------------------------------------------
# Sharing & collaborators (unchanged behavior)
# -------------------------------------------------------------------------------------------------
@login_required
def create_share_link(request):
    if request.method != "POST":
        return HttpResponseForbidden("POST required")
    token = get_random_string(32)
    InventoryShare.objects.update_or_create(
        user=request.user, is_active=True,
        defaults={"token": token}
    )
    return redirect(reverse("inventory:settings") + "?tab=sharing")

@login_required
def revoke_share_link(request):
    if request.method != "POST":
        return HttpResponseForbidden("POST required")
    InventoryShare.objects.filter(user=request.user, is_active=True).update(is_active=False)
    return redirect(reverse("inventory:settings") + "?tab=sharing")


def shared_inventory(request, token):
    share = get_object_or_404(InventoryShare, token=token, is_active=True)
    owner = share.user

    q = (request.GET.get("q") or "").strip()
    cur_sort = (request.GET.get("sort") or "name").lower()
    cur_dir  = (request.GET.get("dir") or "asc").lower()

    items = InventoryItem.objects.filter(user=owner)

    if q:
        items = items.filter(
            Q(name__icontains=q) |
            Q(part_id__icontains=q) |
            Q(color__icontains=q) |
            Q(storage_location__icontains=q)
        )

    items = items.annotate(
        quantity_available_calc=ExpressionWrapper(
            F("quantity_total") - F("quantity_used"),
            output_field=IntegerField()
        )
    )

    sort_map = {
        "name":  "name",
        "part":  "part_id",
        "color": "color",
        "total": "quantity_total",
        "used":  "quantity_used",
        "avail": "quantity_available_calc",
        "loc":   "storage_location",
    }
    sort_field = sort_map.get(cur_sort, "name")
    order = sort_field if cur_dir != "desc" else f"-{sort_field}"
    items = items.order_by(order, "id")

    # Public page uses a fixed/sane default
    paginator = Paginator(items, 50)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "inventory/shared_inventory.html", {
        "owner": owner,
        "page_obj": page_obj,
        "items": page_obj.object_list,
        "q": q,
        "current_sort": cur_sort,
        "current_dir": cur_dir,
        "read_only": True,
    })


# -------------------------------------------------------------------------------------------------
# Danger zone (same as before)
# -------------------------------------------------------------------------------------------------
@login_required
@require_POST
def delete_all_inventory(request):
    confirm_text = request.POST.get("confirm_text", "")
    confirm_ack = request.POST.get("confirm_ack") == "on"
    if confirm_text != "DELETE" or not confirm_ack:
        messages.error(request, "Confirmation failed. Type DELETE and tick the checkbox.")
        return redirect(f"{reverse('inventory:settings')}?tab=danger")
    qs = InventoryItem.objects.filter(user=request.user)
    deleted_count = qs.count()
    qs.delete()
    messages.success(request, f"Deleted {deleted_count} item(s) from your inventory.")
    return redirect("inventory:list")


# -------------------------------------------------------------------------------------------------
# Signup / auth miscellany (unchanged)
# -------------------------------------------------------------------------------------------------
def signup(request):
    if not get_effective_config().allow_registration:
        messages.error(request, "Self-registration is disabled. Please contact the administrator.")
        return redirect("login")
    if request.user.is_authenticated:
        return redirect('inventory:list')
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, 'Welcome! Your account has been created.')
            return redirect('inventory:list')
    else:
        form = UserCreationForm()
    return render(request, 'signup.html', {'form': form})


@login_required
def check_duplicate(request):
    part_id = (request.GET.get("part_id") or "").strip()
    color = (request.GET.get("color") or "").strip()
    exclude = request.GET.get("exclude")
    qs = InventoryItem.objects.filter(user=request.user, part_id__iexact=part_id, color__iexact=color)
    if exclude:
        qs = qs.exclude(pk=exclude)
    exists = qs.exists()
    data = {"exists": exists}
    if exists:
        data["count"] = qs.count()
        data["items"] = list(qs.values("id", "name", "quantity_total", "quantity_used", "storage_location")[:3])
    return JsonResponse(data)


@require_POST
def set_theme(request):
    theme = request.POST.get("theme")
    if theme not in {"light", "dark", "system"}:
        return JsonResponse({"ok": False, "error": "invalid theme"}, status=400)
    resp = JsonResponse({"ok": True, "theme": theme})
    resp.set_cookie("theme", theme, max_age=60*60*24*365, samesite="Lax")
    if request.user.is_authenticated:
        prefs, _ = UserPreference.objects.get_or_create(user=request.user)
        prefs.theme = theme
        prefs.save(update_fields=["theme"])
    return resp


# -------------------------------------------------------------------------------------------------
# Rebrickable helpers – use *user’s* API key only
# -------------------------------------------------------------------------------------------------
def _current_user_rebrickable_key(user) -> str:
    try:
        key = (user.userpreference.rebrickable_api_key or "").strip()
        return key
    except Exception:
        return ""

# -------------------------------------------------------------------------------------------------
# Owner/collab helpers & error handlers
# -------------------------------------------------------------------------------------------------
def _get_owner_from_request(request):
    owner = request.user
    oid = request.GET.get("owner")
    if not oid:
        return owner
    try:
        candidate = User.objects.get(pk=oid)
    except User.DoesNotExist:
        raise Http404("Owner not found")

    if request.user.is_authenticated and (candidate == request.user):
        return candidate

    ok = InventoryCollab.objects.filter(
        owner=candidate,
        collaborator=request.user,
        is_active=True,
        accepted_at__isnull=False,
    ).exists()
    if not ok:
        raise Http404("Not allowed to view this inventory")
    return candidate

def _get_collab_record(viewer, owner):
    if not viewer.is_authenticated or viewer == owner:
        return None
    return InventoryCollab.objects.filter(
        owner=owner, collaborator=viewer, is_active=True, accepted_at__isnull=False
    ).first()

def _can_edit(viewer, owner):
    if viewer == owner:
        return True
    rel = _get_collab_record(viewer, owner)
    return bool(rel and rel.can_edit)

def _can_delete(viewer, owner):
    if viewer == owner:
        return True
    rel = _get_collab_record(viewer, owner)
    return bool(rel and rel.can_delete)

def error_404(request, exception, template_name="errors/404.html"):
    return render(request, template_name, status=404)

def error_500(request, template_name="errors/500.html"):
    return render(request, template_name, status=500)

def get_appcfg():
    return AppConfig.get_cached()
