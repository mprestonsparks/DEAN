#!/bin/bash
# Verify database configuration in Docker environment

echo "=== Docker Database Configuration Verification ==="
echo

# Check if postgres container is running
if docker ps | grep -q "dean-postgres"; then
    echo "PostgreSQL container is running"
    
    # List databases
    echo
    echo "Databases in PostgreSQL:"
    docker exec dean-postgres psql -U dean_prod -c "\l" 2>&1 | grep -E "(dean_|List of databases)"
    
    # Check if dean_production exists
    echo
    echo "Checking for dean_production database..."
    if docker exec dean-postgres psql -U dean_prod -lqt | cut -d \| -f 1 | grep -qw "dean_production"; then
        echo "✓ dean_production database exists"
    else
        echo "✗ dean_production database NOT FOUND"
        echo
        echo "To create the database, run:"
        echo "  docker exec dean-postgres psql -U postgres -c 'CREATE DATABASE dean_production;'"
        echo "  docker exec dean-postgres psql -U postgres -c 'GRANT ALL PRIVILEGES ON DATABASE dean_production TO dean_prod;'"
    fi
else
    echo "PostgreSQL container is not running"
fi

# Check orchestrator environment
echo
echo "Orchestrator environment variables:"
if docker ps | grep -q "dean-orchestrator"; then
    docker exec dean-orchestrator printenv | grep -E "(POSTGRES|DATABASE)" | sort
else
    echo "Orchestrator container is not running"
fi