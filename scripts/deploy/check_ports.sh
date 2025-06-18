#!/bin/bash
# Check if required ports are available

# Default ports (can be overridden by environment variables)
PORTS=(
    "${NGINX_HTTP_PORT:-80}"
    "${NGINX_HTTPS_PORT:-443}"
    "${ORCHESTRATOR_PORT:-8082}"
    "${AIRFLOW_PORT:-8080}"
    "${INDEXAGENT_PORT:-8081}"
    "${POSTGRES_PORT:-5432}"
    "${REDIS_PORT:-6379}"
    "${PROMETHEUS_PORT:-9090}"
    "${GRAFANA_PORT:-3000}"
)

check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 1
    else
        return 0
    fi
}

check_all_ports() {
    echo "Checking port availability..."
    
    local conflicts=()
    
    for port in "${PORTS[@]}"; do
        if ! check_port "$port"; then
            local process=$(lsof -Pi :$port -sTCP:LISTEN | tail -1)
            conflicts+=("Port $port is in use by: $process")
        else
            echo "✓ Port $port is available"
        fi
    done
    
    if [ ${#conflicts[@]} -ne 0 ]; then
        echo "ERROR: Port conflicts detected:"
        printf '%s\n' "${conflicts[@]}"
        echo ""
        echo "Resolution options:"
        echo "1. Stop the conflicting services"
        echo "2. Change DEAN service ports in .env file"
        echo "3. Use the no-nginx configuration if port 80/443 are blocked"
        return 1
    fi
    
    echo "✓ All required ports are available"
    return 0
}

# Run port check
check_all_ports