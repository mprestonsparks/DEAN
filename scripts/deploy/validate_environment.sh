#!/bin/bash
# scripts/deploy/validate_environment.sh

REQUIRED_VARS=(
    "JWT_SECRET_KEY"
    "POSTGRES_USER"
    "POSTGRES_PASSWORD"
    "POSTGRES_DB"
    "REDIS_PASSWORD"
    "DEAN_SERVICE_API_KEY"
)

OPTIONAL_VARS=(
    "CORS_ALLOWED_ORIGINS"
    "LOG_LEVEL"
    "DEAN_ADMIN_EMAIL"
)

validate_environment() {
    echo "Validating environment variables..."
    
    local missing=()
    local warnings=()
    
    # Check required variables
    for var in "${REQUIRED_VARS[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            missing+=("$var")
        fi
    done
    
    # Check optional variables
    for var in "${OPTIONAL_VARS[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            warnings+=("$var")
        fi
    done
    
    # Validate JWT secret length
    if [[ -n "${JWT_SECRET_KEY:-}" ]] && [[ ${#JWT_SECRET_KEY} -lt 32 ]]; then
        echo "ERROR: JWT_SECRET_KEY must be at least 32 characters long"
        return 1
    fi
    
    # Report results
    if [ ${#missing[@]} -ne 0 ]; then
        echo "ERROR: Missing required environment variables:"
        printf '  - %s\n' "${missing[@]}"
        return 1
    fi
    
    if [ ${#warnings[@]} -ne 0 ]; then
        echo "WARNING: Missing optional environment variables:"
        printf '  - %s\n' "${warnings[@]}"
    fi
    
    echo "✓ Environment validation passed"
    return 0
}

# Create template if it doesn't exist
create_env_template() {
    if [[ ! -f .env.template ]]; then
        cat > .env.template <<'EOF'
# DEAN System Environment Configuration
# Copy this file to .env and update with your values

# === REQUIRED VARIABLES ===

# Security
JWT_SECRET_KEY=CHANGE_ME_TO_64_CHAR_RANDOM_STRING
DEAN_SERVICE_API_KEY=CHANGE_ME_TO_32_CHAR_RANDOM_STRING

# Database
POSTGRES_USER=dean_prod
POSTGRES_PASSWORD=CHANGE_ME_TO_SECURE_PASSWORD
POSTGRES_DB=dean_production

# Redis
REDIS_PASSWORD=CHANGE_ME_TO_SECURE_PASSWORD

# === OPTIONAL VARIABLES ===

# CORS (comma-separated list of allowed origins)
CORS_ALLOWED_ORIGINS=http://localhost,https://localhost

# Logging
LOG_LEVEL=INFO

# Admin
DEAN_ADMIN_EMAIL=admin@example.com

# SSL/TLS
USE_SELF_SIGNED=true
CERT_VALIDITY_DAYS=365

# Resource Limits
ORCHESTRATOR_MEMORY_LIMIT=2g
ORCHESTRATOR_CPU_LIMIT=2.0
EOF
        echo "✓ Created .env.template"
    fi
}

# Run validation
create_env_template
validate_environment