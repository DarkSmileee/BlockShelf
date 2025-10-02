#!/bin/bash
# Check what migrations Django thinks are needed

APP_DIR="/opt/blockshelf"
ENV_FILE="/etc/blockshelf/.env"
APP_USER="blockshelf"

echo "→ Checking for needed migrations..."
sudo -u $APP_USER bash -c "set -a; source $ENV_FILE; set +a; cd $APP_DIR && $APP_DIR/.venv/bin/python manage.py makemigrations --dry-run --verbosity 2"

echo ""
echo "→ Creating any needed migrations..."
sudo -u $APP_USER bash -c "set -a; source $ENV_FILE; set +a; cd $APP_DIR && $APP_DIR/.venv/bin/python manage.py makemigrations"
