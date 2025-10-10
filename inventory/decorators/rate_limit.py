"""
Rate limiting decorator for views.
Implements configurable rate limiting using Django cache backend.
"""

import hashlib
import logging
import time
from functools import wraps
from typing import Callable, Optional

from django.conf import settings
from django.core.cache import cache
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render

logger = logging.getLogger(__name__)


def get_client_ip(request: HttpRequest) -> str:
    """
    Get the client's IP address from request, respecting proxy headers.
    Handles X-Forwarded-For and X-Real-IP headers.
    """
    # Check for X-Forwarded-For header (multiple IPs, first is client)
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
        return ip

    # Check for X-Real-IP header
    x_real_ip = request.META.get('HTTP_X_REAL_IP')
    if x_real_ip:
        return x_real_ip.strip()

    # Fallback to REMOTE_ADDR
    return request.META.get('REMOTE_ADDR', 'unknown')


def rate_limit(
    attempts: int = 5,
    window: int = 900,  # 15 minutes in seconds
    block_duration: Optional[int] = None,
    key_prefix: str = 'rate_limit',
    progressive_delays: bool = True,
) -> Callable:
    """
    Rate limiting decorator for views.

    Args:
        attempts: Maximum number of attempts allowed within the time window
        window: Time window in seconds
        block_duration: How long to block after exceeding limit (defaults to window)
        key_prefix: Prefix for cache keys (to differentiate endpoints)
        progressive_delays: Enable progressive lockout durations

    Usage:
        @rate_limit(attempts=5, window=900, key_prefix='login')
        def login_view(request):
            ...
    """
    if block_duration is None:
        block_duration = window

    def decorator(view_func: Callable) -> Callable:
        @wraps(view_func)
        def wrapped_view(request: HttpRequest, *args, **kwargs) -> HttpResponse:
            # Check if rate limiting is enabled
            if not getattr(settings, 'ENABLE_RATE_LIMITING', True):
                return view_func(request, *args, **kwargs)

            # Get client IP
            client_ip = get_client_ip(request)

            # Create cache key
            cache_key = f"{key_prefix}:{client_ip}"
            attempts_key = f"{cache_key}:attempts"
            blocked_key = f"{cache_key}:blocked"
            violation_count_key = f"{cache_key}:violations"

            # Check if client is currently blocked
            blocked_until = cache.get(blocked_key)
            if blocked_until:
                time_remaining = int(blocked_until - time.time())
                if time_remaining > 0:
                    logger.warning(
                        f"Rate limit exceeded for {client_ip} on {key_prefix}. "
                        f"Blocked for {time_remaining} more seconds."
                    )

                    # Return appropriate error response
                    if request.headers.get('Accept') == 'application/json':
                        return JsonResponse(
                            {
                                'error': 'Too many requests',
                                'message': f'Rate limit exceeded. Please try again in {time_remaining} seconds.',
                                'retry_after': time_remaining
                            },
                            status=429
                        )

                    return render(
                        request,
                        'errors/rate_limit.html',
                        {
                            'time_remaining': time_remaining,
                            'retry_after': time_remaining
                        },
                        status=429
                    )
                else:
                    # Block expired, clear it
                    cache.delete(blocked_key)

            # Get current attempt count
            current_attempts = cache.get(attempts_key, 0)

            # Increment attempt counter
            current_attempts += 1
            cache.set(attempts_key, current_attempts, window)

            # Check if limit exceeded
            if current_attempts > attempts:
                # Calculate block duration (progressive if enabled)
                if progressive_delays:
                    violation_count = cache.get(violation_count_key, 0) + 1
                    cache.set(violation_count_key, violation_count, 60 * 60 * 24)  # 24 hour window

                    # Progressive delays: 5min, 15min, 1hr, 24hr
                    delay_schedule = [300, 900, 3600, 86400]
                    actual_block_duration = delay_schedule[min(violation_count - 1, len(delay_schedule) - 1)]
                else:
                    actual_block_duration = block_duration

                blocked_until = time.time() + actual_block_duration
                cache.set(blocked_key, blocked_until, actual_block_duration)

                logger.warning(
                    f"Rate limit exceeded for {client_ip} on {key_prefix}. "
                    f"Blocked for {actual_block_duration} seconds. "
                    f"Attempts: {current_attempts}/{attempts}"
                )

                # Return error response
                if request.headers.get('Accept') == 'application/json':
                    return JsonResponse(
                        {
                            'error': 'Too many requests',
                            'message': f'Rate limit exceeded. Please try again in {actual_block_duration} seconds.',
                            'retry_after': actual_block_duration
                        },
                        status=429
                    )

                return render(
                    request,
                    'errors/rate_limit.html',
                    {
                        'time_remaining': actual_block_duration,
                        'retry_after': actual_block_duration
                    },
                    status=429
                )

            # Allow the request
            return view_func(request, *args, **kwargs)

        return wrapped_view
    return decorator


def reset_rate_limit(request: HttpRequest, key_prefix: str) -> None:
    """
    Reset rate limit for a specific client and endpoint.
    Useful after successful authentication.

    Args:
        request: The HTTP request object
        key_prefix: The rate limit key prefix to reset
    """
    client_ip = get_client_ip(request)
    cache_key = f"{key_prefix}:{client_ip}"

    # Clear all rate limit keys for this client/endpoint
    cache.delete(f"{cache_key}:attempts")
    cache.delete(f"{cache_key}:blocked")

    logger.debug(f"Reset rate limit for {client_ip} on {key_prefix}")
