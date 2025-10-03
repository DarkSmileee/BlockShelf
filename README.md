<p align="center">
  <img src="docs/branding/blockshelf-logo.png" alt="BlockShelf" width="260" />
</p>

<h1 align="center">BlockShelf</h1>

<p align="center">
  A clean, local‑first LEGO® parts inventory app — import, search, share, and collaborate.
</p>

<p align="center">
  <em>This project is Vibe Coded ✨</em>
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
