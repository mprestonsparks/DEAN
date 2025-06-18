#!/bin/bash
# scripts/deploy/deploy_dean_system.sh

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Load environment
if [[ -f "$PROJECT_ROOT/.env" ]]; then
    export $(grep -v '^#' "$PROJECT_ROOT/.env" | xargs)
fi

# Deployment stages
stage_banner() {
    echo -e "${BLUE}===================================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}===================================================${NC}"
}

# 1. Pre-deployment validation
stage_banner "Stage 1: Pre-deployment Validation"

# Check Docker
if ! docker info &>/dev/null; then
    echo -e "${RED}ERROR: Docker is not running${NC}"
    exit 1
fi

# Validate environment
source "$SCRIPT_DIR/validate_environment.sh"
if ! validate_environment; then
    echo -e "${RED}Environment validation failed${NC}"
    exit 1
fi

# Check ports
source "$SCRIPT_DIR/check_ports.sh"
if ! check_all_ports; then
    echo -e "${RED}Port conflicts detected${NC}"
    exit 1
fi

# 2. SSL Certificate Setup
stage_banner "Stage 2: SSL Certificate Setup"
source "$SCRIPT_DIR/setup_ssl_certificates.sh"
if ! setup_ssl_certificates; then
    echo -e "${RED}SSL certificate setup failed${NC}"
    exit 1
fi

# 3. Build Docker Images
stage_banner "Stage 3: Building Docker Images"
cd "$PROJECT_ROOT"
DOCKER_BUILDKIT=1 docker-compose -f docker-compose.prod.yml build --parallel

# 4. Start Infrastructure Services
stage_banner "Stage 4: Starting Infrastructure Services"
docker-compose -f docker-compose.prod.yml up -d postgres-prod redis-prod

# Wait for database
echo "Waiting for PostgreSQL to be ready..."
until docker-compose -f docker-compose.prod.yml exec -T postgres-prod pg_isready -U ${POSTGRES_USER}; do
    sleep 2
done

# 5. Initialize Database
stage_banner "Stage 5: Initializing Database"
docker-compose -f docker-compose.prod.yml exec -T postgres-prod psql -U ${POSTGRES_USER} <<EOF
CREATE DATABASE IF NOT EXISTS ${POSTGRES_DB};
CREATE DATABASE IF NOT EXISTS indexagent;
CREATE DATABASE IF NOT EXISTS airflow;
CREATE DATABASE IF NOT EXISTS agent_evolution;
EOF

# 6. Start Application Services
stage_banner "Stage 6: Starting Application Services"
docker-compose -f docker-compose.prod.yml up -d orchestrator

# Wait for orchestrator
echo "Waiting for orchestrator to be ready..."
until curl -f http://localhost:8082/health &>/dev/null; do
    sleep 2
done

# 7. Start Nginx
stage_banner "Stage 7: Starting Nginx Proxy"
docker-compose -f docker-compose.prod.yml up -d nginx

# 8. Verify Deployment
stage_banner "Stage 8: Deployment Verification"
sleep 5

# Check all services
services=("postgres-prod" "redis-prod" "orchestrator" "nginx")
failed=()

for service in "${services[@]}"; do
    if docker-compose -f docker-compose.prod.yml ps | grep "$service" | grep -q "Up"; then
        echo -e "${GREEN}✓ $service is running${NC}"
    else
        failed+=("$service")
        echo -e "${RED}✗ $service is not running${NC}"
    fi
done

if [ ${#failed[@]} -eq 0 ]; then
    echo -e "${GREEN}"
    echo "===================================================="
    echo "  DEAN System Deployed Successfully!"
    echo "===================================================="
    echo -e "${NC}"
    echo "Access URLs:"
    echo "  - Web Dashboard: https://localhost/"
    echo "  - API Endpoint: https://localhost/api/v1/"
    echo "  - Health Check: https://localhost/health"
    echo ""
    echo "Next steps:"
    echo "  1. Change default passwords"
    echo "  2. Configure production domain"
    echo "  3. Set up monitoring alerts"
    echo "  4. Schedule backups"
else
    echo -e "${RED}"
    echo "===================================================="
    echo "  Deployment Failed!"
    echo "===================================================="
    echo -e "${NC}"
    echo "Failed services: ${failed[*]}"
    echo "Check logs with: docker-compose -f docker-compose.prod.yml logs [service-name]"
    exit 1
fi