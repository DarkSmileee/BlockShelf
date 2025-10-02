# Multi-stage Dockerfile for BlockShelf
# Optimized for production deployment with minimal image size

# Stage 1: Build stage
FROM python:3.11-slim as builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install Python dependencies
COPY requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip && \
    pip install -r /tmp/requirements.txt && \
    pip install gunicorn

# Stage 2: Runtime stage
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=blockshelf_inventory.settings

# Install runtime system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create application user (non-root for security)
RUN groupadd -r blockshelf && \
    useradd -r -g blockshelf -d /app -s /bin/bash blockshelf && \
    mkdir -p /app /var/log/blockshelf /run/blockshelf && \
    chown -R blockshelf:blockshelf /app /var/log/blockshelf /run/blockshelf

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=blockshelf:blockshelf . .

# Create directories for static/media files
RUN mkdir -p static media && \
    chown -R blockshelf:blockshelf static media

# Switch to non-root user
USER blockshelf

# Collect static files (run at build time)
RUN python manage.py collectstatic --noinput --clear

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/inventory/health/liveness/ || exit 1

# Expose port
EXPOSE 8000

# Default command: run Gunicorn
CMD ["gunicorn", "--config", "gunicorn.conf.py", "blockshelf_inventory.wsgi:application"]
