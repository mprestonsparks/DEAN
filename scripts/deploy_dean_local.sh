#!/bin/bash
# Deploy DEAN System Locally for Integration Testing

set -e

echo "=================================="
echo "DEAN System Local Deployment"
echo "=================================="

# Function to check if service is healthy
check_health() {
    local service_name=$1
    local health_url=$2
    local max_attempts=30
    local attempt=0
    
    echo -n "Checking $service_name health..."
    while [ $attempt -lt $max_attempts ]; do
        if curl -s -f "$health_url" > /dev/null 2>&1; then
            echo " ✓ Healthy"
            return 0
        fi
        echo -n "."
        sleep 2
        ((attempt++))
    done
    echo " ✗ Failed"
    return 1
}

# Navigate to infra directory
cd ../infra

echo "1. Starting infrastructure services..."
docker-compose -f docker-compose.dean.yml up -d postgres redis

# Wait for PostgreSQL to be ready
check_health "PostgreSQL" "http://localhost:5432" || true

# Check if postgres is actually ready with psql
echo "Waiting for PostgreSQL to accept connections..."
until PGPASSWORD=postgres psql -h localhost -U postgres -d agent_evolution -c '\q' 2>/dev/null; do
    echo -n "."
    sleep 2
done
echo " ✓ Ready"

echo "2. Initializing database schema..."
# If schema doesn't exist, apply it
PGPASSWORD=postgres psql -h localhost -U postgres -d agent_evolution -f database/init_agent_evolution.sql || true

echo "3. Starting Token Economy Service..."
cd modules/agent-evolution
docker-compose -f docker-compose.token_economy.yml up -d token-economy
cd ../..

check_health "Token Economy" "http://localhost:8091/health"

echo "4. Starting IndexAgent API..."
cd ../IndexAgent
if [ -f "docker-compose.yml" ]; then
    docker-compose up -d
else
    echo "Building IndexAgent container..."
    docker build -t indexagent:latest .
    docker run -d \
        --name indexagent \
        -p 8081:8081 \
        -e DATABASE_URL=postgresql://postgres:postgres@host.docker.internal:5432/agent_evolution \
        -e REDIS_URL=redis://host.docker.internal:6379 \
        --network infra_dean-network \
        indexagent:latest || true
fi
cd ../infra

check_health "IndexAgent" "http://localhost:8081/health"

echo "5. Starting DEAN Orchestration..."
cd ../DEAN
if [ -f "docker-compose.yml" ]; then
    docker-compose up -d
else
    echo "Building DEAN Orchestration container..."
    docker build -t dean-orchestration:latest .
    docker run -d \
        --name dean-orchestration \
        -p 8082:8082 \
        -e DATABASE_URL=postgresql://postgres:postgres@host.docker.internal:5432/agent_evolution \
        -e REDIS_URL=redis://host.docker.internal:6379 \
        -e INDEXAGENT_URL=http://host.docker.internal:8081 \
        -e TOKEN_ECONOMY_URL=http://host.docker.internal:8091 \
        --network infra_dean-network \
        dean-orchestration:latest || true
fi
cd ../infra

check_health "DEAN Orchestration" "http://localhost:8082/health"

echo ""
echo "=================================="
echo "Deployment Status:"
echo "=================================="
echo "PostgreSQL:        http://localhost:5432"
echo "Redis:             http://localhost:6379"
echo "Token Economy:     http://localhost:8091/health"
echo "IndexAgent:        http://localhost:8081/health"
echo "DEAN Orchestration: http://localhost:8082/health"
echo ""

# Show running containers
echo "Running containers:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "To view logs: docker logs <container-name>"
echo "To stop all: docker-compose down && docker stop \$(docker ps -q)"