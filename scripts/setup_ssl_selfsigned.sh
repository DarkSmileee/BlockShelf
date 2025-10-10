#!/bin/bash
# Setup self-signed SSL certificates for development/testing
# NOT recommended for production - use Let's Encrypt instead

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "============================================"
echo "BlockShelf SSL Setup (Self-Signed)"
echo "============================================"
echo ""
echo -e "${YELLOW}WARNING: Self-signed certificates are for development only!${NC}"
echo -e "${YELLOW}For production, use setup_ssl_letsencrypt.sh instead${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Error: This script must be run as root${NC}"
    exit 1
fi

# Prompt for domain/hostname
read -p "Enter hostname/domain (e.g., localhost or blockshelf.local): " DOMAIN
if [ -z "$DOMAIN" ]; then
    DOMAIN="localhost"
fi

echo ""
echo "Domain: $DOMAIN"
read -p "Continue? (y/n): " CONFIRM
if [ "$CONFIRM" != "y" ]; then
    echo "Aborted."
    exit 0
fi

# Create SSL directory
SSL_DIR="/etc/nginx/ssl"
mkdir -p "$SSL_DIR"

# Generate self-signed certificate
echo -e "${YELLOW}Generating self-signed certificate...${NC}"

openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout "$SSL_DIR/key.pem" \
    -out "$SSL_DIR/cert.pem" \
    -subj "/C=US/ST=State/L=City/O=Organization/CN=$DOMAIN"

# Set proper permissions
chmod 600 "$SSL_DIR/key.pem"
chmod 644 "$SSL_DIR/cert.pem"

echo -e "${GREEN}✓ Self-signed certificate generated${NC}"

# Update nginx configuration
NGINX_CONF="/etc/nginx/sites-available/blockshelf.conf"

if [ -f "$NGINX_CONF" ]; then
    echo -e "${YELLOW}Updating nginx configuration...${NC}"

    # Comment out Let's Encrypt paths
    sed -i 's|ssl_certificate /etc/letsencrypt|#ssl_certificate /etc/letsencrypt|g' "$NGINX_CONF"
    sed -i 's|ssl_certificate_key /etc/letsencrypt|#ssl_certificate_key /etc/letsencrypt|g' "$NGINX_CONF"
    sed -i 's|ssl_trusted_certificate /etc/letsencrypt|#ssl_trusted_certificate /etc/letsencrypt|g' "$NGINX_CONF"

    # Uncomment self-signed paths
    sed -i 's|# ssl_certificate /etc/nginx/ssl/cert.pem|ssl_certificate /etc/nginx/ssl/cert.pem|g' "$NGINX_CONF"
    sed -i 's|# ssl_certificate_key /etc/nginx/ssl/key.pem|ssl_certificate_key /etc/nginx/ssl/key.pem|g' "$NGINX_CONF"

    # Comment out OCSP stapling (not supported with self-signed)
    sed -i 's|ssl_stapling on|#ssl_stapling on|g' "$NGINX_CONF"
    sed -i 's|ssl_stapling_verify on|#ssl_stapling_verify on|g' "$NGINX_CONF"

    # Update server_name if needed
    if [ "$DOMAIN" != "localhost" ]; then
        sed -i "s/server_name _;/server_name $DOMAIN;/g" "$NGINX_CONF"
    fi

    # Test nginx configuration
    nginx -t

    # Reload nginx
    systemctl reload nginx

    echo -e "${GREEN}✓ Nginx configuration updated${NC}"
fi

echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}Self-Signed SSL Setup Complete!${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo -e "${YELLOW}IMPORTANT: Your browser will show a security warning${NC}"
echo -e "${YELLOW}This is expected for self-signed certificates${NC}"
echo ""
echo "Certificate location: $SSL_DIR/cert.pem"
echo "Private key location: $SSL_DIR/key.pem"
echo ""
echo "To access your site:"
echo "1. Visit https://$DOMAIN"
echo "2. Accept the browser security warning"
echo "3. Proceed to the site"
echo ""
echo -e "${YELLOW}For production use, run setup_ssl_letsencrypt.sh instead${NC}"
echo ""
