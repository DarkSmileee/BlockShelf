<p align="center">
  <img src="docs/branding/blockshelf-logo.png" alt="BlockShelf" width="260" />
</p>

<h1 align="center">BlockShelf</h1>

<p align="center">
  A clean, local‑first LEGO® parts inventory app — import, search, share, and collaborate.
</p>

<p align="center">
  <em>Built with Claude Code - AI-assisted development at its finest ✨</em>
</p>

---

## ✨ Features

### Core Functionality
- 📊 **Dashboard** - Overview with statistics, top items, low stock alerts, and quick actions
- 🔎 **Clean inventory UI** - Search, sort, pagination & dark mode
- 📥 **Import/Export** - CSV/XLS/XLSX import and CSV export
- 🧠 **Smart lookups** - Local-first part lookups with Rebrickable API fallback
- 🧩 **Rebrickable Bootstrap** - Seed local data from downloads ZIP (`colors.csv`, `parts.csv`, `elements.csv`)

### Collaboration & Sharing
- 🔗 **Share links** - Public read-only inventory links
- 👥 **Collaborator invitations** - Invite users with custom permissions (view/edit/delete)
- 🔄 **Inventory switching** - View and manage inventories you have access to

### Data Management
- 💾 **Automated backups** - Full database and per-user inventory backups
- ⚙️ **Backup rotation** - Automatic cleanup (keeps 10 most recent)
- 📅 **Scheduled backups** - Cron/systemd integration for daily backups
- 📝 **Notes system** - Built-in notepad for project planning

### User Experience
- 🎨 **Dark mode** - Automatic theme with localStorage persistence
- 🔢 **Sort persistence** - Remembers your inventory sorting preferences
- 📱 **Responsive design** - Works on desktop, tablet, and mobile
- ♿ **Accessibility** - WCAG compliant with keyboard navigation

> **Note:** LEGO® is a trademark of the LEGO Group, which does not sponsor, authorize or endorse this project.

---

## 🚀 Quick Start

### Docker Deployment (Recommended)

```bash
# 1. Clone repository
git clone https://github.com/DarkSmileee/BlockShelf.git
cd BlockShelf

# 2. Configure environment
cp .env.example .env
# Edit .env with your settings (see Environment Configuration below)

# 3. Start services
docker-compose up -d

# 4. Create admin user
docker-compose exec web python manage.py createsuperuser

# 5. Access at http://localhost
```

### Traditional Setup

```bash
# 1. Clone and setup
git clone https://github.com/DarkSmileee/BlockShelf.git
cd BlockShelf

# 2. Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your settings

# 5. Setup database
python manage.py migrate
python manage.py createcachetable

# 6. Create admin user
python manage.py createsuperuser

# 7. Run development server
python manage.py runserver
```

---

## 📋 Environment Configuration

### Required Variables

```bash
# Generate secret key:
# python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

DJANGO_SECRET_KEY=your-secret-key-here
POSTGRES_PASSWORD=secure-password

# Production settings
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Database (PostgreSQL recommended for production)
DATABASE_URL=postgresql://blockshelf:password@localhost:5432/blockshelf
```

### Optional but Recommended

```bash
# Monitoring
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project

# Caching
REDIS_URL=redis://localhost:6379/0

# Email notifications
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

See `.env.example` for all available options.

---

## 💾 Backup System

BlockShelf includes a comprehensive backup system with automated rotation.

### Manual Backups (Web Interface)

**Users:**
- Go to Settings → Backups → "Create Backup Now"
- Download your inventory backups (JSON format)

**Admins:**
- Settings → Backups → "Create Full DB Backup" (complete database)
- Settings → Backups → "Backup All Users" (individual inventories)

### Automated Backups (Recommended)

```bash
# Daily backups at 2 AM via cron
crontab -e

# Add this line:
0 2 * * * cd /path/to/BlockShelf && python manage.py create_backups --full-db --all-users >> /var/log/blockshelf-backup.log 2>&1
```

### Backup Management

```bash
# Create full database backup
python manage.py create_backups --full-db

# Backup all user inventories
python manage.py create_backups --all-users

# Both at once
python manage.py create_backups --full-db --all-users

# Keep 20 backups instead of 10
python manage.py create_backups --full-db --keep 20
```

Backups are stored in `media/backups/` and automatically rotated.

---

## 🐳 Docker Commands

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f web

# Run migrations
docker-compose exec web python manage.py migrate

# Create backups
docker-compose exec web python manage.py create_backups --full-db --all-users

# Shell access
docker-compose exec web bash

# Database backup
docker-compose exec db pg_dump -U blockshelf blockshelf > backup.sql

# Restore database
cat backup.sql | docker-compose exec -T db psql -U blockshelf blockshelf
```

---

## 🔧 Production Deployment

### Prerequisites
- Python 3.11+
- PostgreSQL 14+ (SQLite for development only)
- 1GB+ RAM, 2GB+ disk space
- Nginx/Caddy (reverse proxy)

### SSL/HTTPS Setup

