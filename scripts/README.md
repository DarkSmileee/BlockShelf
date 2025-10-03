# BlockShelf Deployment Scripts

This directory contains scripts for deploying and managing BlockShelf.

## Scripts

### Fresh Installation

Use this for a brand new installation:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/DarkSmileee/BlockShelf/main/scripts/install.sh)
```

**What it does:**
- Detects existing BlockShelf installations and prompts for confirmation
- If confirmed, completely removes old installation (database, files, service)
- Installs system dependencies (Python, PostgreSQL, Nginx, etc.)
- Creates BlockShelf user and database
- Generates secure random passwords and Django secret key
- Clones repository and sets up Python virtual environment
- Runs migrations and collects static files
- Creates and starts systemd service

**WARNING:** This will destroy all existing BlockShelf data if you confirm the cleanup!

### Update Existing Installation

Use this to update an existing BlockShelf installation:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/DarkSmileee/BlockShelf/main/scripts/update.sh)
```

**What it does:**
- Checks for existing installation
- Creates backup of current installation (excludes venv and caches)
- Pulls latest code from GitHub (hard reset to origin/main)
- Cleans Python bytecode cache
- Updates Python dependencies
- Runs database migrations
- Collects static files
- Restarts service

**Safe:** This preserves your database and configuration files.

## Requirements

Both scripts require:
- Ubuntu/Debian-based system
- Root access (run with sudo)
- Internet connection

## After Installation

1. Update allowed hosts:
   ```bash
   sudo nano /etc/blockshelf/.env
   # Update DJANGO_ALLOWED_HOSTS with your domain
   ```

2. Create superuser:
   ```bash
   sudo -u blockshelf bash -c 'source /etc/blockshelf/.env && /opt/blockshelf/.venv/bin/python /opt/blockshelf/manage.py createsuperuser'
   ```

3. Configure Nginx and SSL (see main documentation)

## Troubleshooting

Check service status:
```bash
sudo systemctl status blockshelf
```

View logs:
```bash
sudo journalctl -u blockshelf -n 50
```

Restart service:
```bash
sudo systemctl restart blockshelf
```
