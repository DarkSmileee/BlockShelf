"""
Health check endpoints for monitoring and load balancer integration.

Provides comprehensive health checks including:
- Basic liveness check
- Database connectivity
- Cache connectivity
- Disk space
- System metrics
"""

import logging
import os
import shutil
from typing import Any

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.http import HttpRequest, JsonResponse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

logger = logging.getLogger(__name__)


@require_GET
@never_cache
def health_check(request: HttpRequest) -> JsonResponse:
    """
    Comprehensive health check endpoint.

    Checks:
    - Application is running
    - Database connectivity
    - Cache connectivity (if configured)
    - Disk space availability
    - System time

    Returns:
        200 OK if all checks pass
        503 Service Unavailable if any check fails

    Response format:
        {
            "status": "healthy" | "unhealthy",
            "timestamp": "2025-01-02T10:30:00Z",
            "checks": {
                "database": {"status": "ok", "latency_ms": 5.2},
                "cache": {"status": "ok"},
                "disk": {"status": "ok", "free_gb": 50.3, "usage_percent": 45.2}
            },
            "version": "1.0.0"
        }
    """
    checks = {}
    all_healthy = True

    # Database check
    try:
        db_check = check_database()
        checks['database'] = db_check
        if db_check['status'] != 'ok':
            all_healthy = False
    except Exception as e:
        logger.exception("Health check: Database check failed")
        checks['database'] = {'status': 'error', 'error': str(e)}
        all_healthy = False

    # Cache check
    try:
        cache_check = check_cache()
        checks['cache'] = cache_check
        if cache_check['status'] != 'ok':
            all_healthy = False
    except Exception as e:
        logger.exception("Health check: Cache check failed")
        checks['cache'] = {'status': 'error', 'error': str(e)}
        all_healthy = False

    # Disk space check
    try:
        disk_check = check_disk_space()
        checks['disk'] = disk_check
        if disk_check['status'] != 'ok':
            all_healthy = False
    except Exception as e:
        logger.exception("Health check: Disk check failed")
        checks['disk'] = {'status': 'error', 'error': str(e)}
        all_healthy = False

    # Build response
    response_data = {
        'status': 'healthy' if all_healthy else 'unhealthy',
        'timestamp': timezone.now().isoformat(),
        'checks': checks,
        'version': getattr(settings, 'VERSION', '1.0.0'),
    }

    status_code = 200 if all_healthy else 503
    return JsonResponse(response_data, status=status_code)


@require_GET
@never_cache
def liveness_check(request: HttpRequest) -> JsonResponse:
    """
    Simple liveness check for Kubernetes/container orchestration.

    This is a lightweight check that only verifies the application is running.
    Use this for liveness probes that restart unhealthy containers.

    Returns:
        200 OK with {"status": "alive"}
    """
    return JsonResponse({
        'status': 'alive',
        'timestamp': timezone.now().isoformat(),
    })


@require_GET
@never_cache
def readiness_check(request: HttpRequest) -> JsonResponse:
    """
    Readiness check for Kubernetes/load balancers.

    Checks if the application is ready to receive traffic.
    Use this for readiness probes that remove containers from load balancers.

    Returns:
        200 OK if ready to serve traffic
        503 Service Unavailable if not ready
    """
    try:
        # Quick database connectivity check
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")

        return JsonResponse({
            'status': 'ready',
            'timestamp': timezone.now().isoformat(),
        })

    except Exception as e:
        logger.warning(f"Readiness check failed: {str(e)}")
        return JsonResponse({
            'status': 'not_ready',
            'timestamp': timezone.now().isoformat(),
            'reason': 'database_unavailable',
        }, status=503)


def check_database() -> dict[str, Any]:
    """
    Check database connectivity and measure latency.

    Returns:
        dict with status, latency_ms, and optionally error
    """
    import time

    start_time = time.time()

    try:
        # Execute simple query
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()

        latency_ms = (time.time() - start_time) * 1000

        # Warn if latency is high
        if latency_ms > 100:
            logger.warning(f"Database latency is high: {latency_ms:.2f}ms")

        return {
            'status': 'ok',
            'latency_ms': round(latency_ms, 2),
        }

    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        return {
            'status': 'error',
            'error': str(e),
        }


def check_cache() -> dict[str, Any]:
    """
    Check cache connectivity.

    Returns:
        dict with status and optionally error
    """
    try:
        # Try to set and get a value
        test_key = 'health_check_test'
        test_value = 'ok'

        cache.set(test_key, test_value, timeout=10)
        retrieved_value = cache.get(test_key)

        if retrieved_value != test_value:
            return {
                'status': 'error',
                'error': 'Cache set/get mismatch',
            }

        # Clean up
        cache.delete(test_key)

        return {'status': 'ok'}

    except Exception as e:
        # Cache is optional, so log as warning not error
        logger.warning(f"Cache health check failed: {str(e)}")
        return {
            'status': 'degraded',
            'error': str(e),
            'note': 'Cache is optional, application continues without it',
        }


def check_disk_space(threshold_percent: int = 90) -> dict[str, Any]:
    """
    Check available disk space.

    Args:
        threshold_percent: Warn if disk usage exceeds this percentage

    Returns:
        dict with status, free_gb, usage_percent
    """
    try:
        # Check the media directory or current directory
        path = getattr(settings, 'MEDIA_ROOT', os.getcwd())

        stat = shutil.disk_usage(path)

        free_gb = stat.free / (1024 ** 3)  # Convert to GB
        usage_percent = (stat.used / stat.total) * 100

        status = 'ok'
        if usage_percent >= threshold_percent:
            status = 'warning'
            logger.warning(f"Disk usage is high: {usage_percent:.1f}%")

        return {
            'status': status,
            'free_gb': round(free_gb, 2),
            'usage_percent': round(usage_percent, 1),
        }

    except Exception as e:
        logger.error(f"Disk space check failed: {str(e)}")
        return {
            'status': 'error',
            'error': str(e),
        }


@require_GET
@never_cache
def metrics(request: HttpRequest) -> JsonResponse:
    """
    Expose basic metrics for monitoring systems.

    Returns application metrics in Prometheus-compatible format (JSON).
    For actual Prometheus support, consider django-prometheus package.

    Returns:
        {
            "active_users": 150,
            "total_items": 5432,
            "database_size_mb": 234.5,
            "uptime_seconds": 86400
        }
    """
    try:
        from django.contrib.auth import get_user_model
        from ..models import InventoryItem

        User = get_user_model()

        metrics_data = {
            'active_users': User.objects.filter(is_active=True).count(),
            'total_items': InventoryItem.objects.count(),
            'timestamp': timezone.now().isoformat(),
        }

        # Database size (PostgreSQL only)
        try:
            with connection.cursor() as cursor:
                if connection.vendor == 'postgresql':
                    cursor.execute("""
                        SELECT pg_database_size(current_database()) / (1024.0 * 1024.0)
                    """)
                    db_size_mb = cursor.fetchone()[0]
                    metrics_data['database_size_mb'] = round(db_size_mb, 2)
        except Exception:
            pass  # Database size check is optional

        return JsonResponse(metrics_data)

    except Exception as e:
        logger.exception("Metrics endpoint failed")
        return JsonResponse({
            'error': 'Failed to collect metrics',
            'detail': str(e),
        }, status=500)
