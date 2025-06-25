#!/bin/bash
# Infisical initialization script for air-gapped deployment

set -e

echo "🔐 Initializing Infisical Security Platform"
echo "========================================="

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL..."
until pg_isready -h postgres-infisical -p 5432 -U infisical_user; do
  echo "PostgreSQL is not ready yet. Retrying in 5 seconds..."
  sleep 5
done
echo "✅ PostgreSQL is ready"

# Wait for Redis to be ready
echo "Waiting for Redis..."
until redis-cli -h redis-infisical -a "${REDIS_PASSWORD}" ping > /dev/null 2>&1; do
  echo "Redis is not ready yet. Retrying in 5 seconds..."
  sleep 5
done
echo "✅ Redis is ready"

# Initialize database if needed
echo "Initializing database schema..."
if [ "${INFISICAL_DB_MIGRATE}" = "true" ]; then
  echo "Running database migrations..."
  # Infisical will handle migrations automatically on startup
fi

# Create default directories
mkdir -p /app/data/{logs,backups,temp}

# Log startup configuration (without sensitive data)
echo "Starting Infisical with configuration:"
echo "  - Public URL: ${INFISICAL_PUBLIC_URL}"
echo "  - Port: ${INFISICAL_PORT}"
echo "  - Air-gapped mode: ${INFISICAL_AIR_GAPPED}"
echo "  - Audit retention: ${INFISICAL_AUDIT_LOG_RETENTION_DAYS} days"
echo "  - Telemetry: ${INFISICAL_TELEMETRY_ENABLED}"

# Start Infisical server
echo "🚀 Starting Infisical server..."
exec node /app/dist/main.js