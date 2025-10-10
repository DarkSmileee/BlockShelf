#!/bin/bash
# Security vulnerability checking script for BlockShelf
# Runs security audits on Python dependencies

set -e

echo "============================================"
echo "BlockShelf Security Dependency Check"
echo "============================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if pip-audit is installed
if ! command -v pip-audit &> /dev/null; then
    echo -e "${YELLOW}pip-audit not found. Installing...${NC}"
    pip install pip-audit
fi

# Run pip-audit to check for known vulnerabilities
echo "Checking for known security vulnerabilities..."
echo ""

if pip-audit --requirement requirements.txt; then
    echo -e "${GREEN}✓ No known security vulnerabilities found!${NC}"
    exit 0
else
    echo -e "${RED}✗ Security vulnerabilities detected!${NC}"
    echo ""
    echo "Please review the vulnerabilities above and update the affected packages."
    echo "You can update dependencies with: pip install -U <package-name>"
    exit 1
fi
