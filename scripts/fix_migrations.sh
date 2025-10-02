#!/usr/bin/env bash
# Fix any pending migrations by creating and applying them

set -euo pipefail

APP_DIR="/opt/blockshelf"
ENV_FILE="/etc/blockshelf/.env"

echo "╔════════════════════════════════════════╗"
echo "║     Fix Migrations Script              ║"
echo "╚════════════════════════════════════════╝"
echo

cd "$APP_DIR"

echo "→ Checking for unapplied model changes..."
sudo -u blockshelf bash -c "set -a; source $ENV_FILE; set +a; cd $APP_DIR && .venv/bin/python manage.py makemigrations --dry-run --verbosity 2"

echo
echo "→ Creating migrations for any changes..."
sudo -u blockshelf bash -c "set -a; source $ENV_FILE; set +a; cd $APP_DIR && .venv/bin/python manage.py makemigrations"

echo
echo "→ Applying migrations..."
sudo -u blockshelf bash -c "set -a; source $ENV_FILE; set +a; cd $APP_DIR && .venv/bin/python manage.py migrate --noinput"

echo
echo "→ Checking migration status..."
sudo -u blockshelf bash -c "set -a; source $ENV_FILE; set +a; cd $APP_DIR && .venv/bin/python manage.py showmigrations inventory"

echo
echo "✓ Migrations fixed!"
echo
echo "Now restart the service:"
echo "  sudo systemctl restart blockshelf"
