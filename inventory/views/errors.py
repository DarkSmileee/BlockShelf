"""
Error handling views.
Custom 404 and 500 error handlers.
"""

import logging
from typing import Any

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

logger = logging.getLogger(__name__)


def error_404(request: HttpRequest, exception: Exception, template_name: str = "errors/404.html") -> HttpResponse:
    """Custom 404 error handler."""
    logger.warning(f"404 error for path: {request.path}", extra={"request": request})
    return render(request, template_name, status=404)


def error_500(request: HttpRequest, template_name: str = "errors/500.html") -> HttpResponse:
    """Custom 500 error handler."""
    logger.error(f"500 error for path: {request.path}", extra={"request": request})
    return render(request, template_name, status=500)