**With Certbot (Let's Encrypt):**
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

**With Docker:**
1. Place SSL certificates in `nginx/ssl/`
2. Uncomment HTTPS section in `nginx/conf.d/blockshelf.conf`
3. Restart containers: `docker-compose restart nginx`

### Systemd Service (Traditional Deployment)

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

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable blockshelf
sudo systemctl start blockshelf
```

---

## 🏥 Health Checks & Monitoring

BlockShelf provides comprehensive health check endpoints:

| Endpoint | Purpose |
|----------|---------|
| `/inventory/health/` | Comprehensive health check |
| `/inventory/health/liveness/` | Liveness probe (K8s) |
| `/inventory/health/readiness/` | Readiness probe (K8s) |
| `/inventory/health/metrics/` | Basic metrics |

**Example response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-10-03T14:30:00Z",
  "checks": {
    "database": {"status": "ok", "latency_ms": 5.2},
    "cache": {"status": "ok"},
    "disk": {"status": "ok", "free_gb": 50.3, "usage_percent": 45.2}
  }
}
```

### Kubernetes Probes

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

---

## 🧪 Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=inventory --cov-report=html

# Specific categories
pytest -m auth          # Authentication tests
pytest -m permissions   # Permission tests
pytest -m imports       # Import/export tests
```

Target: 70%+ coverage for critical paths.

---

## 📸 Screenshots

### Dashboard
<p>
  <img src="docs/printscreens/dark/dark_dashboard.png" width="420" alt="Dashboard (Dark)">
  <img src="docs/printscreens/light/light_dashboard.png" width="420" alt="Dashboard (Light)">
</p>

### Inventory & Settings
<p>
  <img src="docs/printscreens/dark/dark_inventory.png" width="420" alt="Inventory (Dark)">
  <img src="docs/printscreens/dark/dark_settings.png" width="420" alt="Settings (Dark)">
</p>

### Dark Mode
<p>
  <img src="docs/printscreens/dark/dark_login.png" width="420" alt="Login (Dark)">
  <img src="docs/printscreens/dark/dark_add_item.png" width="420" alt="Add Item (Dark)">
</p>

### Light Mode
<p>
  <img src="docs/printscreens/light/light_login.png" width="420" alt="Login (Light)">
  <img src="docs/printscreens/light/light_inventory.png" width="420" alt="Inventory (Light)">
</p>

---

## 🔒 Security Checklist

- [ ] `DEBUG=False` in production
- [ ] Strong `DJANGO_SECRET_KEY` (50+ characters)
- [ ] `ALLOWED_HOSTS` configured
- [ ] `CSRF_TRUSTED_ORIGINS` configured
- [ ] SSL/HTTPS enabled
- [ ] Secure cookies enabled
- [ ] HSTS enabled (`SECURE_HSTS_SECONDS=31536000`)
- [ ] Strong database password
- [ ] Firewall configured (allow 80, 443 only)
- [ ] Regular backups enabled
- [ ] Sentry monitoring configured
- [ ] Admin panel secured

---

## 🛠️ Performance Tuning

### Gunicorn Workers
Formula: `(CPU cores * 2) + 1`

```bash
# Set in .env
GUNICORN_WORKERS=5
GUNICORN_WORKER_CLASS=sync  # or 'gevent' for I/O-bound
```

### Database Optimization
- Indexes already applied on critical fields
- Connection pooling: `CONN_MAX_AGE=600` (10 minutes)
- Enable Redis caching: `REDIS_URL=redis://localhost:6379/0`

---

## 🐛 Troubleshooting

### Application won't start
```bash
sudo journalctl -u blockshelf -n 50
python manage.py check --deploy
```

### Static files not loading
```bash
python manage.py collectstatic --noinput --clear
sudo nginx -t
```

### Database connection errors
```bash
psql -U blockshelf -h localhost -d blockshelf
sudo systemctl status postgresql
```

### 502 Bad Gateway
```bash
sudo systemctl status blockshelf
ls -la /run/blockshelf/blockshelf.sock
sudo tail -f /var/log/nginx/error.log
```

---

## 📚 Documentation

- **Backup Guide**: `QUICK_START_BACKUPS.md` - Backup system quick reference
- **Backup Scheduling**: `docs/backup_scheduling.md` - Detailed scheduling guide
- **Implementation Details**: `IMPLEMENTATION_SUMMARY.md` - Technical documentation
- **Features Added**: `FEATURES_ADDED.md` - Recent feature additions

---

## 🔄 Updating

```bash
# 1. Backup first!
python manage.py create_backups --full-db

# 2. Pull latest code
git pull origin main

# 3. Update dependencies
pip install -r requirements.txt

# 4. Run migrations
python manage.py migrate

# 5. Collect static files
python manage.py collectstatic --noinput

# 6. Restart
sudo systemctl restart blockshelf

# 7. Verify
curl http://localhost/inventory/health/
```

---

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new features
5. Submit a pull request

---

## 📄 License

Released under the **PolyForm Noncommercial License 1.0.0** — see [LICENSE](LICENSE).

---

## 🙏 Acknowledgments

- Built with [Django](https://www.djangoproject.com/)
- Powered by [Rebrickable API](https://rebrickable.com/api/)
- UI components from [Bootstrap 5](https://getbootstrap.com/)
- Developed with assistance from [Claude Code](https://claude.com/claude-code)

---

**Version**: 1.0.0
**Last Updated**: 2025-10-03
