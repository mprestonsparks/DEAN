#!/bin/bash
# quick_start.sh

echo "DEAN System Quick Start"
echo "======================"

# Create minimal .env if not exists
if [[ ! -f .env ]]; then
    echo "Creating default .env file..."
    cat > .env <<EOF
# Minimal configuration for local development
JWT_SECRET_KEY=$(openssl rand -hex 32)
POSTGRES_USER=dean_dev
POSTGRES_PASSWORD=dean_dev_password
POSTGRES_DB=dean_development
REDIS_PASSWORD=dean_redis_dev
DEAN_SERVICE_API_KEY=$(openssl rand -hex 16)
USE_SELF_SIGNED=true
ENVIRONMENT=development
EOF
fi

# Generate SSL certificates
./scripts/deploy/setup_ssl_certificates.sh

# Start services
echo "Starting DEAN services..."
docker-compose -f docker-compose.prod.yml up -d

# Wait and show status
sleep 10
docker-compose -f docker-compose.prod.yml ps

echo ""
echo "DEAN System is starting up!"
echo "Access the dashboard at: https://localhost"
echo "Note: You may need to accept the self-signed certificate warning"