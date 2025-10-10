#!/bin/bash
# Clear all rate limiting and account lockout timers
# Usage: sudo ./scripts/clear_rate_limits.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "Clearing rate limits and lockouts..."

# Check if running in production
if [ -d "/opt/blockshelf" ]; then
    # Production path
    sudo -u blockshelf bash -c "set -a; source /etc/blockshelf/.env; set +a; /opt/blockshelf/.venv/bin/python /opt/blockshelf/manage.py clear_rate_limits --verbose"
else
    # Development path
    cd "$PROJECT_DIR"
    python manage.py clear_rate_limits --verbose
fi

echo "✓ Rate limits cleared successfully"
