#!/usr/bin/env bash
set -euo pipefail

# =========================
# BlockShelf One-Step Installer (interactive)
# =========================

APP_USER="blockshelf"
APP_GROUP="blockshelf"
APP_DIR="/opt/blockshelf"
ENV_DIR="/etc/blockshelf"
ENV_FILE="$ENV_DIR/.env"
SERVICE_NAME="blockshelf"
PYTHON_BIN="python3"
PIP_BIN="pip3"
REPO_URL="https://github.com/DarkSmileee/BlockShelf.git"

echo "==> Detecting distro & installing base deps..."
PKG=""
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

echo "==> Ensuring system user/group..."
if ! id -u "$APP_USER" >/dev/null 2>&1; then
  sudo useradd --system --create-home --home-dir /var/lib/$APP_USER --shell /usr/sbin/nologin $APP_USER
fi

echo "==> Creating directories..."
sudo mkdir -p "$APP_DIR" "$ENV_DIR" /var/log/$SERVICE_NAME /run/$SERVICE_NAME
sudo chown -R $APP_USER:$APP_GROUP "$APP_DIR" "$ENV_DIR" /var/log/$SERVICE_NAME /run/$SERVICE_NAME

echo "==> Cloning or updating repository..."
if [ -d "$APP_DIR/.git" ]; then
  sudo -u $APP_USER git -C "$APP_DIR" pull --ff-only
else
  sudo -u $APP_USER git clone "$REPO_URL" "$APP_DIR"
fi

echo "==> Creating virtualenv & installing Python deps..."
if [ ! -d "$APP_DIR/.venv" ]; then
  sudo -u $APP_USER $PYTHON_BIN -m venv "$APP_DIR/.venv"
fi
sudo -u $APP_USER "$APP_DIR/.venv/bin/pip" install --upgrade pip wheel
sudo -u $APP_USER "$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt" gunicorn

# ------------------------------
# Interactive config (TTY-safe)
# ------------------------------
echo
echo "==> Configuration (press Enter for defaults)"
read -r -p "ALLOWED_HOSTS (default: localhost,127.0.0.1): " ALLOWED_HOSTS_INPUT </dev/tty || true
ALLOWED_HOSTS="${ALLOWED_HOSTS_INPUT:-localhost,127.0.0.1}"

read -r -p "CSRF_TRUSTED_ORIGINS (default: http://localhost:8000): " CSRF_INPUT </dev/tty || true
CSRF_TRUSTED_ORIGINS="${CSRF_INPUT:-http://localhost:8000}"

read -r -p "Use PostgreSQL? [Y/n] " USEPG_IN </dev/tty || true
USEPG="${USEPG_IN:-Y}"

# Secret key (allow auto-generate)
read -r -p "DJANGO_SECRET_KEY (leave empty to auto-generate): " DJANGO_SECRET_KEY_IN </dev/tty || true
if [ -z "${DJANGO_SECRET_KEY_IN:-}" ]; then
  DJANGO_SECRET_KEY_IN="$("$APP_DIR/.venv/bin/python" -c 'import secrets; print(secrets.token_urlsafe(64))')"
  echo
  echo "Generated Django secret key (will be written to env):"
  echo "DJANGO_SECRET_KEY=$DJANGO_SECRET_KEY_IN"
  echo
fi
DJANGO_SECRET_KEY="$DJANGO_SECRET_KEY_IN"

DB_URL="sqlite:////opt/blockshelf/db.sqlite3"
DB_SUMMARY="SQLite"

if [[ "$USEPG" =~ ^[Yy]$ ]]; then
  echo "==> Installing PostgreSQL server (if missing) and creating DB/user..."
  # Install & init postgres server per distro
  if [ "$PKG" = "apt" ]; then
    sudo apt install -y postgresql
    sudo systemctl enable --now postgresql
  elif [ "$PKG" = "dnf" ]; then
    sudo dnf install -y postgresql-server postgresql
    if [ ! -d /var/lib/pgsql/data ]; then
      sudo postgresql-setup --initdb
    fi
    sudo systemctl enable --now postgresql
  elif [ "$PKG" = "yum" ]; then
    sudo yum install -y postgresql-server postgresql
    if [ ! -d /var/lib/pgsql/data ]; then
      sudo postgresql-setup --initdb
    fi
    sudo systemctl enable --now postgresql
  elif [ "$PKG" = "pacman" ]; then
    sudo pacman -Sy --noconfirm postgresql
    if [ ! -d /var/lib/postgres/data/base ]; then
      sudo -u postgres initdb -D /var/lib/postgres/data
    fi
    sudo systemctl enable --now postgresql
  fi

  # Ask for DB params
  read -r -p "Postgres DB name (default: blockshelf): " PG_DB_IN </dev/tty || true
  PG_DB="${PG_DB_IN:-blockshelf}"
  read -r -p "Postgres user (default: blockshelf): " PG_USER_IN </dev/tty || true
  PG_USER="${PG_USER_IN:-blockshelf}"
  # Silent password prompt
  read -s -r -p "Postgres password for user ${PG_USER}: " PG_PASS </dev/tty || true; echo
  # escape single quotes for SQL
  PGPASS_ESC=$(printf "%s" "$PG_PASS" | sed "s/'/''/g")

  # Create role idempotently (OK in DO)
  sudo -u postgres psql -v ON_ERROR_STOP=1 -c "DO \$\$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='${PG_USER}') THEN
      CREATE ROLE ${PG_USER} LOGIN PASSWORD '${PGPASS_ESC}';
    END IF;
  END \$\$;"

  # Create database OUTSIDE a DO / transaction
  if ! sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='${PG_DB}'" | grep -q 1; then
    sudo -u postgres psql -v ON_ERROR_STOP=1 -c "CREATE DATABASE ${PG_DB} OWNER ${PG_USER}"
  fi

  # Ensure privileges
  sudo -u postgres psql -v ON_ERROR_STOP=1 -d postgres -c "GRANT ALL PRIVILEGES ON DATABASE ${PG_DB} TO ${PG_USER}"

  DB_URL="postgres://${PG_USER}:${PG_PASS}@localhost:5432/${PG_DB}"
  DB_SUMMARY="PostgreSQL (${PG_DB} as ${PG_USER})"
