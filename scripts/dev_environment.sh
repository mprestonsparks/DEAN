#!/bin/bash

# DEAN Development Environment Startup Script
# Starts all stub services and the orchestration layer for development

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

# Create logs directory
mkdir -p "$LOGS_DIR"

echo -e "${BLUE}=== DEAN Development Environment ===${NC}"
echo "Starting all services for local development..."
echo ""

# Function to check if port is available
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${RED}✗ Port $port is already in use${NC}"
        return 1
    else
        echo -e "${GREEN}✓ Port $port is available${NC}"
        return 0
    fi
}

# Function to wait for service health
wait_for_health() {
    local url=$1
    local service=$2
    local max_attempts=30
    local attempt=0
    
    echo -n "Waiting for $service to be healthy..."
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -f -s "$url" > /dev/null 2>&1; then
            echo -e " ${GREEN}✓${NC}"
            return 0
        fi
        echo -n "."
        sleep 1
        ((attempt++))
    done
    
    echo -e " ${RED}✗ Failed${NC}"
    return 1
}

# Step 1: Check port availability
echo -e "${YELLOW}Checking port availability...${NC}"
PORTS=(5432 6379 8080 8081 8082 8083)
PORT_NAMES=("PostgreSQL" "Redis" "Airflow" "IndexAgent" "Orchestration" "Evolution")
all_ports_available=true

for i in "${!PORTS[@]}"; do
    if ! check_port "${PORTS[$i]}"; then
        echo "  Service: ${PORT_NAMES[$i]}"
        all_ports_available=false
    fi
done

if [ "$all_ports_available" = false ]; then
    echo -e "\n${RED}Error: Some required ports are in use.${NC}"
    echo "Please stop conflicting services or change port configuration."
    exit 1
fi

echo ""

# Step 2: Start infrastructure services
echo -e "${YELLOW}Starting infrastructure services...${NC}"

cd "$STUBS_DIR"

# Start PostgreSQL and Redis
echo "Starting PostgreSQL and Redis..."
docker-compose -f docker-compose.stubs.yml up -d postgres-dev redis-dev

# Wait for infrastructure
wait_for_health "localhost:5432" "PostgreSQL" || exit 1
wait_for_health "localhost:6379" "Redis" || exit 1

echo ""

# Step 3: Start stub services
echo -e "${YELLOW}Starting stub services...${NC}"

# Build and start all stub services
echo "Building stub services..."
docker-compose -f docker-compose.stubs.yml build

echo "Starting stub services..."
docker-compose -f docker-compose.stubs.yml up -d indexagent-stub airflow-stub evolution-stub

# Wait for stub services
wait_for_health "http://localhost:8081/health" "IndexAgent" || exit 1
wait_for_health "http://localhost:8080/health" "Airflow" || exit 1
wait_for_health "http://localhost:8083/health" "Evolution API" || exit 1

echo ""

# Step 4: Run database migrations
echo -e "${YELLOW}Running database migrations...${NC}"

cd "$DEAN_ROOT"

# Create databases if they don't exist
docker exec postgres-dev psql -U dean -d dean_dev -c "CREATE DATABASE IF NOT EXISTS orchestration;" 2>/dev/null || true
docker exec postgres-dev psql -U dean -d dean_dev -c "CREATE DATABASE IF NOT EXISTS indexagent;" 2>/dev/null || true
docker exec postgres-dev psql -U dean -d dean_dev -c "CREATE DATABASE IF NOT EXISTS airflow;" 2>/dev/null || true

# Run migrations
if [ -f "scripts/utilities/db_migrate.py" ]; then
    echo "Running migrations..."
    python scripts/utilities/db_migrate.py up
else
    echo "Migration script not found, skipping..."
fi

echo ""

# Step 5: Start DEAN orchestration server
echo -e "${YELLOW}Starting DEAN orchestration server...${NC}"

cd "$DEAN_ROOT"

# Set environment variables
export DEAN_ENV=development
export DEAN_SERVER_HOST=0.0.0.0
export DEAN_SERVER_PORT=8082
export INDEXAGENT_API_URL=http://localhost:8081
export AIRFLOW_API_URL=http://localhost:8080
export EVOLUTION_API_URL=http://localhost:8083
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_USER=dean
export POSTGRES_PASSWORD=dean123
export POSTGRES_DB=orchestration
export REDIS_HOST=localhost
export REDIS_PORT=6379
export LOG_LEVEL=INFO

