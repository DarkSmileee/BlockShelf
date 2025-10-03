#!/bin/bash
# BlockShelf Deployment Script
# Usage:
#   Fresh install: sudo bash deploy_blockshelf.sh install
#   Update:        sudo bash deploy_blockshelf.sh update

set -e

MODE="${1:-update}"
APP_DIR="/opt/blockshelf"
APP_USER="blockshelf"
SERVICE_NAME="blockshelf"
ENV_FILE="/etc/blockshelf/.env"

echo "╔════════════════════════════════════════╗"
echo "║     BlockShelf Deployment Script      ║"
echo "╚════════════════════════════════════════╝"
echo ""

# ============================================================================
# INSTALL MODE - Fresh installation
# ============================================================================
if [ "$MODE" = "install" ]; then
    echo "==> FRESH INSTALLATION MODE"
    echo ""

    # Check if running as root
    if [ "$(id -u)" -ne 0 ]; then
        echo "❌ This script must be run as root (use sudo)"
        exit 1
    fi

    echo "→ Installing system dependencies..."
    apt-get update
    apt-get install -y python3 python3-pip python3-venv git nginx certbot python3-certbot-nginx postgresql postgresql-contrib

    echo "→ Creating blockshelf user..."
    if ! id -u $APP_USER > /dev/null 2>&1; then
        useradd --system --home-dir $APP_DIR --create-home --shell /bin/bash $APP_USER
    fi

    echo "→ Setting up PostgreSQL..."
    sudo -u postgres psql -c "CREATE USER blockshelf WITH PASSWORD 'your_secure_password';" 2>/dev/null || echo "User already exists"
    sudo -u postgres psql -c "CREATE DATABASE blockshelf OWNER blockshelf;" 2>/dev/null || echo "Database already exists"
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE blockshelf TO blockshelf;"

    echo "→ Cloning repository..."
    if [ ! -d "$APP_DIR/.git" ]; then
        sudo -u $APP_USER git clone https://github.com/DarkSmileee/BlockShelf.git $APP_DIR
    fi

    echo "→ Creating virtual environment..."
    sudo -u $APP_USER python3 -m venv $APP_DIR/.venv

    echo "→ Installing Python dependencies..."
    sudo -u $APP_USER $APP_DIR/.venv/bin/pip install --upgrade pip
    sudo -u $APP_USER $APP_DIR/.venv/bin/pip install -r $APP_DIR/requirements.txt

    echo "→ Setting up configuration..."
    mkdir -p /etc/blockshelf
    if [ ! -f "$ENV_FILE" ]; then
        cat > $ENV_FILE << 'ENVEOF'
# Django settings
DJANGO_SECRET_KEY=change_me_to_random_string
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=your-domain.com

# Database
DATABASE_URL=postgresql://blockshelf:your_secure_password@localhost:5432/blockshelf

# Email (optional)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
DEFAULT_FROM_EMAIL=noreply@your-domain.com

# App settings
ALLOW_REGISTRATION=True
REBRICKABLE_API_KEY=

# django-allauth
ACCOUNT_EMAIL_VERIFICATION=none
ENVEOF
        echo "⚠️  Created $ENV_FILE - EDIT THIS FILE before continuing!"
        echo "    Update: DJANGO_SECRET_KEY, DJANGO_ALLOWED_HOSTS, DATABASE_URL password"
        exit 0
    fi

    echo "→ Running migrations..."
    sudo -u $APP_USER bash -c "set -a; source $ENV_FILE; set +a; cd $APP_DIR && $APP_DIR/.venv/bin/python manage.py migrate --noinput"

    echo "→ Collecting static files..."
    sudo -u $APP_USER bash -c "set -a; source $ENV_FILE; set +a; cd $APP_DIR && $APP_DIR/.venv/bin/python manage.py collectstatic --noinput"

    echo "→ Creating systemd service..."
    cat > /etc/systemd/system/$SERVICE_NAME.service << 'SERVICEEOF'
[Unit]
Description=BlockShelf Gunicorn Service
After=network.target

[Service]
Type=notify
User=blockshelf
Group=blockshelf
RuntimeDirectory=blockshelf
WorkingDirectory=/opt/blockshelf
EnvironmentFile=/etc/blockshelf/.env
ExecStart=/opt/blockshelf/.venv/bin/gunicorn \
    --config /opt/blockshelf/gunicorn.conf.py \
    blockshelf_inventory.wsgi:application
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true

[Install]
WantedBy=multi-user.target
SERVICEEOF

    echo "→ Enabling and starting service..."
    systemctl daemon-reload
    systemctl enable $SERVICE_NAME
    systemctl start $SERVICE_NAME

    echo ""
    echo "✓ Installation complete!"
    echo ""
    echo "Next steps:"
    echo "  1. Configure Nginx (see docs)"
    echo "  2. Set up SSL with: certbot --nginx -d your-domain.com"
    echo "  3. Create superuser: sudo -u blockshelf bash -c 'source $ENV_FILE && $APP_DIR/.venv/bin/python $APP_DIR/manage.py createsuperuser'"
    echo ""
    exit 0
fi

# ============================================================================
# UPDATE MODE - Update existing installation
# ============================================================================
if [ "$MODE" = "update" ]; then
    echo "==> UPDATE MODE"
    echo ""

    # Check if installation exists
    if [ ! -d "$APP_DIR" ]; then
        echo "❌ BlockShelf not found at $APP_DIR"
        echo "   Run: sudo bash deploy_blockshelf.sh install"
        exit 1
    fi

    echo "→ Pulling latest code from GitHub..."
    sudo -u $APP_USER git -C "$APP_DIR" pull

    echo "→ Cleaning Python bytecode cache..."
    sudo -u $APP_USER find "$APP_DIR" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
    sudo -u $APP_USER find "$APP_DIR" -name "*.pyc" -delete 2>/dev/null || true

    echo "→ Installing/updating Python dependencies..."
    sudo -u $APP_USER $APP_DIR/.venv/bin/pip install -r $APP_DIR/requirements.txt --upgrade

    echo "→ Creating any new migrations..."
    sudo -u $APP_USER bash -c "set -a; source $ENV_FILE; set +a; cd $APP_DIR && $APP_DIR/.venv/bin/python manage.py makemigrations --noinput" || true

    echo "→ Running database migrations..."
    sudo -u $APP_USER bash -c "set -a; source $ENV_FILE; set +a; cd $APP_DIR && $APP_DIR/.venv/bin/python manage.py migrate --noinput"

    echo "→ Collecting static files..."
    sudo -u $APP_USER bash -c "set -a; source $ENV_FILE; set +a; cd $APP_DIR && $APP_DIR/.venv/bin/python manage.py collectstatic --noinput"

    echo "→ Restarting BlockShelf service..."
    systemctl restart $SERVICE_NAME

    echo "→ Checking service status..."
    sleep 2
    systemctl status $SERVICE_NAME --no-pager -l || true

    echo ""
    echo "✓ Update complete!"
    echo "  Check logs: sudo journalctl -u $SERVICE_NAME -n 50"
    echo ""
    exit 0
fi

echo "❌ Invalid mode: $MODE"
echo "Usage: sudo bash deploy_blockshelf.sh [install|update]"
exit 1
