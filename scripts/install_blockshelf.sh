#!/usr/bin/env bash
set -e

APP_USER="blockshelf"
APP_DIR="/opt/blockshelf"
ENV_FILE="/etc/blockshelf/.env"
PYTHON_BIN="python3"
PIP_BIN="pip3"

# Detect distro and set PKG installer & packages
if command -v apt >/dev/null 2>&1; then
  PKG="apt"
  sudo apt update
  sudo apt install -y git python3 python3-venv python3-pip build-essential libpq-dev
elif command -v dnf >/dev/null 2>&1; then
  PKG="dnf"
  sudo dnf install -y git python3 python3-venv python3-pip @development-tools postgresql-devel
elif command -v yum >/dev/null 2>&1; then
  PKG="yum"
  sudo yum groupinstall -y "Development Tools" || true
  sudo yum install -y git python3 python3-venv python3-pip postgresql-devel
elif command -v pacman >/dev/null 2>&1; then
  PKG="pacman"
  sudo pacman -Sy --noconfirm git python python-pip base-devel postgresql-libs
  PYTHON_BIN="python"
  PIP_BIN="pip"
else
  echo "Unsupported Linux distribution (need apt, dnf, yum, or pacman)."
  exit 1
fi

# Create app user if not exists
if ! id -u "$APP_USER" >/dev/null 2>&1; then
  sudo useradd --system --create-home --home-dir /var/lib/$APP_USER --shell /usr/sbin/nologin $APP_USER
fi

# Create directories
sudo mkdir -p "$APP_DIR" /var/log/blockshelf /run/blockshelf /etc/blockshelf
sudo chown -R $APP_USER:$APP_USER "$APP_DIR" /var/log/blockshelf /run/blockshelf /etc/blockshelf

# Fetch source (clone or update)
if [ -d "$APP_DIR/.git" ]; then
  sudo -u $APP_USER git -C "$APP_DIR" pull --ff-only
else
  sudo -u $APP_USER git clone https://github.com/DarkSmileee/BlockShelf.git "$APP_DIR"
fi

# Create virtualenv
if [ ! -d "$APP_DIR/.venv" ]; then
  sudo -u $APP_USER $PYTHON_BIN -m venv "$APP_DIR/.venv"
fi

# Install Python deps
sudo -u $APP_USER "$APP_DIR/.venv/bin/pip" install --upgrade pip wheel
sudo -u $APP_USER "$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt" gunicorn

# Generate default .env if missing
if [ ! -f "$ENV_FILE" ]; then
  SECRET_KEY=$("$APP_DIR/.venv/bin/python" - <<'PY'\nimport secrets; print(secrets.token_urlsafe(50))\nPY\n)
  cat <<EOF | sudo tee "$ENV_FILE" >/dev/null
# === BlockShelf environment ===
DEBUG=False
SITE_ID=1
ALLOW_REGISTRATION=True
# If you expose via domain, set ALLOWED_HOSTS accordingly, e.g. "example.com"
ALLOWED_HOSTS=*
# SQLite default; replace with Postgres URL if desired:
DATABASE_URL=sqlite:///$APP_DIR/db.sqlite3
# Optional integrations
ACCOUNT_EMAIL_VERIFICATION=none
ACCOUNT_EMAIL_REQUIRED=False
REBRICKABLE_API_KEY=
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
# Django secret
SECRET_KEY=$SECRET_KEY
EOF
  sudo chown $APP_USER:$APP_USER "$ENV_FILE"
  sudo chmod 640 "$ENV_FILE"
fi

# Django setup: migrate, create cache table, collectstatic
sudo -u $APP_USER envdir=$(dirname "$ENV_FILE"); set -a; source "$ENV_FILE"; set +a; \
  "$APP_DIR/.venv/bin/python" "$APP_DIR/manage.py" migrate --noinput
sudo -u $APP_USER "$APP_DIR/.venv/bin/python" "$APP_DIR/manage.py" createcachetable
sudo -u $APP_USER "$APP_DIR/.venv/bin/python" "$APP_DIR/manage.py" collectstatic --noinput

# Optional: create admin user if env vars provided
if [ -n "$BS_ADMIN_USER" ] && [ -n "$BS_ADMIN_EMAIL" ] && [ -n "$BS_ADMIN_PASSWORD" ]; then
  sudo -u $APP_USER "$APP_DIR/.venv/bin/python" "$APP_DIR/manage.py" shell <<PY
from django.contrib.auth import get_user_model
User=get_user_model()
u,created=User.objects.get_or_create(username="${BS_ADMIN_USER}", defaults={"email":"${BS_ADMIN_EMAIL}"})
if created:
    u.set_password("${BS_ADMIN_PASSWORD}"); u.is_superuser=True; u.is_staff=True; u.save(); print("Created admin user")
else:
    print("Admin user exists")
PY
fi

# Install systemd service
SERVICE_PATH="/etc/systemd/system/blockshelf.service"
cat <<'UNIT' | sudo tee "$SERVICE_PATH" >/dev/null
[Unit]
Description=BlockShelf (Django) service
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=blockshelf
Group=blockshelf
WorkingDirectory=/opt/blockshelf
EnvironmentFile=/etc/blockshelf/.env
RuntimeDirectory=blockshelf
ExecStart=/opt/blockshelf/.venv/bin/gunicorn --workers 3 --timeout 60 --bind 0.0.0.0:8000 blockshelf_inventory.wsgi:application
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
UNIT

sudo systemctl daemon-reload
sudo systemctl enable blockshelf.service
sudo systemctl restart blockshelf.service

echo "-------------------------------------------"
echo "BlockShelf installed."
echo "Service:   systemctl status blockshelf"
echo "Listening: http://localhost:8000"
echo "Env file:  $ENV_FILE"
echo "Code dir:  $APP_DIR"
echo "-------------------------------------------"