fi

echo "==> Writing env to $ENV_FILE"
sudo tee "$ENV_FILE" >/dev/null <<EOF
# --- Django ---
DJANGO_SECRET_KEY=${DJANGO_SECRET_KEY}
DEBUG=False
ALLOWED_HOSTS=${ALLOWED_HOSTS}
CSRF_TRUSTED_ORIGINS=${CSRF_TRUSTED_ORIGINS}
TIME_ZONE=Europe/Brussels

# --- Database ---
DATABASE_URL=${DB_URL}

# --- Security (production defaults) ---
SECURE_SSL_REDIRECT=True
CSRF_COOKIE_SECURE=True
SESSION_COOKIE_SECURE=True

# --- Auth / Allauth ---
ACCOUNT_EMAIL_VERIFICATION=none
ACCOUNT_EMAIL_REQUIRED=false

# --- Email (console) ---
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
DEFAULT_FROM_EMAIL=noreply@example.com

# --- Optional integrations ---
REBRICKABLE_API_KEY=
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
EOF
sudo chown $APP_USER:$APP_GROUP "$ENV_FILE"
sudo chmod 640 "$ENV_FILE"

echo "==> Running Django migrations & collectstatic..."
sudo -u $APP_USER bash -lc 'set -euo pipefail; set -a; source '"$ENV_FILE"'; set +a; '"$APP_DIR"'/.venv/bin/python '"$APP_DIR"'/manage.py migrate --noinput'
sudo -u $APP_USER bash -lc 'set -euo pipefail; set -a; source '"$ENV_FILE"'; set +a; '"$APP_DIR"'/.venv/bin/python '"$APP_DIR"'/manage.py createcachetable || true'
sudo -u $APP_USER bash -lc 'set -euo pipefail; set -a; source '"$ENV_FILE"'; set +a; '"$APP_DIR"'/.venv/bin/python '"$APP_DIR"'/manage.py collectstatic --noinput || true'

echo "==> (Optional) Create Django superuser"
read -r -p "Create an admin user now? [Y/n] " MAKE_ADMIN </dev/tty || true
MAKE_ADMIN="${MAKE_ADMIN:-Y}"

if [[ "$MAKE_ADMIN" =~ ^[Yy]$ ]]; then
  read -r -p "Admin username (default: admin): " ADMIN_USER </dev/tty || true
  ADMIN_USER="${ADMIN_USER:-admin}"

  read -r -p "Admin email (default: admin@example.com): " ADMIN_EMAIL </dev/tty || true
  ADMIN_EMAIL="${ADMIN_EMAIL:-admin@example.com}"

  # silent password twice
  while true; do
    read -s -r -p "Admin password: " ADMIN_PASS1 </dev/tty || true; echo
    read -s -r -p "Repeat admin password: " ADMIN_PASS2 </dev/tty || true; echo
    if [[ "${ADMIN_PASS1:-}" == "${ADMIN_PASS2:-}" && -n "${ADMIN_PASS1:-}" ]]; then
      break
    else
      echo "Passwords do not match or are empty. Try again."
    fi
  done

  # Use the official non-interactive flow (manage.py sets DJANGO_SETTINGS_MODULE)
  sudo -u $APP_USER bash -lc 'set -euo pipefail; set -a; source '"$ENV_FILE"'; set +a; \
    DJANGO_SUPERUSER_USERNAME='"$ADMIN_USER"' \
    DJANGO_SUPERUSER_EMAIL='"$ADMIN_EMAIL"' \
    DJANGO_SUPERUSER_PASSWORD='"$ADMIN_PASS1"' \
    '"$APP_DIR"'/.venv/bin/python '"$APP_DIR"'/manage.py createsuperuser --noinput || true'
fi

echo "==> Installing systemd service..."
SERVICE_PATH="/etc/systemd/system/${SERVICE_NAME}.service"
sudo tee "$SERVICE_PATH" >/dev/null <<'UNIT'
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
sudo systemctl enable --now ${SERVICE_NAME}.service

echo
echo "-------------------------------------------"
echo "BlockShelf installed & started."
echo "Service:     sudo systemctl status $SERVICE_NAME"
echo "Listening:   http://localhost:8000"
echo "Code dir:    $APP_DIR"
echo "Env file:    $ENV_FILE"
echo "Database:    $DB_SUMMARY"
echo "-------------------------------------------"
