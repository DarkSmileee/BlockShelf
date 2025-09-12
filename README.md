# Blockshelf Inventory Management (Django + Bootstrap 5)

A self-hosted web app to manage your personal Blockshelf parts inventory. Multiple users can sign in,
keep private inventories, import/export CSV, and look up part details via the Rebrickable API.

## Features
- User accounts (local username/password) + optional Google login (via `django-allauth`).
- Add, edit, delete, search, and filter your Blockshelf parts.
- Import/Export inventory to/from CSV.
- Rebrickable API lookup to auto-fill part details (name, image), by part ID.
- Clean, responsive UI using Bootstrap 5 and a Blockshelf-inspired theme.

## Prerequisites
- Python 3.10+ (recommended 3.11).
- (Optional) Rebrickable API key (free): https://rebrickable.com/api/
- (Optional) Google OAuth Client ID & Secret for social login: https://console.cloud.google.com/apis/credentials

## Quickstart (Development)
```bash
# 1) Create and activate a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # on Windows: .venv\Scripts\activate

# 2) Install dependencies
pip install -r requirements.txt

# 3) Create the database (with app migrations)
python manage.py migrate

# (If Django asks to make migrations for 'inventory', run:)
# python manage.py makemigrations inventory && python manage.py migrate

# 4) Create a superuser to access the Django admin
python manage.py createsuperuser

# 5) Run the dev server
python manage.py runserver
```
Visit http://127.0.0.1:8000/ — you’ll be redirected to the login page. After logging in,
you’ll land on **My Inventory**.

## Configuration
Open `blockshelf_inventory/settings.py` and review these settings:

- `ALLOW_REGISTRATION = True`  
  Set to `False` to disable self-signups (useful for private deployments).

- `REBRICKABLE_API_KEY`  
  By default, reads from the environment variable `REBRICKABLE_API_KEY`.  
  Alternatively, edit the placeholder value directly in `settings.py`.  
  The **Lookup** button on the Add/Edit item page calls:
  `GET https://rebrickable.com/api/v3/blockshelf/parts/<part_id>/`

- Google OAuth (optional) via `django-allauth`  
  In `settings.py` the `SOCIALACCOUNT_PROVIDERS['google']['APP']` block contains placeholders
  for `client_id` and `secret`. Fill those in. Then, in Django Admin → **Sites** (id=1) set your
  domain (e.g., `localhost:8000`), and in **Social Applications** add a Google social app
  linked to that site. The login template already shows a “Login with Google” button.

- Static files: Bootstrap 5 and Google Fonts are loaded via CDN for simplicity.

## CSV Import/Export
- **Export**: Click **Export CSV** on the inventory page to download all your items.
- **Import**: Click **Import CSV**, select a CSV with a header row like:
  ```csv
  name,part_id,color,quantity_total,quantity_used,storage_location,image_url,notes
  2x4 Brick,3001,Red,50,10,Bin A1,https://...,Some note
  ```
  Existing items are matched by **part_id + color** and updated; otherwise, new items are created.

## Project Structure
```
blockshelf-inventory/
├─ manage.py
├─ requirements.txt
├─ README.md
├─ blockshelf_inventory/
│  ├─ settings.py
│  ├─ urls.py
│  ├─ wsgi.py
│  └─ asgi.py
├─ inventory/
│  ├─ models.py, views.py, forms.py, admin.py, urls.py, tests.py
│  └─ migrations/
├─ templates/
│  ├─ base.html
│  ├─ registration/login.html
│  ├─ signup.html
│  └─ inventory/*.html
└─ static/
   ├─ css/blockshelf.css
   └─ img/brick.svg
```

## Notes
- **Production**: set `DEBUG = False`, configure `ALLOWED_HOSTS`, static files (e.g. via `collectstatic`), and a real database.
- This project defaults to SQLite for easy local setup.
- The admin is available at `/admin/` (superuser required).

Enjoy and happy building!


## Production & Postgres

### Switch to production settings
- Set `DEBUG=False` in your environment (e.g. `.env`).
- Set `ALLOWED_HOSTS` to your domain or server IP (comma-separated).
- Set a strong `DJANGO_SECRET_KEY` (do **not** commit your real `.env`).

Optional but recommended when using HTTPS:
- `SECURE_SSL_REDIRECT=True`
- Add your domain to `CSRF_TRUSTED_ORIGINS` (e.g. `https://your-domain.com`).

### Use PostgreSQL (recommended for multi-user)
Install Postgres and create a database & user, for example on Ubuntu:

```bash
sudo apt-get update && sudo apt-get install -y postgresql postgresql-contrib
sudo -u postgres psql -c "CREATE USER blockshelf WITH PASSWORD 'change-me';"
sudo -u postgres psql -c "CREATE DATABASE blockshelf OWNER blockshelf;"
```

Set the `DATABASE_URL` in your environment:

```env
DATABASE_URL=postgres://blockshelf:change-me@localhost:5432/blockshelf
```

Apply migrations and collect static files:

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic --noinput
```

Run with a production server (example using Gunicorn):

```bash
pip install gunicorn
gunicorn blockshelf_inventory.wsgi:application --bind 0.0.0.0:8000
```

Put Gunicorn behind Nginx or your reverse proxy and serve over HTTPS.
