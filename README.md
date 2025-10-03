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
- 💾 **Automated backups** - Full database and per-user inventory backups (CSV format)
- ⚙️ **Backup rotation** - Keeps 10 most recent backups per user
- 📅 **Scheduled backups** - Daily automatic backups at 2 AM via systemd timer
- 📝 **Notes system** - Built-in notepad for project planning
- 🔍 **Backup search** - Filter admin backup list by username

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

## 💾 Backup System

### Automatic Daily Backups

BlockShelf includes an automated backup system that runs daily at 2 AM:

**Setup automatic backups:**
```bash
cd BlockShelf/scripts
./setup-backup-timer.sh
```

This creates:
- **Full database backup** - Complete PostgreSQL/MySQL/SQLite dump (1 backup, kept 10 most recent)
- **Per-user inventory backups** - Individual CSV files for each user (10 most recent per user)

**Manual backups:**
```bash
# Full database + all user inventories
python manage.py create_backups --full-db --all-users

# Full database only
python manage.py create_backups --full-db

# All user inventories only
python manage.py create_backups --all-users

# Custom retention (default: 10)
python manage.py create_backups --full-db --all-users --keep 20
```

**Check backup status:**
```bash
# View next scheduled backup time
systemctl list-timers blockshelf-backup.timer

# View backup logs
sudo journalctl -u blockshelf-backup.service -f

# Manually trigger backup
sudo systemctl start blockshelf-backup.service
```

**Backup locations:**
- Full DB: `media/backups/full_db/`
- User inventories: `media/backups/user_inventory/{user_id}/`

**Admin features:**
- View all backups in Settings > Backups tab
- Filter user backups by username
- Download individual backups
- Manual backup creation
- Automatic rotation (keeps 10 most recent per user)

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

**Version**: 1.0.0
**Last Updated**: 2025-10-03
