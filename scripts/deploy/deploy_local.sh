#!/bin/bash
# Deploy DEAN orchestration locally using Docker

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

echo -e "${GREEN}DEAN Local Deployment Script${NC}"
echo "================================"

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check port availability
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${RED}Port $port is already in use${NC}"
        return 1
    fi
    return 0
}

# Check prerequisites
echo "Checking prerequisites..."

if ! command_exists docker; then
    echo -e "${RED}Docker is not installed. Please install Docker first.${NC}"
    exit 1
fi

if ! command_exists docker-compose; then
    echo -e "${RED}Docker Compose is not installed. Please install Docker Compose first.${NC}"
    exit 1
fi

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo -e "${RED}Docker daemon is not running. Please start Docker.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Prerequisites satisfied${NC}"

# Check required ports
echo "Checking port availability..."
REQUIRED_PORTS=(8080 8081 8082 8083 5432 6379 8200 6070 9090)
PORTS_AVAILABLE=true

for port in "${REQUIRED_PORTS[@]}"; do
    if ! check_port $port; then
        PORTS_AVAILABLE=false
    fi
done

if [ "$PORTS_AVAILABLE" = false ]; then
    echo -e "${RED}Some required ports are in use. Please free them or adjust configuration.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ All required ports are available${NC}"

# Create necessary directories
echo "Creating directories..."
mkdir -p "$PROJECT_ROOT/data/postgres"
mkdir -p "$PROJECT_ROOT/data/redis"
mkdir -p "$PROJECT_ROOT/logs"
mkdir -p "$PROJECT_ROOT/vault/data"

# Copy environment file if it doesn't exist
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    echo "Creating .env file from example..."
    cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
    echo -e "${YELLOW}Please edit .env file with your configuration${NC}"
fi

# Build DEAN orchestration image
echo "Building DEAN orchestration Docker image..."
cd "$PROJECT_ROOT"

cat > Dockerfile <<EOF
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements/base.txt requirements/base.txt
RUN pip install --no-cache-dir -r requirements/base.txt

# Copy source code
COPY src/ src/
COPY pyproject.toml .
COPY configs/ configs/

# Install the package
RUN pip install -e .

# Expose port
EXPOSE 8082

# Run the server
CMD ["dean-server"]
EOF

docker build -t dean-orchestration:latest .

echo -e "${GREEN}✓ Docker image built successfully${NC}"

# Create docker-compose.yml for local deployment
echo "Creating docker-compose configuration..."

cat > docker-compose.local.yml <<EOF
version: '3.8'

services:
  # DEAN Orchestration Server
  dean-server:
    image: dean-orchestration:latest
    container_name: dean-server
    ports:
      - "8082:8082"
    environment:
      - DEAN_SERVER_HOST=0.0.0.0
      - DEAN_SERVER_PORT=8082
      - INDEXAGENT_API_URL=http://indexagent:8081
      - AIRFLOW_API_URL=http://airflow:8080
      - EVOLUTION_API_URL=http://evolution-api:8083
      - POSTGRES_HOST=postgres
      - REDIS_HOST=redis
      - VAULT_URL=http://vault:8200
    depends_on:
      - postgres
      - redis
    volumes:
      - ./logs:/app/logs
      - ./configs:/app/configs:ro
    networks:
      - dean-network
    restart: unless-stopped

  # PostgreSQL Database
  postgres:
    image: postgres:15-alpine
    container_name: dean-postgres
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_DB=postgres
    ports:
      - "5432:5432"
    volumes:
      - ./data/postgres:/var/lib/postgresql/data
    networks:
      - dean-network
    restart: unless-stopped

  # Redis Cache
  redis:
    image: redis:7-alpine
    container_name: dean-redis
    ports:
      - "6379:6379"
    volumes:
      - ./data/redis:/data
    networks:
      - dean-network
    restart: unless-stopped

  # HashiCorp Vault (for secrets)
  vault:
    image: vault:latest
    container_name: dean-vault
    ports:
      - "8200:8200"
    environment:
      - VAULT_DEV_ROOT_TOKEN_ID=dean-dev-token
      - VAULT_DEV_LISTEN_ADDRESS=0.0.0.0:8200
    cap_add:
      - IPC_LOCK
    volumes:
      - ./vault/data:/vault/data
    networks:
      - dean-network
    restart: unless-stopped

networks:
  dean-network:
    driver: bridge
    name: dean-network

volumes:
  postgres-data:
  redis-data:
  vault-data:
EOF

# Start services
echo "Starting DEAN services..."
docker-compose -f docker-compose.local.yml up -d

# Wait for services to be ready
echo "Waiting for services to start..."
sleep 10

# Check service health
echo "Checking service health..."

# Function to check if service is healthy
check_service() {
    local service=$1
    local url=$2
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s -f "$url" >/dev/null 2>&1; then
            echo -e "${GREEN}✓ $service is healthy${NC}"
            return 0
        fi
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    echo -e "${RED}✗ $service failed to start${NC}"
    return 1
}

# Check each service
check_service "PostgreSQL" "http://localhost:5432" || true
check_service "Redis" "http://localhost:6379" || true
check_service "Vault" "http://localhost:8200/v1/sys/health"
check_service "DEAN Server" "http://localhost:8082/health"

echo ""
echo -e "${GREEN}DEAN Orchestration System Deployed Successfully!${NC}"
echo ""
echo "Access the dashboard at: http://localhost:8082"
echo "API documentation at: http://localhost:8082/docs"
echo ""
echo "To view logs:"
echo "  docker-compose -f docker-compose.local.yml logs -f"
echo ""
echo "To stop services:"
echo "  docker-compose -f docker-compose.local.yml down"
echo ""

# Note about missing services
echo -e "${YELLOW}Note: This deployment includes only the DEAN orchestration server.${NC}"
echo -e "${YELLOW}To deploy the full system, you need to also run:${NC}"
echo -e "${YELLOW}  - IndexAgent (port 8081)${NC}"
echo -e "${YELLOW}  - Airflow (port 8080)${NC}"
echo -e "${YELLOW}  - Evolution API (port 8083)${NC}"