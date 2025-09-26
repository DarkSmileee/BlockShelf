#!/usr/bin/env bash
set -euo pipefail

APP_USER="blockshelf"
APP_GROUP="blockshelf"
APP_DIR="/opt/blockshelf"
ENV_DIR="/etc/blockshelf"
ENV_FILE="$ENV_DIR/.env"
SERVICE_NAME="blockshelf"
PYTHON_BIN="python3"
PIP_BIN="pip3"

echo "==> Detecting distro & installing dependencies..."
if command -v apt >/dev/null 2>&1; then
  sudo apt update
  sudo apt install -y git python3 python3-venv python3-pip build-essential libpq-dev
elif command -v dnf >/dev/null 2>&1; then
  sudo dnf install -y git python3 python3-venv python3-pip @development-tools postgresql-devel
elif command -v yum >/dev/null 2>&1; then
  sudo yum groupinstall -y "Development Tools" || true
  sudo yum install -y git python3 python3-venv python3-pip postgresql-devel
elif command -v pacman >/dev/null 2>&1; then
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
  sudo -u $APP_USER git clone https://github.com/DarkSmileee/BlockShelf.git "$APP_DIR"
fi

echo "==> Creating virtualenv & installing Python deps..."
if [ ! -d "$APP_DIR/.venv" ]; then
  sudo -u $APP_USER $PYTHON_BIN -m venv "$APP_DIR/.venv"
fi
sudo -u $APP_USER "$APP_DIR/.venv/bin/pip" install --upgrade pip wheel
sudo -u $APP_USER "$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt" gunicorn

echo "==> Preparing environment file..."
# Copy repo .env.example to /etc/blockshelf/.env if missing, else keep user's edits
if [ ! -f "$ENV_FILE" ]; then
  if [ -f "$APP_DIR/.env.example" ]; then
    sudo cp "$APP_DIR/.env.example" "$ENV_FILE"
    sudo chown $APP_USER:$APP_GROUP "$ENV_FILE"
    sudo chmod 640 "$ENV_FILE"
    echo "   - Copied $APP_DIR/.env.example -> $ENV_FILE"
  else
    # Fallback minimal env if example is missing
    sudo tee "$ENV_FILE" >/dev/null <<EOF
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=sqlite:////opt/blockshelf/db.sqlite3
DJANGO_SECRET_KEY=CHANGE_ME
EOF
    sudo chown $APP_USER:$APP_GROUP "$ENV_FILE"
    sudo chmod 640 "$ENV_FILE"
    echo "   - Wrote minimal $ENV_FILE"
  fi
else
  echo "   - $ENV_FILE exists; not overwriting."
fi

# Generate a strong secret key and SHOW IT to the user (do not auto-write)
SECRET_KEY=$("$APP_DIR/.venv/bin/python" -c 'import secrets; print(secrets.token_urlsafe(64))')
echo
echo "====================  ACTION REQUIRED  ===================="
echo "Generated Django secret key (copy this):"
echo
echo "DJANGO_SECRET_KEY=$SECRET_KEY"
echo
echo "Open your env and paste/update DJANGO_SECRET_KEY, then save:"
echo "  sudo nano $ENV_FILE"
echo "==========================================================="
echo

# Try to run Django setup with the current env (even if key isn't updated yet)
echo "==> Running Django migrations & collectstatic..."
set +e
sudo -u $APP_USER envdir=$(dirname "$ENV_FILE"); set -a; source "$ENV_FILE"; set +a; \
  "$APP_DIR/.venv/bin/python" "$APP_DIR/manage.py" migrate --noinput
MIG_EXIT=$?
sudo -u $APP_USER "$APP_DIR/.venv/bin/python" "$APP_DIR/manage.py" createcachetable || true
sudo -u $APP_USER "$APP_DIR/.venv/bin/python" "$APP_DIR/manage.py" collectstatic --noinput || true
set -e
if [ "$MIG_EXIT" -ne 0 ]; then
  echo "   - Migrations returned a non-zero exit (likely due to env). You can re-run after editing the env:"
  echo "     sudo -u $APP_USER $APP_DIR/.venv/bin/python $APP_DIR/manage.py migrate --noinput"
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
sudo systemctl enable --now ${SERVICE_NAME}.service || true

echo
echo "-------------------------------------------"
echo "BlockShelf installed (service may start)."
echo "Service:     sudo systemctl status $SERVICE_NAME"
echo "Listening:   http://localhost:8000"
echo "Code dir:    $APP_DIR"
echo "Env file:    $ENV_FILE"
echo "-------------------------------------------"
echo
echo "NEXT STEPS:"
echo "1) Edit your env and paste the secret:"
echo "     sudo nano $ENV_FILE"
echo "2) (Optional) Adjust ALLOWED_HOSTS / CSRF_TRUSTED_ORIGINS / DATABASE_URL"
echo "3) Apply migrations and restart once env is saved:"
echo "     sudo -u $APP_USER $APP_DIR/.venv/bin/python $APP_DIR/manage.py migrate --noinput"
echo "     sudo -u $APP_USER $APP_DIR/.venv/bin/python $APP_DIR/manage.py collectstatic --noinput"
echo "     sudo systemctl restart $SERVICE_NAME"
echo
