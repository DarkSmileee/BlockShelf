<p align="center">
  <img src="docs/branding/blockshelf-logo.png" alt="BlockShelf" width="260" />
</p>

<h1 align="center">BlockShelf</h1>

<p align="center">
  A clean, local‑first LEGO® parts inventory app — import, search, share, and collaborate.
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License: MIT"></a>
  <img src="https://img.shields.io/badge/Python-3.11%2B-blue" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/Django-5.x-blueviolet" alt="Django 5.x">
</p>

---

## ✨ Highlights

- 🔎 **Clean inventory UI** with search, sort, pagination & dark mode
- 📥 **Import** CSV/XLS/XLSX (and export CSV)
- 🧠 **Local‑first part lookups** with Rebrickable API fallback (and BrickLink name fallback)
- 🧩 **Rebrickable Bootstrap**: seed local data from `downloads` ZIP (`colors.csv`, `parts.csv`, `elements.csv`)
- 🔗 **Share & collaborate**: public read‑only links and invite collaborators with edit/delete permissions
- ⚙️ **Admin “Site settings”** (toggle self‑registration, set API keys, email), optional **Google Sign‑in**

> LEGO® is a trademark of the LEGO Group, which does not sponsor, authorize or endorse this project.

---

## 🚀 Quick Start (Local)

```bash
git clone https://github.com/DarkSmileee/BlockShelf.git
cd BlockShelf

python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

pip install -U pip
pip install -r requirements.txt

cp .env.example .env  # or create manually (see below)

python manage.py migrate
python manage.py createcachetable
python manage.py runserver
```

Create an admin user (optional):

```bash
python manage.py createsuperuser
```

---

## ⚙️ Configuration (.env)

```dotenv
DJANGO_SECRET_KEY=change-me
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://127.0.0.1:8000,http://localhost:8000
TIME_ZONE=UTC
SITE_ID=1

# Database (omit for SQLite default)
# DATABASE_URL=postgres://blockshelf:yourpassword@localhost:5432/blockshelf

ALLOW_REGISTRATION=True
REBRICKABLE_API_KEY=
DEFAULT_FROM_EMAIL=noreply@example.com

# Optional Google login
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
```

**Reverse proxy note:** When serving behind HTTPS, add your origin to `CSRF_TRUSTED_ORIGINS` (e.g., `https://blockshelf.example.com`) and ensure the proxy sets `X-Forwarded-Proto: https`.

---

## 🧩 Rebrickable Bootstrap

**Settings → Site settings → Rebrickable Bootstrap**

1) Upload the official Rebrickable **downloads** ZIP (or the separate `colors.csv`, `parts.csv`, `elements.csv` / `.csv.gz`).  
2) Click **Upload & Scan** → **Start Import**.

> ℹ️ **Batch size is per request, not the total.**  
> The importer will loop automatically until **all rows are processed** (colors → parts → elements).  
> If you hit server timeouts, just lower the batch size (e.g., 500–2000).

---

## 👥 Admin & Collaboration

Promote an existing user to staff + superuser:

```bash
python manage.py shell -c "from django.contrib.auth import get_user_model; U=get_user_model(); u=U.objects.get(username='DarkSmile'); u.is_staff=True; u.is_superuser=True; u.save(); print('OK')"
```

Invite collaborators from **Settings → Invite**. You can allow add/edit and optionally delete.  
Create a public read‑only link from **Settings → Sharing**.

---

## 🛡️ Production (Gunicorn + systemd + Traefik)

```ini
# /etc/systemd/system/blockshelf-gunicorn.service
[Unit]
Description=Gunicorn daemon for BlockShelf
After=network.target

[Service]
User=<youruser>
Group=www-data
WorkingDirectory=/srv/blockshelf
Environment="PATH=/srv/blockshelf/.venv/bin"
Environment="DJANGO_SETTINGS_MODULE=blockshelf_inventory.settings"
ExecStart=/srv/blockshelf/.venv/bin/gunicorn   --workers 3   --bind 0.0.0.0:8000   --access-logfile -   blockshelf_inventory.wsgi:application
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Traefik service should forward to `http://<app-ip>:8000`. Don’t forget `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` for your domain.

**Common gotchas**  
- CSRF 403 behind proxy → missing/incorrect `CSRF_TRUSTED_ORIGINS` or `ALLOWED_HOSTS`  
- Static files in prod → run `python manage.py collectstatic --noinput`  
- Import 500s → lower Rebrickable **Batch size**; it still imports everything

---

## 🔄 Upgrading

```bash
git pull --ff-only origin main    # or: git fetch && git reset --hard origin/main && git clean -fd
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart blockshelf-gunicorn
```

---

## 📄 License

Released under the **MIT License** — see [LICENSE](LICENSE).
