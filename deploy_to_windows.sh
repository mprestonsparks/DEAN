#!/bin/bash
# Deploy DEAN to Windows deployment PC
# This script should be run after pushing changes to GitHub

echo "=== DEAN Deployment to Windows PC ==="
echo "This script will deploy the latest code from GitHub to the Windows deployment PC"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if we're in the DEAN repository
if [ ! -d ".git" ] || ! git remote -v | grep -q "DEAN"; then
    echo -e "${RED}Error: Not in DEAN repository${NC}"
    exit 1
fi

# Check for uncommitted changes
if [ -n "$(git status --porcelain)" ]; then
    echo -e "${YELLOW}Warning: You have uncommitted changes${NC}"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Push latest changes to GitHub
echo -e "${YELLOW}Pushing latest changes to GitHub...${NC}"
git push origin main

if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to push to GitHub${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Changes pushed to GitHub${NC}"

# Deploy to Windows using SSH
echo -e "${YELLOW}Deploying to Windows deployment PC...${NC}"

# Note: Update this command based on your SSH configuration
# You may need to adjust the SSH key path and command format
ssh deployer@10.7.0.2 "powershell.exe -Command 'cd C:\\dean; powershell -ExecutionPolicy Bypass -File .\\deploy_from_github.ps1 -Environment production'"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Deployment completed successfully${NC}"
else
    echo -e "${RED}✗ Deployment failed${NC}"
    exit 1
fi

# Show deployment status
echo -e "${YELLOW}Checking deployment status...${NC}"
ssh deployer@10.7.0.2 "powershell.exe -Command 'docker ps --filter name=dean --format \"table {{.Names}}\\t{{.Status}}\"'"