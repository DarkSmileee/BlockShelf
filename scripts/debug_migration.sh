#!/bin/bash
# Debug why migration isn't being detected

echo "=== Debugging Migration Issue ==="
echo ""

echo "1. Check migration files:"
ls -la /opt/blockshelf/inventory/migrations/
echo ""

echo "2. Check if 0002 migration is valid Python:"
sudo -u blockshelf python3 -m py_compile /opt/blockshelf/inventory/migrations/0002_security_features.py
echo "✓ Migration file is valid Python"
echo ""

echo "3. Check migration dependencies in 0002:"
grep -A 3 "dependencies = \[" /opt/blockshelf/inventory/migrations/0002_security_features.py
echo ""

echo "4. Check what Django thinks the migration state is:"
sudo -u blockshelf bash -lc 'set -a; source /etc/blockshelf/.env; set +a; cd /opt/blockshelf && ./.venv/bin/python manage.py showmigrations inventory'
echo ""

echo "5. Try to see what makemigrations detects:"
sudo -u blockshelf bash -lc 'set -a; source /etc/blockshelf/.env; set +a; cd /opt/blockshelf && ./.venv/bin/python manage.py makemigrations --dry-run inventory'
