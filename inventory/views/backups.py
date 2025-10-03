"""
Views for backup management.
Handles creating, downloading, and managing backups.
"""

import logging
import os
from typing import Optional

from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods, require_POST

from ..backup_utils import (
    create_all_user_backups,
    create_full_db_backup,
    create_user_inventory_backup,
    rotate_backups,
)
from ..models import Backup

logger = logging.getLogger(__name__)


@staff_member_required
@require_POST
def trigger_full_backup(request: HttpRequest) -> HttpResponse:
    """
    Manually trigger a full database backup (admin only).
    """
    backup = create_full_db_backup(created_by=request.user, is_scheduled=False)

    if backup:
        # Rotate old backups
        rotate_backups('full_db', keep_count=10)

        messages.success(
            request,
            f'Full database backup created successfully ({backup.file_size / 1024 / 1024:.2f} MB)'
        )
    else:
        messages.error(request, 'Failed to create database backup. Check server logs.')

    return redirect(reverse('inventory:settings') + '?tab=backups')


@staff_member_required
@require_POST
def trigger_all_user_backups(request: HttpRequest) -> HttpResponse:
    """
    Manually trigger inventory backups for all users (admin only).
    """
    success_count, fail_count = create_all_user_backups(
        created_by=request.user, is_scheduled=False
    )

    if success_count > 0:
        messages.success(
            request,
            f'Created inventory backups for {success_count} user(s)'
        )

    if fail_count > 0:
        messages.warning(
            request,
            f'Failed to create backups for {fail_count} user(s)'
        )

    return redirect(reverse('inventory:settings') + '?tab=backups')


@staff_member_required
@require_POST
def trigger_user_backup(request: HttpRequest) -> HttpResponse:
    """
    Manually trigger backup for the current user's inventory (staff only).
    """
    backup = create_user_inventory_backup(
        user=request.user,
        created_by=request.user,
        is_scheduled=False
    )

    if backup:
        # Rotate old backups for this user
        rotate_backups('user_inventory', user=request.user, keep_count=10)

        messages.success(
            request,
            f'Your inventory backup was created successfully ({backup.file_size / 1024:.2f} KB)'
        )
    else:
        messages.error(request, 'Failed to create your inventory backup. Please try again.')

    return redirect(reverse('inventory:settings') + '?tab=backups')


@login_required
def download_backup(request: HttpRequest, backup_id: int) -> HttpResponse:
    """
    Download a backup file.
    Users can only download their own inventory backups.
    Admins can download any backup.
    """
    try:
        backup = Backup.objects.get(id=backup_id)
    except Backup.DoesNotExist:
        raise Http404("Backup not found")

    # Permission check
    if not request.user.is_staff:
        # Regular users can only download their own inventory backups
        if backup.backup_type != 'user_inventory' or backup.user != request.user:
            raise Http404("Backup not found")

    # Build file path
    file_path = os.path.join(settings.MEDIA_ROOT, backup.file_path)

    if not os.path.exists(file_path):
        messages.error(request, 'Backup file not found on disk.')
        return redirect(reverse('inventory:settings') + '?tab=backups')

    # Determine filename for download
    filename = os.path.basename(file_path)

    # Serve the file
    response = FileResponse(
        open(file_path, 'rb'),
        as_attachment=True,
        filename=filename
    )

    return response


@staff_member_required
@require_POST
def delete_backup(request: HttpRequest, backup_id: int) -> HttpResponse:
    """
    Delete a backup (admin only).
    """
    try:
        backup = Backup.objects.get(id=backup_id)
        backup.delete()  # This will also delete the physical file
        messages.success(request, 'Backup deleted successfully')
    except Backup.DoesNotExist:
        messages.error(request, 'Backup not found')
    except Exception as e:
        logger.error(f"Failed to delete backup {backup_id}: {e}")
        messages.error(request, 'Failed to delete backup')

    return redirect(reverse('inventory:settings') + '?tab=backups')


@login_required
def list_user_backups(request: HttpRequest) -> JsonResponse:
    """
    List backups for the current user (for AJAX requests).
    """
    backups = Backup.objects.filter(
        backup_type='user_inventory',
        user=request.user
    ).order_by('-created_at')[:10]

    backup_list = [
        {
            'id': b.id,
            'created_at': b.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'file_size': b.file_size,
            'is_scheduled': b.is_scheduled,
        }
        for b in backups
    ]

    return JsonResponse({'backups': backup_list})


@staff_member_required
def list_all_backups(request: HttpRequest) -> JsonResponse:
    """
    List all backups (admin only, for AJAX requests).
    """
    backup_type = request.GET.get('type', 'all')

    query = Backup.objects.all()
    if backup_type == 'full_db':
        query = query.filter(backup_type='full_db')
    elif backup_type == 'user_inventory':
        query = query.filter(backup_type='user_inventory')

    backups = query.order_by('-created_at')[:50]

    backup_list = [
        {
            'id': b.id,
            'backup_type': b.backup_type,
            'user': b.user.username if b.user else None,
            'created_at': b.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'file_size': b.file_size,
            'is_scheduled': b.is_scheduled,
            'created_by': b.created_by.username if b.created_by else 'System',
        }
        for b in backups
    ]

    return JsonResponse({'backups': backup_list})
