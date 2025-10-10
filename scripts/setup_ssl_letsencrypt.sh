#!/bin/bash
# Setup SSL certificates using Let's Encrypt
# This script helps configure HTTPS for BlockShelf in production

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "============================================"
echo "BlockShelf SSL Setup (Let's Encrypt)"
echo "============================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Error: This script must be run as root${NC}"
    exit 1
fi

# Prompt for domain name
read -p "Enter your domain name (e.g., blockshelf.example.com): " DOMAIN
if [ -z "$DOMAIN" ]; then
    echo -e "${RED}Error: Domain name is required${NC}"
    exit 1
fi

# Prompt for email
read -p "Enter your email address for Let's Encrypt notifications: " EMAIL
if [ -z "$EMAIL" ]; then
    echo -e "${RED}Error: Email address is required${NC}"
    exit 1
fi

echo ""
echo "Domain: $DOMAIN"
echo "Email: $EMAIL"
echo ""
read -p "Continue? (y/n): " CONFIRM
if [ "$CONFIRM" != "y" ]; then
    echo "Aborted."
    exit 0
fi

# Install certbot if not already installed
if ! command -v certbot &> /dev/null; then
    echo -e "${YELLOW}Installing certbot...${NC}"
    apt-get update
    apt-get install -y certbot python3-certbot-nginx
fi

# Create webroot directory for ACME challenges
mkdir -p /var/www/certbot
chown -R www-data:www-data /var/www/certbot

# Update nginx configuration with domain name
echo -e "${YELLOW}Updating nginx configuration...${NC}"
NGINX_CONF="/etc/nginx/sites-available/blockshelf.conf"

# Replace placeholder domain with actual domain
sed -i "s/yourdomain.com/$DOMAIN/g" "$NGINX_CONF"
sed -i "s/server_name _;/server_name $DOMAIN;/g" "$NGINX_CONF"

# Test nginx configuration
nginx -t

# Reload nginx
systemctl reload nginx

# Obtain SSL certificate
echo -e "${YELLOW}Obtaining SSL certificate from Let's Encrypt...${NC}"
certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email "$EMAIL" \
    --agree-tos \
    --no-eff-email \
    -d "$DOMAIN"

# Verify certificate was obtained
if [ ! -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ]; then
    echo -e "${RED}Error: Failed to obtain SSL certificate${NC}"
    exit 1
fi

echo -e "${GREEN}✓ SSL certificate obtained successfully!${NC}"

# Test nginx configuration again
nginx -t

# Reload nginx to use new certificates
systemctl reload nginx

# Set up automatic renewal
echo -e "${YELLOW}Setting up automatic certificate renewal...${NC}"

# Create renewal hook
cat > /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh <<'HOOK'
#!/bin/bash
systemctl reload nginx
HOOK

chmod +x /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh

# Test automatic renewal
certbot renew --dry-run

echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}SSL Setup Complete!${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo "Your BlockShelf installation is now secured with HTTPS"
echo "Certificate will auto-renew every 60 days"
echo ""
echo "Next steps:"
echo "1. Visit https://$DOMAIN to verify HTTPS is working"
echo "2. Update ALLOWED_HOSTS and CSRF_TRUSTED_ORIGINS in .env"
echo "3. Set DEBUG=False in production"
echo ""
echo "Certificate location: /etc/letsencrypt/live/$DOMAIN/"
echo "Auto-renewal: Managed by certbot systemd timer"
echo ""
