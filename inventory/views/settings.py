"""
Settings and admin configuration views.
Handles user preferences, site configuration, and dangerous operations.
"""

import logging

from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from ..forms import AppConfigForm, InviteCollaboratorForm, ProfileForm, UserSettingsForm
from ..models import AppConfig, InventoryCollab, InventoryItem, UserPreference

logger = logging.getLogger(__name__)


@login_required
def settings_view(request: HttpRequest) -> HttpResponse:
    """
    Main settings view with multiple tabs:
    - account: Profile and password
    - sharing: Share links
    - invite: Collaborator invitations
    - config: Site-wide admin settings (staff only)
    - maintenance: Bulk update tools
    - danger: Delete all inventory
    """
    try:
        tab = request.GET.get("tab", "maintenance")

        context = {
            "active_tab": tab,
            "item_count": InventoryItem.objects.filter(user=request.user).count(),
        }

        # =================== ACCOUNT TAB ===================
        if tab == "account":
            return handle_account_tab(request, context)

        # =================== SITE (PER-USER) TAB ===================
        if tab == "site":
            return handle_site_tab(request, context)

        # =================== SHARING TAB ===================
        # Handled in sharing.py, but context is prepared here
        if tab == "sharing":
            from ..models import InventoryShare
            share = InventoryShare.objects.filter(user=request.user, is_active=True).first()
            share_url = None
            if share:
                share_url = request.build_absolute_uri(
                    reverse("inventory:shared_inventory", args=[share.token])
                )
            context.update({"share_url": share_url, "share_obj": share})
            return render(request, "inventory/settings.html", context)

        # =================== INVITE TAB ===================
        if tab == "invite":
            context.update({
                "invite_form": InviteCollaboratorForm(),
                "invites": InventoryCollab.objects.filter(owner=request.user).order_by("-created_at"),
            })
            return render(request, "inventory/settings.html", context)

        # =================== ADMIN CONFIG TAB ===================
        if tab == "admin":
            if not request.user.is_staff:
                return HttpResponseForbidden("Admins only.")
            return handle_admin_config_tab(request, context)

        # =================== MAINTENANCE / DANGER / DEFAULT ===================
        return render(request, "inventory/settings.html", context)

    except Exception as e:
        logger.exception("Error in settings_view")
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect("inventory:list")


def handle_site_tab(request: HttpRequest, context: dict) -> HttpResponse:
    """Handle the site (per-user) tab settings."""
    # Get or create user preference
    user_pref, created = UserPreference.objects.get_or_create(user=request.user)

    if request.method == "POST":
        form = UserSettingsForm(request.POST, instance=user_pref)
        if form.is_valid():
            form.save()
            messages.success(request, "Settings saved.")
            return redirect(f"{reverse('inventory:settings')}?tab=site")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = UserSettingsForm(instance=user_pref)

    context.update({"user_settings_form": form})
    return render(request, "inventory/settings.html", context)


def handle_account_tab(request: HttpRequest, context: dict) -> HttpResponse:
    """Handle the account tab (profile and password)."""
    if request.method == "POST":
        action = request.POST.get("action")

        if action in ("save_profile", "update_profile"):
            profile_form = ProfileForm(request.POST, instance=request.user)
            password_form = PasswordChangeForm(user=request.user)

            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, "Profile updated.")
                return redirect(f"{reverse('inventory:settings')}?tab=account")
            else:
                messages.error(request, "Please correct the errors below.")

            context.update({"profile_form": profile_form, "password_form": password_form})
            return render(request, "inventory/settings.html", context)

        elif action == "change_password":
            profile_form = ProfileForm(instance=request.user)
            password_form = PasswordChangeForm(user=request.user, data=request.POST)

            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Password changed.")
                return redirect(f"{reverse('inventory:settings')}?tab=account")
            else:
                messages.error(request, "Please correct the errors below.")

            context.update({"profile_form": profile_form, "password_form": password_form})
            return render(request, "inventory/settings.html", context)

        else:
            return redirect(f"{reverse('inventory:settings')}?tab=account")

    # GET request
    context.update({
        "profile_form": ProfileForm(instance=request.user),
        "password_form": PasswordChangeForm(user=request.user),
    })
    return render(request, "inventory/settings.html", context)


def handle_admin_config_tab(request: HttpRequest, context: dict) -> HttpResponse:
    """Handle the admin config tab (site-wide settings)."""
    from django.conf import settings

    config = AppConfig.get_solo()

    if request.method == "POST":
        form = AppConfigForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, "Site settings saved.")
            return redirect(f"{reverse('inventory:settings')}?tab=admin")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = AppConfigForm(instance=config)

    # Check if Google sign-in is configured
    google_ready = bool(
        getattr(settings, "SOCIALACCOUNT_PROVIDERS", {})
        .get("google", {})
        .get("APP", {})
        .get("client_id")
    )

    context.update({
        "appconfig_form": form,
        "google_ready": google_ready,
    })
    return render(request, "inventory/settings.html", context)


@login_required
@require_POST
def delete_all_inventory(request: HttpRequest) -> HttpResponse:
    """
    Permanently delete all inventory items for the authenticated user.
    Requires confirmation text and checkbox acknowledgment.
    """
    try:
        confirm_text = request.POST.get("confirm_text", "")
        confirm_ack = request.POST.get("confirm_ack") == "on"

        if confirm_text != "DELETE" or not confirm_ack:
            messages.error(request, "Confirmation failed. Type DELETE and tick the checkbox.")
            return redirect(f"{reverse('inventory:settings')}?tab=danger")

        queryset = InventoryItem.objects.filter(user=request.user)
        deleted_count = queryset.count()
        queryset.delete()

        logger.info(f"User {request.user.username} deleted {deleted_count} inventory items")
        messages.success(request, f"Deleted {deleted_count} item(s) from your inventory.")
        return redirect("inventory:list")

    except Exception as e:
        logger.exception("Error in delete_all_inventory")
        messages.error(request, f"Failed to delete inventory: {str(e)}")
        return redirect(f"{reverse('inventory:settings')}?tab=danger")
