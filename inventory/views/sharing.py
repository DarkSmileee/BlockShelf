"""
Sharing and collaboration views.
Handles public share links and collaborator invitations.
"""

import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import ExpressionWrapper, F, IntegerField, Q
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.crypto import get_random_string
from django.views.decorators.http import require_POST

from ..constants import PUBLIC_SHARE_ITEMS_PER_PAGE
from ..forms import InviteCollaboratorForm
from ..models import InventoryCollab, InventoryItem, InventoryShare, User
from ..utils import get_effective_config

logger = logging.getLogger(__name__)


@login_required
def create_share_link(request: HttpRequest) -> HttpResponse:
    """Create or refresh a single active share link for the current user."""
    if request.method != "POST":
        return HttpResponseForbidden("POST required")

    try:
        token = get_random_string(32)
        InventoryShare.objects.update_or_create(
            user=request.user,
            is_active=True,
            defaults={"token": token}
        )
        messages.success(request, "Share link created successfully.")

    except Exception as e:
        logger.exception("Error creating share link")
        messages.error(request, f"Failed to create share link: {str(e)}")

    return redirect(reverse("inventory:settings") + "?tab=sharing")


@login_required
def revoke_share_link(request: HttpRequest) -> HttpResponse:
    """Revoke the current user's active share link."""
    if request.method != "POST":
        return HttpResponseForbidden("POST required")

    try:
        # Use revoke() method to properly track revocation
        active_shares = InventoryShare.objects.filter(user=request.user, is_active=True)
        for share in active_shares:
            share.revoke()
        messages.success(request, "Share link revoked.")

    except Exception as e:
        logger.exception("Error revoking share link")
        messages.error(request, f"Failed to revoke share link: {str(e)}")

    return redirect(reverse("inventory:settings") + "?tab=sharing")


def shared_inventory(request: HttpRequest, token: str) -> HttpResponse:
    """Public, read-only inventory view by share token."""
    try:
        share = get_object_or_404(InventoryShare, token=token, is_active=True)

        # Check if share link has expired
        if share.is_expired():
            share.revoke()
            return render(request, "inventory/share_expired.html", {
                "owner": share.user,
            }, status=410)

        # Track access
        share.record_access()
        owner = share.user

        # Get query parameters
        query = (request.GET.get("q") or '').strip()
        sort_field = (request.GET.get("sort") or "name").lower()
        direction = (request.GET.get("dir") or "asc").lower()

        # Build queryset
        items = InventoryItem.objects.filter(user=owner)

        if query:
            items = items.filter(
                Q(name__icontains=query)
                | Q(part_id__icontains=query)
                | Q(color__icontains=query)
                | Q(storage_location__icontains=query)
            )

        # Add calculated field for available quantity
        items = items.annotate(
            quantity_available_calc=ExpressionWrapper(
                F("quantity_total") - F("quantity_used"),
                output_field=IntegerField()
            )
        )

        # Sorting
        sort_mapping = {
            "name": "name",
            "part": "part_id",
            "color": "color",
            "total": "quantity_total",
            "used": "quantity_used",
            "avail": "quantity_available_calc",
            "loc": "storage_location",
        }
        order_field = sort_mapping.get(sort_field, "name")
        if direction == "desc":
            order_field = f"-{order_field}"

        items = items.order_by(order_field, "id")

        # Pagination
        config = get_effective_config()
        per_page = getattr(config, "items_per_page", PUBLIC_SHARE_ITEMS_PER_PAGE) or PUBLIC_SHARE_ITEMS_PER_PAGE
        paginator = Paginator(items, per_page)
        page_obj = paginator.get_page(request.GET.get("page"))

        return render(request, "inventory/shared_inventory.html", {
            "owner": owner,
            "page_obj": page_obj,
            "items": page_obj.object_list,
            "q": query,
            "current_sort": sort_field,
            "current_dir": direction,
            "read_only": True,
        })

    except Exception as e:
        logger.exception("Error in shared_inventory view")
        return render(request, "errors/500.html", status=500)


@login_required
def inventory_switcher(request: HttpRequest) -> HttpResponse:
    """Display inventory switcher for collaborations."""
    try:
        my_inv = request.user
        collabs = (
            InventoryCollab.objects
            .filter(collaborator=request.user, is_active=True, accepted_at__isnull=False)
            .select_related("owner")
            .order_by("owner__username")
        )

        return render(request, "inventory/inventory_switcher.html", {
            "my_inv": my_inv,
            "collabs": collabs,
        })

    except Exception as e:
        logger.exception("Error in inventory_switcher view")
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect("inventory:list")


