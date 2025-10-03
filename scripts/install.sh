#!/bin/bash
# BlockShelf Fresh Installation Script
# This will install BlockShelf from scratch
# WARNING: If BlockShelf is already installed, this will completely remove it!

set -e

APP_DIR="/opt/blockshelf"
APP_USER="blockshelf"
SERVICE_NAME="blockshelf"
ENV_FILE="/etc/blockshelf/.env"

echo "╔════════════════════════════════════════╗"
echo "║   BlockShelf Fresh Installation        ║"
echo "╚════════════════════════════════════════╝"
echo ""

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    echo "❌ This script must be run as root (use sudo)"
    exit 1
fi

# Check if BlockShelf already exists
if [ -d "$APP_DIR" ] || [ -f "$ENV_FILE" ] || systemctl list-unit-files | grep -q "^$SERVICE_NAME.service"; then
    echo "⚠️  WARNING: Existing BlockShelf installation detected!"
    echo ""
    echo "This will:"
    echo "  • Stop and remove the BlockShelf service"
    echo "  • Delete all files in $APP_DIR"
    echo "  • Delete configuration in /etc/blockshelf"
    echo "  • DROP and recreate the PostgreSQL database (ALL DATA WILL BE LOST)"
    echo ""
    read -p "Type 'YES' to continue with fresh installation: " confirm

    if [ "$confirm" != "YES" ]; then
        echo "Installation cancelled."
        exit 0
    fi

    echo ""
    echo "→ Removing existing installation..."

    # Stop and disable service
    systemctl stop $SERVICE_NAME 2>/dev/null || true
    systemctl disable $SERVICE_NAME 2>/dev/null || true
    rm -f /etc/systemd/system/$SERVICE_NAME.service
    systemctl daemon-reload

    # Remove files
    rm -rf $APP_DIR
    rm -rf /etc/blockshelf

    # Drop database
    sudo -u postgres psql -c "DROP DATABASE IF EXISTS blockshelf;"
    sudo -u postgres psql -c "DROP USER IF EXISTS blockshelf;"

    echo "✓ Cleanup complete"
    echo ""
fi

echo "→ Installing system dependencies..."
apt-get update
apt-get install -y python3 python3-pip python3-venv git nginx certbot python3-certbot-nginx postgresql postgresql-contrib

echo "→ Creating blockshelf user..."
if ! id -u $APP_USER > /dev/null 2>&1; then
    useradd --system --home-dir $APP_DIR --create-home --shell /bin/bash $APP_USER
fi

echo "→ Setting up PostgreSQL..."
# Generate random password
DB_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
sudo -u postgres psql -c "CREATE USER blockshelf WITH PASSWORD '$DB_PASSWORD';"
sudo -u postgres psql -c "CREATE DATABASE blockshelf OWNER blockshelf;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE blockshelf TO blockshelf;"

echo "→ Cloning repository..."
sudo -u $APP_USER git clone https://github.com/DarkSmileee/BlockShelf.git $APP_DIR

echo "→ Creating virtual environment..."
sudo -u $APP_USER python3 -m venv $APP_DIR/.venv

echo "→ Installing Python dependencies..."
sudo -u $APP_USER $APP_DIR/.venv/bin/pip install --upgrade pip
sudo -u $APP_USER $APP_DIR/.venv/bin/pip install -r $APP_DIR/requirements.txt

echo "→ Setting up configuration..."
mkdir -p /etc/blockshelf

# Generate Django secret key
DJANGO_SECRET=$(openssl rand -base64 50 | tr -d "=+/" | cut -c1-50)

cat > $ENV_FILE << ENVEOF
# Django settings
DJANGO_SECRET_KEY=$DJANGO_SECRET
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DATABASE_URL=postgresql://blockshelf:$DB_PASSWORD@localhost:5432/blockshelf

# Email (optional - configure for production)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
DEFAULT_FROM_EMAIL=noreply@blockshelf.local

# App settings
ALLOW_REGISTRATION=True
REBRICKABLE_API_KEY=

# django-allauth
ACCOUNT_EMAIL_VERIFICATION=none
ENVEOF

chmod 640 $ENV_FILE
chown root:$APP_USER $ENV_FILE

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
echo "Database credentials have been saved to: $ENV_FILE"
echo ""
echo "Next steps:"
echo "  1. Update DJANGO_ALLOWED_HOSTS in $ENV_FILE with your domain"
echo "  2. Configure Nginx (see documentation)"
echo "  3. Set up SSL: certbot --nginx -d your-domain.com"
echo "  4. Create superuser:"
echo "     sudo -u blockshelf bash -c 'source $ENV_FILE && $APP_DIR/.venv/bin/python $APP_DIR/manage.py createsuperuser'"
echo ""
echo "Check service status: sudo systemctl status $SERVICE_NAME"
echo "View logs: sudo journalctl -u $SERVICE_NAME -f"
echo ""
