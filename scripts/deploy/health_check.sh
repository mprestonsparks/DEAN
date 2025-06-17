#!/bin/bash
# Health check script for DEAN orchestration system

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
ORCHESTRATION_URL="${ORCHESTRATION_URL:-http://localhost:8082}"
INDEXAGENT_URL="${INDEXAGENT_URL:-http://localhost:8081}"
AIRFLOW_URL="${AIRFLOW_URL:-http://localhost:8080}"
EVOLUTION_URL="${EVOLUTION_URL:-http://localhost:8083}"
TIMEOUT="${HEALTH_CHECK_TIMEOUT:-5}"

echo "DEAN System Health Check"
echo "========================"
echo ""

# Function to check service health
check_service() {
    local service_name=$1
    local service_url=$2
    local endpoint="${3:-/health}"
    
    echo -n "Checking $service_name... "
    
    if curl -s -f -m "$TIMEOUT" "$service_url$endpoint" >/dev/null 2>&1; then
        echo -e "${GREEN}✓ Healthy${NC}"
        return 0
    else
        echo -e "${RED}✗ Unhealthy${NC}"
        return 1
    fi
}

# Function to check database connectivity
check_database() {
    echo -n "Checking PostgreSQL... "
    
    if PGPASSWORD="${POSTGRES_PASSWORD:-postgres}" psql \
        -h "${POSTGRES_HOST:-localhost}" \
        -p "${POSTGRES_PORT:-5432}" \
        -U "${POSTGRES_USER:-postgres}" \
        -d postgres \
        -c "SELECT 1" >/dev/null 2>&1; then
        echo -e "${GREEN}✓ Connected${NC}"
        return 0
    else
        echo -e "${RED}✗ Connection failed${NC}"
        return 1
    fi
}

# Function to check Redis connectivity
check_redis() {
    echo -n "Checking Redis... "
    
    if redis-cli -h "${REDIS_HOST:-localhost}" -p "${REDIS_PORT:-6379}" ping >/dev/null 2>&1; then
        echo -e "${GREEN}✓ Connected${NC}"
        return 0
    else
        echo -e "${RED}✗ Connection failed${NC}"
        return 1
    fi
}

# Overall health status
OVERALL_HEALTH=true

# Check core services
echo "Core Services:"
echo "--------------"

check_service "Orchestration Server" "$ORCHESTRATION_URL" || OVERALL_HEALTH=false
check_service "IndexAgent API" "$INDEXAGENT_URL" || OVERALL_HEALTH=false
check_service "Airflow API" "$AIRFLOW_URL" || OVERALL_HEALTH=false
check_service "Evolution API" "$EVOLUTION_URL" || OVERALL_HEALTH=false

echo ""
echo "Infrastructure:"
echo "---------------"

# Check infrastructure services if tools are available
if command -v psql >/dev/null 2>&1; then
    check_database || OVERALL_HEALTH=false
else
    echo -e "${YELLOW}⚠ PostgreSQL check skipped (psql not installed)${NC}"
fi

if command -v redis-cli >/dev/null 2>&1; then
    check_redis || OVERALL_HEALTH=false
else
    echo -e "${YELLOW}⚠ Redis check skipped (redis-cli not installed)${NC}"
fi

# Detailed orchestration health check
echo ""
echo "Detailed Orchestration Status:"
echo "------------------------------"

if curl -s -f -m "$TIMEOUT" "$ORCHESTRATION_URL/api/system/status" > /tmp/dean_status.json 2>/dev/null; then
    if command -v jq >/dev/null 2>&1; then
        # Parse with jq if available
        status=$(jq -r '.status' /tmp/dean_status.json)
        active_agents=$(jq -r '.metrics.active_agents' /tmp/dean_status.json)
        recent_trials=$(jq -r '.metrics.recent_trials' /tmp/dean_status.json)
        
        echo "System Status: $status"
        echo "Active Agents: $active_agents"
        echo "Recent Trials: $recent_trials"
        
        echo ""
        echo "Service Details:"
        jq -r '.services | to_entries[] | "  \(.key): \(.value.status)"' /tmp/dean_status.json
    else
        echo -e "${YELLOW}⚠ Install jq for detailed status${NC}"
        cat /tmp/dean_status.json
    fi
else
    echo -e "${RED}Failed to fetch detailed status${NC}"
    OVERALL_HEALTH=false
fi

# Performance metrics
echo ""
echo "Performance Metrics:"
echo "--------------------"

# Check response times
for service in "Orchestration:$ORCHESTRATION_URL" "IndexAgent:$INDEXAGENT_URL"; do
    IFS=':' read -r name url <<< "$service"
    echo -n "  $name response time: "
    
    if response_time=$(curl -o /dev/null -s -w '%{time_total}' "$url/health" 2>/dev/null); then
        # Convert to milliseconds
        response_ms=$(echo "$response_time * 1000" | bc 2>/dev/null || echo "N/A")
        if [ "$response_ms" != "N/A" ]; then
            echo "${response_ms}ms"
        else
            echo "$response_time seconds"
        fi
    else
        echo "N/A"
    fi
done

# Memory usage check (if in Docker)
if [ -f /.dockerenv ]; then
    echo ""
    echo "Container Resource Usage:"
    echo "-------------------------"
    
    if [ -f /proc/meminfo ]; then
        total_mem=$(grep MemTotal /proc/meminfo | awk '{print $2}')
        free_mem=$(grep MemFree /proc/meminfo | awk '{print $2}')
        used_mem=$((total_mem - free_mem))
        used_percent=$((used_mem * 100 / total_mem))
        
        echo "  Memory: ${used_percent}% used"
    fi
    
    if [ -f /proc/loadavg ]; then
        load=$(cat /proc/loadavg | cut -d' ' -f1-3)
        echo "  Load Average: $load"
    fi
fi

# Summary
echo ""
echo "================================"
if [ "$OVERALL_HEALTH" = true ]; then
    echo -e "${GREEN}Overall System Health: HEALTHY${NC}"
    exit 0
else
    echo -e "${RED}Overall System Health: UNHEALTHY${NC}"
    echo ""
    echo "Troubleshooting steps:"
    echo "1. Check service logs: docker-compose logs [service-name]"
    echo "2. Verify network connectivity between services"
    echo "3. Check resource availability (CPU, memory, disk)"
    echo "4. Ensure all required environment variables are set"
    echo "5. Verify database migrations have been run"
    exit 1
fi