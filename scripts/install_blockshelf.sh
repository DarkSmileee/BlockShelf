#!/bin/bash
# BlockShelf Interactive Installation Script
# This will install BlockShelf from scratch with interactive configuration

set -e

APP_DIR="/opt/blockshelf"
APP_USER="blockshelf"
SERVICE_NAME="blockshelf"
ENV_FILE="/etc/blockshelf/.env"

# TTY check for interactive mode
if [ -t 0 ]; then
    INTERACTIVE=1
else
    INTERACTIVE=0
fi

echo "╔════════════════════════════════════════╗"
echo "║   BlockShelf Interactive Installation  ║"
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

    if [ $INTERACTIVE -eq 1 ]; then
        read -p "Type 'YES' to continue with fresh installation: " confirm
    else
        echo "Non-interactive mode: Skipping cleanup. Use update.sh instead."
        exit 1
    fi

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

    # Stop and disable backup timer if exists
    systemctl stop blockshelf-backup.timer 2>/dev/null || true
    systemctl disable blockshelf-backup.timer 2>/dev/null || true
    rm -f /etc/systemd/system/blockshelf-backup.service 2>/dev/null || true
    rm -f /etc/systemd/system/blockshelf-backup.timer 2>/dev/null || true

    systemctl daemon-reload

    # Remove files
    rm -rf $APP_DIR
    rm -rf /etc/blockshelf

    # Drop database
    sudo -u postgres psql -c "DROP DATABASE IF EXISTS blockshelf;" 2>/dev/null || true
    sudo -u postgres psql -c "DROP USER IF EXISTS blockshelf;" 2>/dev/null || true

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

# Interactive configuration
echo ""
echo "═══════════════════════════════════════"
echo "  Configuration"
echo "═══════════════════════════════════════"
echo ""

if [ $INTERACTIVE -eq 1 ]; then
    # Domain/hostname
    read -p "Enter your domain or IP (default: localhost): " DOMAIN
    DOMAIN=${DOMAIN:-localhost}

    # Allow registration
    read -p "Allow user registration? (yes/no, default: yes): " ALLOW_REG
    ALLOW_REG=${ALLOW_REG:-yes}
    if [ "$ALLOW_REG" = "yes" ]; then
        ALLOW_REGISTRATION="True"
    else
        ALLOW_REGISTRATION="False"
    fi

    # Email configuration
    read -p "Configure email? (yes/no, default: no): " SETUP_EMAIL
    if [ "$SETUP_EMAIL" = "yes" ]; then
        read -p "SMTP Host: " SMTP_HOST
        read -p "SMTP Port (default: 587): " SMTP_PORT
        SMTP_PORT=${SMTP_PORT:-587}
        read -p "SMTP Username: " SMTP_USER
        read -sp "SMTP Password: " SMTP_PASS
        echo ""
        read -p "From Email: " FROM_EMAIL
        EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend"
    else
        EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend"
        FROM_EMAIL="noreply@blockshelf.local"
    fi

    # Rebrickable API
    read -p "Rebrickable API Key (optional, press Enter to skip): " REBRICKABLE_KEY

    # Backup setup
    read -p "Setup automatic daily backups? (yes/no, default: yes): " SETUP_BACKUPS
    SETUP_BACKUPS=${SETUP_BACKUPS:-yes}
else
    # Non-interactive defaults
    DOMAIN="localhost"
    ALLOW_REGISTRATION="True"
    EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend"
    FROM_EMAIL="noreply@blockshelf.local"
    REBRICKABLE_KEY=""
    SETUP_BACKUPS="yes"
fi

echo ""
echo "→ Setting up PostgreSQL..."
# Generate random password
DB_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
sudo -u postgres psql -c "CREATE USER blockshelf WITH PASSWORD '$DB_PASSWORD';"
sudo -u postgres psql -c "CREATE DATABASE blockshelf OWNER blockshelf;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE blockshelf TO blockshelf;"

echo "→ Creating application directory..."
mkdir -p $APP_DIR
chown $APP_USER:$APP_USER $APP_DIR

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

# Build environment file
cat > $ENV_FILE << ENVEOF
# Django settings
DJANGO_SECRET_KEY=$DJANGO_SECRET
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=$DOMAIN,localhost,127.0.0.1

# Database
DATABASE_URL=postgresql://blockshelf:$DB_PASSWORD@localhost:5432/blockshelf

# Email
EMAIL_BACKEND=$EMAIL_BACKEND
DEFAULT_FROM_EMAIL=$FROM_EMAIL
ENVEOF

# Add email config if configured
if [ "$SETUP_EMAIL" = "yes" ] && [ $INTERACTIVE -eq 1 ]; then
    cat >> $ENV_FILE << ENVEOF
EMAIL_HOST=$SMTP_HOST
EMAIL_PORT=$SMTP_PORT
EMAIL_HOST_USER=$SMTP_USER
EMAIL_HOST_PASSWORD=$SMTP_PASS
EMAIL_USE_TLS=True
ENVEOF
fi

# Add remaining settings
cat >> $ENV_FILE << ENVEOF

# App settings
ALLOW_REGISTRATION=$ALLOW_REGISTRATION
REBRICKABLE_API_KEY=$REBRICKABLE_KEY

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

# Setup automatic backups
if [ "$SETUP_BACKUPS" = "yes" ]; then
    echo "→ Setting up automatic daily backups..."

    # Copy backup service and timer files
    cp $APP_DIR/scripts/blockshelf-backup.service /etc/systemd/system/
    cp $APP_DIR/scripts/blockshelf-backup.timer /etc/systemd/system/

    # Reload systemd
    systemctl daemon-reload

    # Enable and start timer
    systemctl enable blockshelf-backup.timer
    systemctl start blockshelf-backup.timer

    echo "✓ Automatic backups configured (daily at 2 AM)"
fi

echo ""
echo "╔════════════════════════════════════════╗"
echo "║   Installation Complete!               ║"
echo "╚════════════════════════════════════════╝"
echo ""
echo "Configuration saved to: $ENV_FILE"
echo ""
echo "Next steps:"
echo "  1. Create superuser:"
echo "     sudo -u blockshelf bash -c 'source $ENV_FILE && $APP_DIR/.venv/bin/python $APP_DIR/manage.py createsuperuser'"
echo ""
if [ "$DOMAIN" != "localhost" ]; then
    echo "  2. Set up SSL certificate:"
    echo "     certbot --nginx -d $DOMAIN"
    echo ""
fi
if [ "$SETUP_BACKUPS" = "yes" ]; then
    echo "Automatic backups: Daily at 2 AM"
    echo "  Check status: systemctl status blockshelf-backup.timer"
    echo "  View schedule: systemctl list-timers blockshelf-backup.timer"
    echo ""
fi
echo "Service management:"
echo "  Status: sudo systemctl status $SERVICE_NAME"
echo "  Logs:   sudo journalctl -u $SERVICE_NAME -f"
echo "  Restart: sudo systemctl restart $SERVICE_NAME"
echo ""