@login_required
@require_POST
def create_invite(request: HttpRequest) -> HttpResponse:
    """Create a new collaborator invitation."""
    try:
        form = InviteCollaboratorForm(request.POST)

        if not form.is_valid():
            messages.error(request, "Please correct the errors below.")
            return render(request, "inventory/settings.html", {
                "active_tab": "invite",
                "invite_form": form,
                "invites": InventoryCollab.objects.filter(owner=request.user).order_by("-created_at"),
            })

        email = form.cleaned_data["email"].strip().lower()
        can_edit_perm = form.cleaned_data.get("can_edit", True)
        can_delete_perm = form.cleaned_data.get("can_delete", False)

        # Prevent self-invitation
        if request.user.email and request.user.email.lower() == email:
            messages.error(request, "You cannot invite yourself.")
            return redirect(f"{reverse('inventory:settings')}?tab=invite")

        InventoryCollab.objects.create(
            owner=request.user,
            invited_email=email,
            can_edit=can_edit_perm,
            can_delete=can_delete_perm,
        )

        messages.success(request, "Invite created. Copy the link from the table below.")
        return redirect(f"{reverse('inventory:settings')}?tab=invite")

    except Exception as e:
        logger.exception("Error creating invite")
        messages.error(request, f"Failed to create invite: {str(e)}")
        return redirect(f"{reverse('inventory:settings')}?tab=invite")


@login_required
def revoke_invite(request: HttpRequest, pk: int) -> HttpResponse:
    """Revoke a collaborator invitation."""
    try:
        invite = get_object_or_404(InventoryCollab, pk=pk, owner=request.user, is_active=True)
        invite.revoke()
        messages.success(request, "Invite revoked.")

    except Exception as e:
        logger.exception("Error revoking invite")
        messages.error(request, f"Failed to revoke invite: {str(e)}")

    return redirect(f"{reverse('inventory:settings')}?tab=invite")


def accept_invite(request: HttpRequest, token: str) -> HttpResponse:
    """Accept a collaborator invitation."""
    try:
        invite = get_object_or_404(InventoryCollab, token=token, is_active=True)

        # If already accepted, redirect to inventory
        if invite.accepted_at:
            if not request.user.is_authenticated:
                return redirect(reverse("login") + f"?next={request.path}")
            return redirect(f"{reverse('inventory:list')}?owner={invite.owner_id}")

        # Must be logged in to accept
        if not request.user.is_authenticated:
            return redirect(reverse("login") + f"?next={request.path}")

        # Cannot accept own invite
        if request.user == invite.owner:
            messages.error(request, "You cannot accept your own invite.")
            return redirect(f"{reverse('inventory:settings')}?tab=invite")

        # Check for existing collaboration
        existing = InventoryCollab.objects.filter(
            owner=invite.owner,
            collaborator=request.user,
            is_active=True,
            accepted_at__isnull=False
        ).first()

        if existing:
            # Use NEW invite's permissions to prevent escalation
            existing.can_edit = invite.can_edit
            existing.can_delete = invite.can_delete
            existing.save(update_fields=["can_edit", "can_delete"])

            invite.revoke()

            messages.info(
                request,
                f"Your permissions for {invite.owner.username}'s inventory have been updated."
            )
        else:
            invite.mark_accepted(request.user)

        messages.success(request, f"You now have access to {invite.owner.username}'s inventory.")
        return redirect(f"{reverse('inventory:list')}?owner={invite.owner_id}")

    except Exception as e:
        logger.exception("Error accepting invite")
        messages.error(request, f"Failed to accept invite: {str(e)}")
        return redirect("inventory:list")


@login_required
@require_POST
def update_invite(request: HttpRequest, pk: int) -> HttpResponse:
    """Update permissions for an invitation/collaboration."""
    try:
        invite = get_object_or_404(InventoryCollab, pk=pk, owner=request.user)

        if not invite.is_active:
            messages.error(request, "Cannot edit a revoked invite.")
            return redirect(f"{reverse('inventory:settings')}?tab=invite")

        invite.can_edit = bool(request.POST.get("can_edit"))
        invite.can_delete = bool(request.POST.get("can_delete"))
        invite.save(update_fields=["can_edit", "can_delete"])

        messages.success(request, "Permissions updated.")
        return redirect(f"{reverse('inventory:settings')}?tab=invite")

    except Exception as e:
        logger.exception("Error updating invite")
        messages.error(request, f"Failed to update permissions: {str(e)}")
        return redirect(f"{reverse('inventory:settings')}?tab=invite")


@login_required
@require_POST
def purge_invite(request: HttpRequest, pk: int) -> HttpResponse:
    """Permanently delete a revoked invite."""
    try:
        invite = get_object_or_404(InventoryCollab, pk=pk, owner=request.user)

        if invite.is_active:
            messages.error(request, "You can only delete revoked invites.")
            return redirect(f"{reverse('inventory:settings')}?tab=invite")

        invite.delete()
        messages.success(request, "Revoked invite removed.")
        return redirect(f"{reverse('inventory:settings')}?tab=invite")

    except Exception as e:
        logger.exception("Error purging invite")
        messages.error(request, f"Failed to delete invite: {str(e)}")
        return redirect(f"{reverse('inventory:settings')}?tab=invite")