# Authentication configuration
export JWT_SECRET_KEY="dev-secret-key-change-in-production"
export JWT_ALGORITHM="HS256"
export ACCESS_TOKEN_EXPIRE_MINUTES=30
export REFRESH_TOKEN_EXPIRE_DAYS=7
export AIRFLOW_USERNAME=airflow
export AIRFLOW_PASSWORD=airflow

# Security settings for development
export ENFORCE_HTTPS=false
export ALLOWED_ORIGINS="http://localhost:3000,http://localhost:8082"
export DEV_MODE=true

# Start the orchestration server in background
echo "Starting orchestration server..."
nohup python -m uvicorn src.interfaces.web.app:app \
    --host $DEAN_SERVER_HOST \
    --port $DEAN_SERVER_PORT \
    --reload \
    > "$LOGS_DIR/orchestration.log" 2>&1 &

ORCH_PID=$!
echo "Orchestration server PID: $ORCH_PID"

# Save PID for shutdown
echo $ORCH_PID > "$LOGS_DIR/orchestration.pid"

# Wait for orchestration server
wait_for_health "http://localhost:8082/api/health" "Orchestration" || exit 1

echo ""

# Step 6: Initialize authentication
echo -e "${YELLOW}Initializing authentication...${NC}"

# Create development SSL certificates if they don't exist
if [ ! -f "$DEAN_ROOT/certs/dev-cert.pem" ]; then
    echo "Creating self-signed certificates for development..."
    mkdir -p "$DEAN_ROOT/certs"
    openssl req -x509 -newkey rsa:4096 -nodes -days 365 \
        -keyout "$DEAN_ROOT/certs/dev-key.pem" \
        -out "$DEAN_ROOT/certs/dev-cert.pem" \
        -subj "/C=US/ST=State/L=City/O=DEAN-Dev/CN=localhost" \
        2>/dev/null
    echo -e "${GREEN}✓ Development certificates created${NC}"
fi

echo ""

# Step 7: Display service URLs and authentication info
echo -e "${GREEN}=== All services started successfully! ===${NC}"
echo ""
echo -e "${BLUE}Service URLs:${NC}"
echo "  • Orchestration Dashboard: http://localhost:8082"
echo "  • Orchestration API:      http://localhost:8082/api"
echo "  • API Documentation:      http://localhost:8082/docs"
echo "  • IndexAgent API:         http://localhost:8081"
echo "  • Airflow UI:            http://localhost:8080"
echo "  • Evolution API:          http://localhost:8083"
echo "  • Evolution WebSocket:    ws://localhost:8083/ws"
echo ""
echo -e "${BLUE}Authentication:${NC}"
echo "  • Default Admin:     username: admin, password: admin123"
echo "  • Default User:      username: user, password: user123"
echo "  • Default Viewer:    username: viewer, password: viewer123"
echo "  • Airflow:          username: airflow, password: airflow"
echo ""
echo -e "${YELLOW}⚠️  WARNING: Using default credentials. Change these for production!${NC}"
echo ""
echo -e "${BLUE}Database connections:${NC}"
echo "  • PostgreSQL: postgresql://dean:dean123@localhost:5432/dean_dev"
echo "  • Redis:      redis://localhost:6379"
echo ""
echo -e "${BLUE}Logs:${NC}"
echo "  • Orchestration: $LOGS_DIR/orchestration.log"
echo "  • Docker logs:   docker-compose -f $STUBS_DIR/docker-compose.stubs.yml logs -f"
echo ""
echo -e "${BLUE}Quick Authentication Test:${NC}"
echo "  # Login and get token:"
echo "  curl -X POST http://localhost:8082/auth/login \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"username\": \"admin\", \"password\": \"admin123\"}'"
echo ""
echo -e "${YELLOW}To stop all services, run:${NC}"
echo "  $DEAN_ROOT/scripts/stop_dev_environment.sh"
echo ""

# Step 7: Open dashboard in browser (optional)
if command -v open >/dev/null 2>&1; then
    # macOS
    echo "Opening dashboard in browser..."
    sleep 2
    open "http://localhost:8082"
elif command -v xdg-open >/dev/null 2>&1; then
    # Linux
    echo "Opening dashboard in browser..."
    sleep 2
    xdg-open "http://localhost:8082"
fi

echo -e "\n${GREEN}Development environment is ready!${NC}"
echo -e "${GREEN}Authentication is enabled for all services.${NC}"