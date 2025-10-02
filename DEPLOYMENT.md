# BlockShelf Deployment Guide

Complete guide for deploying BlockShelf to production using Docker or traditional methods.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Environment Configuration](#environment-configuration)
- [Docker Deployment](#docker-deployment-recommended)
- [Traditional Deployment](#traditional-deployment)
- [Health Checks & Monitoring](#health-checks--monitoring)
- [Database Backups](#database-backups)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required
- Python 3.11+
- PostgreSQL 14+ (SQLite for development only)
- 1GB+ RAM
- 2GB+ disk space

### Optional
- Redis 7+ (for caching)
- Nginx/Caddy (reverse proxy)
- Sentry account (error monitoring)
- Docker & Docker Compose (for containerized deployment)

---

## Environment Configuration

### 1. Copy Environment Template

```bash
cp .env.example .env
```

### 2. Generate Secret Key

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 3. Configure Required Variables

Edit `.env` and set at minimum:

```bash
# REQUIRED
DJANGO_SECRET_KEY=<your-generated-secret-key>
POSTGRES_PASSWORD=<secure-password>

# REQUIRED for production
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Database (PostgreSQL recommended)
DATABASE_URL=postgresql://blockshelf:password@localhost:5432/blockshelf
```

### 4. Optional but Recommended

```bash
# Sentry monitoring
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project

# Redis caching
REDIS_URL=redis://localhost:6379/0

# Email (for notifications)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

See `.env.example` for all available options.

---

## Docker Deployment (Recommended)

### Quick Start

```bash
# 1. Configure environment
cp .env.example .env
# Edit .env with your settings

# 2. Build and start containers
docker-compose up -d

# 3. Create admin user
docker-compose exec web python manage.py createsuperuser

# 4. Access application
# http://localhost (or your domain)
```

### Docker Architecture

The `docker-compose.yml` includes:

- **web**: Django application (Gunicorn)
- **db**: PostgreSQL database
- **redis**: Redis cache
- **nginx**: Reverse proxy & static file server

### Docker Commands

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f web

# Stop services
docker-compose down

# Rebuild after code changes
docker-compose build
docker-compose up -d

# Run migrations
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser

# Shell access
docker-compose exec web bash

# Run tests
docker-compose exec web pytest

# Backup database
docker-compose exec db pg_dump -U blockshelf blockshelf > backup.sql

# Restore database
cat backup.sql | docker-compose exec -T db psql -U blockshelf blockshelf
```

### Production Docker Setup

1. **SSL/HTTPS Configuration**

   Uncomment HTTPS section in `nginx/conf.d/blockshelf.conf`:

   ```nginx
   server {
       listen 443 ssl http2;
       ssl_certificate /etc/nginx/ssl/cert.pem;
       ssl_certificate_key /etc/nginx/ssl/key.pem;
       # ... rest of config
   }
   ```

   Place SSL certificates in `nginx/ssl/`:
   ```bash
   mkdir -p nginx/ssl
   # Copy cert.pem and key.pem to nginx/ssl/
   ```

2. **Environment Variables**

   Set production values in `.env`:
   ```bash
   DEBUG=False
   SECURE_SSL_REDIRECT=True
   SESSION_COOKIE_SECURE=True
   CSRF_COOKIE_SECURE=True
   GUNICORN_WORKERS=4
   GUNICORN_LOG_LEVEL=warning
   ```

3. **Persistent Volumes**

   Docker volumes are automatically created:
   - `blockshelf_postgres_data`: Database files
   - `blockshelf_redis_data`: Redis data
   - `blockshelf_static`: Static files
   - `blockshelf_media`: User uploads

---

## Traditional Deployment

### 1. System Dependencies

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install python3.11 python3.11-venv python3-pip postgresql nginx
```

**RHEL/CentOS:**
```bash
sudo yum install python311 python311-pip postgresql-server nginx
```

### 2. PostgreSQL Setup

```bash
# Create database and user
sudo -u postgres psql
```

```sql
CREATE DATABASE blockshelf;
CREATE USER blockshelf WITH PASSWORD 'your-secure-password';
GRANT ALL PRIVILEGES ON DATABASE blockshelf TO blockshelf;
ALTER DATABASE blockshelf OWNER TO blockshelf;
\q
```

### 3. Application Setup

```bash
# Clone repository
git clone https://github.com/yourusername/BlockShelf.git
cd BlockShelf

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic --noinput
```

### 4. Gunicorn Service

Create `/etc/systemd/system/blockshelf.service`:

```ini
[Unit]
Description=BlockShelf Gunicorn daemon
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/var/www/BlockShelf
Environment="PATH=/var/www/BlockShelf/venv/bin"
ExecStart=/var/www/BlockShelf/venv/bin/gunicorn \
    --config /var/www/BlockShelf/gunicorn.conf.py \
    blockshelf_inventory.wsgi:application

ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable blockshelf
sudo systemctl start blockshelf
sudo systemctl status blockshelf
```

### 5. Nginx Configuration

Create `/etc/nginx/sites-available/blockshelf`:

```nginx
upstream blockshelf_app {
    server unix:/run/blockshelf/blockshelf.sock fail_timeout=0;
}

server {
    listen 80;
    server_name yourdomain.com;
    client_max_body_size 50M;

    location /static/ {
        alias /var/www/BlockShelf/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /media/ {
        alias /var/www/BlockShelf/media/;
        expires 7d;
        add_header Cache-Control "public";
    }

    location / {
        proxy_pass http://blockshelf_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable site:
```bash
sudo ln -s /etc/nginx/sites-available/blockshelf /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 6. SSL with Certbot (Let's Encrypt)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

Certbot will automatically configure HTTPS and set up auto-renewal.

---

## Health Checks & Monitoring

### Health Check Endpoints

BlockShelf provides comprehensive health check endpoints:

| Endpoint | Purpose | Auth Required |
|----------|---------|---------------|
| `/inventory/health/` | Comprehensive health check | No |
| `/inventory/health/liveness/` | Simple liveness probe | No |
| `/inventory/health/readiness/` | Readiness for traffic | No |
| `/inventory/health/metrics/` | Basic metrics | No |

### Comprehensive Health Check

```bash
curl http://localhost/inventory/health/
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2025-10-02T14:30:00Z",
  "checks": {
    "database": {
      "status": "ok",
      "latency_ms": 5.2
    },
    "cache": {
      "status": "ok"
    },
    "disk": {
      "status": "ok",
      "free_gb": 50.3,
      "usage_percent": 45.2
    }
  },
  "version": "1.0.0"
}
```

Returns:
- `200 OK` if all checks pass
- `503 Service Unavailable` if any check fails

### Kubernetes Health Probes

```yaml
livenessProbe:
  httpGet:
    path: /inventory/health/liveness/
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /inventory/health/readiness/
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 5
```

### Sentry Integration

If `SENTRY_DSN` is configured, all errors are automatically reported to Sentry.

**Test Sentry integration:**
```python
# Django shell
python manage.py shell

from sentry_sdk import capture_message
capture_message("Test message from BlockShelf")
```

**Configuration options:**
```bash
SENTRY_DSN=https://xxx@sentry.io/yyy
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0.1  # 10% of transactions
SENTRY_PROFILES_SAMPLE_RATE=0.1  # 10% profiling
SENTRY_RELEASE=v1.0.0  # Track deployments
```

### Monitoring Commands

```bash
# Check application status
sudo systemctl status blockshelf

# View application logs
sudo journalctl -u blockshelf -f

# View Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# Check Gunicorn workers
ps aux | grep gunicorn

# Monitor database connections
sudo -u postgres psql -c "SELECT * FROM pg_stat_activity;"
```

---

## Database Backups

BlockShelf includes automated backup scripts with Grandfather-Father-Son (GFS) retention.

### Automated Backups

**Setup:**
```bash
# Make scripts executable
chmod +x scripts/backup_database.sh
chmod +x scripts/restore_database.sh

# Add to crontab for daily backups at 2 AM
crontab -e
```

Add:
```cron
0 2 * * * /var/www/BlockShelf/scripts/backup_database.sh
```

### Manual Backup

```bash
# Using provided script
bash scripts/backup_database.sh

# Or with make
make backup
```

### Restore from Backup

```bash
# Using provided script
bash scripts/restore_database.sh

# Select backup from list
# Confirm restoration
```

### Backup Strategy

- **Daily**: Last 30 days
- **Weekly**: Last 12 weeks
- **Monthly**: Last 12 months
- Compression: ~90% size reduction
- Integrity checking on restore

See [docs/DATABASE_BACKUP_STRATEGY.md](docs/DATABASE_BACKUP_STRATEGY.md) for details.

---

## Testing

### Run Test Suite

```bash
# All tests
pytest

# With coverage report
pytest --cov=inventory --cov-report=html

# Fast tests only (skip slow integration tests)
pytest -m "not slow"

# Specific test categories
pytest -m auth          # Authentication tests
pytest -m permissions   # Permission tests
pytest -m imports       # Import/export tests
```

### Test Coverage

Target: 70%+ coverage for critical paths:
- Authentication & authorization
- Permissions & sharing
- CSV/Excel imports
- API endpoints

View coverage report:
```bash
pytest --cov=inventory --cov-report=html
open htmlcov/index.html
```

---

## Performance Tuning

### Gunicorn Workers

Formula: `(CPU cores * 2) + 1`

```bash
# Set in .env
GUNICORN_WORKERS=5

# For CPU-bound tasks
GUNICORN_WORKER_CLASS=sync

# For I/O-bound tasks (requires gevent)
GUNICORN_WORKER_CLASS=gevent
```

### Database Optimization

**Indexes** (already applied):
- Composite: `(user, part_id, color)`
- Single: `storage_location`, `name`, `created_at`, `updated_at`

**Connection pooling:**
```python
# settings.py
DATABASES = {
    'default': {
        # ...
        'CONN_MAX_AGE': 600,  # 10 minutes
        'OPTIONS': {
            'pool_size': 20,
        }
    }
}
```

### Redis Caching

```bash
# Enable in .env
REDIS_URL=redis://localhost:6379/0
```

Cache user preferences and frequently accessed data.

---

## Security Checklist

- [ ] `DEBUG=False` in production
- [ ] Strong `DJANGO_SECRET_KEY` (50+ characters)
- [ ] `ALLOWED_HOSTS` configured
- [ ] `CSRF_TRUSTED_ORIGINS` configured
- [ ] SSL/HTTPS enabled (`SECURE_SSL_REDIRECT=True`)
- [ ] Secure cookies (`SESSION_COOKIE_SECURE=True`)
- [ ] HSTS enabled (`SECURE_HSTS_SECONDS=31536000`)
- [ ] Strong database password
- [ ] Firewall configured (allow 80, 443 only)
- [ ] Regular backups enabled
- [ ] Sentry monitoring configured
- [ ] File upload limits enforced
- [ ] Admin panel secured (complex password)
- [ ] Regular security updates (`apt update && apt upgrade`)

---

## Troubleshooting

### Application won't start

```bash
# Check logs
sudo journalctl -u blockshelf -n 50

# Common issues:
# - Missing environment variables
# - Database connection failed
# - Permission errors

# Verify environment
source venv/bin/activate
python manage.py check --deploy
```

### Static files not loading

```bash
# Collect static files
python manage.py collectstatic --noinput --clear

# Check Nginx configuration
sudo nginx -t

# Verify permissions
ls -la /var/www/BlockShelf/static/
```

### Database connection errors

```bash
# Test PostgreSQL connection
psql -U blockshelf -h localhost -d blockshelf

# Check PostgreSQL service
sudo systemctl status postgresql

# Verify DATABASE_URL in .env
echo $DATABASE_URL
```

### 502 Bad Gateway

```bash
# Check if Gunicorn is running
sudo systemctl status blockshelf

# Check socket file exists
ls -la /run/blockshelf/blockshelf.sock

# Check Nginx error logs
sudo tail -f /var/log/nginx/error.log
```

### High memory usage

```bash
# Reduce Gunicorn workers
GUNICORN_WORKERS=2

# Enable worker recycling
GUNICORN_MAX_REQUESTS=1000
GUNICORN_MAX_REQUESTS_JITTER=50

# Monitor memory
htop
```

### Slow performance

```bash
# Check database queries
# Enable DEBUG temporarily and use django-debug-toolbar

# Check database indexes
python manage.py showmigrations

# Enable Redis caching
REDIS_URL=redis://localhost:6379/0

# Monitor Gunicorn workers
GUNICORN_LOG_LEVEL=debug
```

---

## Maintenance

### Update Application

```bash
# Backup database first
make backup

# Pull latest code
git pull origin main

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Restart application
sudo systemctl restart blockshelf

# Verify health
curl http://localhost/inventory/health/
```

### Database Migrations

```bash
# Create migration
python manage.py makemigrations

# Apply migration
python manage.py migrate

# Rollback migration
python manage.py migrate inventory <previous_migration_name>
```

### Log Rotation

Create `/etc/logrotate.d/blockshelf`:

```
/var/log/blockshelf/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
    sharedscripts
    postrotate
        systemctl reload blockshelf > /dev/null
    endscript
}
```

---

## Support

- **Documentation**: See `docs/` directory
- **Issues**: https://github.com/yourusername/BlockShelf/issues
- **Security**: Report to security@yourdomain.com

---

**Deployment Date**: 2025-10-02
**Version**: 1.0.0
**Maintained By**: BlockShelf Development Team
