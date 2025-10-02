"""
Authentication and user preference views.
Handles signup, theme switching, and other auth-related operations.
"""

import logging

from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from ..models import UserPreference
from ..utils import get_effective_config

logger = logging.getLogger(__name__)


def signup(request: HttpRequest) -> HttpResponse:
    """
    Handle user registration (username/password signup).
    Registration can be disabled by setting AppConfig.allow_registration=False.
    """
    try:
        # Check if registration is enabled
        if not get_effective_config().allow_registration:
            messages.error(request, "Self-registration is disabled. Please contact the administrator.")
            return redirect("login")

        # Redirect if already logged in
        if request.user.is_authenticated:
            return redirect('inventory:list')

        if request.method == 'POST':
            form = UserCreationForm(request.POST)
            if form.is_valid():
                user = form.save()
                auth_login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                messages.success(request, 'Welcome! Your account has been created.')
                logger.info(f"New user registered: {user.username}")
                return redirect('inventory:list')
        else:
            form = UserCreationForm()

        return render(request, 'signup.html', {'form': form})

    except Exception as e:
        logger.exception("Error in signup view")
        messages.error(request, f"Registration failed: {str(e)}")
        return redirect("login")


@require_POST
def set_theme(request: HttpRequest) -> JsonResponse:
    """
    Set user's theme preference (light, dark, or system).
    Stores in cookie and database (if authenticated).
    """
    try:
        theme = request.POST.get("theme")

        if theme not in {"light", "dark", "system"}:
            return JsonResponse({"ok": False, "error": "invalid theme"}, status=400)

        response = JsonResponse({"ok": True, "theme": theme})
        response.set_cookie("theme", theme, max_age=60 * 60 * 24 * 365, samesite="Lax")

        # Save to database if user is authenticated
        if request.user.is_authenticated:
            prefs, _ = UserPreference.objects.get_or_create(user=request.user)
            prefs.theme = theme
            prefs.save(update_fields=["theme"])
            logger.debug(f"User {request.user.username} changed theme to {theme}")

        return response

    except Exception as e:
        logger.exception("Error in set_theme view")
        return JsonResponse({"ok": False, "error": str(e)}, status=500)
