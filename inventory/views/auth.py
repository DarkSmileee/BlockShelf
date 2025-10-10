"""
Authentication and user preference views.
Handles signup, theme switching, and other auth-related operations.
"""

import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login as auth_login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST, require_http_methods
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect

from ..models import UserPreference, LoginAttempt
from ..utils import get_effective_config
from ..decorators.rate_limit import rate_limit, reset_rate_limit, get_client_ip

logger = logging.getLogger(__name__)


@never_cache
@csrf_protect
@require_http_methods(["GET", "POST"])
@rate_limit(
    attempts=getattr(settings, 'RATE_LIMIT_LOGIN_ATTEMPTS', 5),
    window=getattr(settings, 'RATE_LIMIT_LOGIN_WINDOW', 900),
    key_prefix='login'
)
def custom_login(request: HttpRequest) -> HttpResponse:
    """
    Custom login view with rate limiting and account lockout.
    Replaces Django's default LoginView.
    """
    if request.user.is_authenticated:
        return redirect(settings.LOGIN_REDIRECT_URL)

    # Get client info
    client_ip = get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()

        # Check if account lockout is enabled
        if getattr(settings, 'ENABLE_ACCOUNT_LOCKOUT', True):
            # Check if account is locked
            is_locked, time_remaining = LoginAttempt.is_account_locked(username)

            if is_locked:
                # Record failed attempt due to lockout
                LoginAttempt.record_attempt(
                    username=username,
                    ip_address=client_ip,
                    success=False,
                    user_agent=user_agent,
                    failure_reason='Account locked'
                )

                messages.error(
                    request,
                    f'Account is temporarily locked due to multiple failed login attempts. '
                    f'Please try again in {time_remaining // 60} minutes.'
                )
                logger.warning(f"Login attempt for locked account: {username} from {client_ip}")
                return render(request, 'registration/login.html', {
                    'form': AuthenticationForm(),
                    'account_locked': True,
                    'time_remaining': time_remaining
                })

        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)

            if user is not None:
                # Record successful login
                LoginAttempt.record_attempt(
                    username=username,
                    ip_address=client_ip,
                    success=True,
                    user_agent=user_agent
                )

                auth_login(request, user)
                # Reset rate limit on successful login
                reset_rate_limit(request, 'login')
                logger.info(f"User {username} logged in successfully from {client_ip}")

                # Redirect to next or default
                next_url = request.GET.get('next', settings.LOGIN_REDIRECT_URL)
                return redirect(next_url)
        else:
            # Record failed login attempt
            LoginAttempt.record_attempt(
                username=username,
                ip_address=client_ip,
                success=False,
                user_agent=user_agent,
                failure_reason='Invalid credentials'
            )

            # Check if account is now locked after this attempt
            is_locked, time_remaining = LoginAttempt.is_account_locked(username)
            if is_locked:
                messages.error(
                    request,
                    f'Too many failed login attempts. Account is now locked for {time_remaining // 60} minutes.'
                )
                logger.warning(f"Account locked after failed attempt: {username} from {client_ip}")
            else:
                logger.warning(f"Failed login attempt for username: {username} from {client_ip}")
    else:
        form = AuthenticationForm()

    return render(request, 'registration/login.html', {'form': form})


@rate_limit(
    attempts=getattr(settings, 'RATE_LIMIT_SIGNUP_ATTEMPTS', 10),
    window=getattr(settings, 'RATE_LIMIT_SIGNUP_WINDOW', 3600),
    key_prefix='signup'
)
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
                # Reset rate limit on successful signup
                reset_rate_limit(request, 'signup')
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
