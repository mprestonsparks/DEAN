#!/bin/bash

# DEAN Development Environment Shutdown Script
# Stops all services started by dev_environment.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DEAN_ROOT="$PROJECT_ROOT/DEAN"
STUBS_DIR="$DEAN_ROOT/service_stubs"
LOGS_DIR="$DEAN_ROOT/logs/dev"

echo -e "${BLUE}=== Stopping DEAN Development Environment ===${NC}"
echo ""

# Step 1: Stop orchestration server
echo -e "${YELLOW}Stopping orchestration server...${NC}"

if [ -f "$LOGS_DIR/orchestration.pid" ]; then
    PID=$(cat "$LOGS_DIR/orchestration.pid")
    if kill -0 $PID 2>/dev/null; then
        echo "Stopping orchestration server (PID: $PID)..."
        kill $PID
        sleep 2
        
        # Force kill if still running
        if kill -0 $PID 2>/dev/null; then
            echo "Force stopping orchestration server..."
            kill -9 $PID
        fi
        
        echo -e "${GREEN}✓ Orchestration server stopped${NC}"
    else
        echo "Orchestration server not running"
    fi
    rm -f "$LOGS_DIR/orchestration.pid"
else
    echo "No PID file found for orchestration server"
fi

echo ""

# Step 2: Stop Docker services
echo -e "${YELLOW}Stopping Docker services...${NC}"

cd "$STUBS_DIR"

# Stop all services
docker-compose -f docker-compose.stubs.yml down

echo -e "${GREEN}✓ All Docker services stopped${NC}"
echo ""

# Step 3: Clean up
echo -e "${YELLOW}Cleaning up...${NC}"

# Optional: Remove volumes (uncomment if you want to clear data)
# docker-compose -f docker-compose.stubs.yml down -v

# Optional: Clean up logs (uncomment if desired)
# rm -rf "$LOGS_DIR"/*

echo -e "${GREEN}✓ Cleanup complete${NC}"
echo ""

echo -e "${GREEN}=== Development environment stopped ===${NC}"