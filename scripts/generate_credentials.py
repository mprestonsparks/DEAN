#!/usr/bin/env python3
"""Generate secure credentials for DEAN deployment."""

import secrets
import string
import json
from datetime import datetime
import base64

def generate_password(length=24):
    """Generate a secure password."""
    alphabet = string.ascii_letters + string.digits + string.punctuation
    # Remove problematic characters for shell/config files
    alphabet = alphabet.replace('"', '').replace("'", '').replace('\\', '').replace('`', '')
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def generate_api_key(prefix="dean", length=32):
    """Generate a secure API key."""
    key = secrets.token_urlsafe(length)
    return f"{prefix}_{key}"

def generate_jwt_secret():
    """Generate a secure JWT secret."""
    return secrets.token_urlsafe(64)

def generate_all_credentials():
    """Generate all required credentials for DEAN deployment."""
    credentials = {
        "generated_at": datetime.utcnow().isoformat(),
        "database": {
            "postgres_password": generate_password(32),
            "postgres_user": "dean_admin",
            "database_name": "agent_evolution"
        },
        "redis": {
            "password": generate_password(24)
        },
        "dean": {
            "service_api_key": generate_api_key("dean_service", 48),
            "jwt_secret_key": generate_jwt_secret(),
            "admin_password": generate_password(24)
        },
        "airflow": {
            "admin_password": generate_password(24),
            "fernet_key": base64.b64encode(secrets.token_bytes(32)).decode('utf-8'),
            "secret_key": generate_jwt_secret()
        },
        "services": {
            "indexagent_api_key": generate_api_key("indexagent", 32),
            "evolution_api_key": generate_api_key("evolution", 32),
            "monitoring_api_key": generate_api_key("monitoring", 32)
        },
        "external": {
            "claude_api_key": "PLACEHOLDER_MUST_BE_PROVIDED",
            "github_token": "PLACEHOLDER_MUST_BE_PROVIDED"
        }
    }
    
    return credentials

def generate_env_file(credentials):
    """Generate .env file content from credentials."""
    env_content = f"""# DEAN Production Environment Configuration
# Generated: {credentials['generated_at']}
# WARNING: This file contains sensitive credentials. Protect it carefully!

# Database Configuration
POSTGRES_USER={credentials['database']['postgres_user']}
POSTGRES_PASSWORD={credentials['database']['postgres_password']}
POSTGRES_DB={credentials['database']['database_name']}
DATABASE_URL=postgresql://{credentials['database']['postgres_user']}:{credentials['database']['postgres_password']}@postgres:5432/{credentials['database']['database_name']}
DEAN_DATABASE_URL=postgresql://{credentials['database']['postgres_user']}:{credentials['database']['postgres_password']}@postgres:5432/{credentials['database']['database_name']}
AGENT_EVOLUTION_DATABASE_URL=postgresql://{credentials['database']['postgres_user']}:{credentials['database']['postgres_password']}@postgres:5432/{credentials['database']['database_name']}

# Redis Configuration
REDIS_PASSWORD={credentials['redis']['password']}
REDIS_URL=redis://:{credentials['redis']['password']}@redis:6379/0

# DEAN Service Configuration
DEAN_SERVICE_API_KEY={credentials['dean']['service_api_key']}
DEAN_JWT_SECRET_KEY={credentials['dean']['jwt_secret_key']}
DEAN_ADMIN_PASSWORD={credentials['dean']['admin_password']}
DEAN_ENV=production

# Airflow Configuration
AIRFLOW_ADMIN_PASSWORD={credentials['airflow']['admin_password']}
AIRFLOW__CORE__FERNET_KEY={credentials['airflow']['fernet_key']}
AIRFLOW__WEBSERVER__SECRET_KEY={credentials['airflow']['secret_key']}

# Service API Keys
INDEXAGENT_API_KEY={credentials['services']['indexagent_api_key']}
EVOLUTION_API_KEY={credentials['services']['evolution_api_key']}
MONITORING_API_KEY={credentials['services']['monitoring_api_key']}

# External Services (MUST BE PROVIDED)
CLAUDE_API_KEY={credentials['external']['claude_api_key']}
GITHUB_TOKEN={credentials['external']['github_token']}

# Service URLs (internal Docker network)
DEAN_SERVER_HOST=dean-orchestration
DEAN_SERVER_PORT=8082
DEAN_WEB_PORT=8083
INDEXAGENT_URL=http://indexagent:8081
AIRFLOW_URL=http://airflow-webserver:8080
EVOLUTION_API_URL=http://evolution-api:8090
PROMETHEUS_URL=http://prometheus:9090
GRAFANA_URL=http://grafana:3000

# Resource Limits
AGENT_MAX_CONCURRENT=8
AGENT_TOKEN_LIMIT=4096
AGENT_EVOLUTION_MAX_POPULATION=100000
DEAN_MIN_DIVERSITY=0.3
DEAN_MUTATION_RATE=0.1
DEAN_MIN_VALUE_PER_TOKEN=0.001

# Deployment Configuration
DOCKER_DEFAULT_PLATFORM=linux/amd64
COMPOSE_PROJECT_NAME=dean-production
"""
    return env_content

def main():
    """Generate and save credentials."""
    print("Generating secure credentials for DEAN deployment...")
    
    credentials = generate_all_credentials()
    
    # Save credentials as JSON (for reference)
    with open("credentials.json", "w") as f:
        json.dump(credentials, f, indent=2)
    print("✓ Saved credentials to credentials.json")
    
    # Generate .env file
    env_content = generate_env_file(credentials)
    with open(".env.production", "w") as f:
        f.write(env_content)
    print("✓ Generated .env.production file")
    
    # Generate docker-compose override for security
    compose_override = f"""# docker-compose.security.yml
# Security overrides for production deployment
version: '3.8'

services:
  postgres:
    environment:
      POSTGRES_PASSWORD: {credentials['database']['postgres_password']}
      POSTGRES_USER: {credentials['database']['postgres_user']}
      POSTGRES_DB: {credentials['database']['database_name']}
    
  redis:
    command: redis-server --requirepass {credentials['redis']['password']}
    
  dean-orchestration:
    environment:
      DEAN_ENV: production
      DEAN_SERVICE_API_KEY: {credentials['dean']['service_api_key']}
      DEAN_JWT_SECRET_KEY: {credentials['dean']['jwt_secret_key']}
    
  airflow-webserver:
    environment:
      AIRFLOW__CORE__FERNET_KEY: {credentials['airflow']['fernet_key']}
      AIRFLOW__WEBSERVER__SECRET_KEY: {credentials['airflow']['secret_key']}
      AIRFLOW_ADMIN_PASSWORD: {credentials['airflow']['admin_password']}
"""
    
    with open("docker-compose.security.yml", "w") as f:
        f.write(compose_override)
    print("✓ Generated docker-compose.security.yml")
    
    print("\n⚠️  IMPORTANT SECURITY NOTES:")
    print("1. Replace PLACEHOLDER values in .env.production with actual CLAUDE_API_KEY and GITHUB_TOKEN")
    print("2. Protect these files - they contain sensitive credentials")
    print("3. Never commit these files to version control")
    print("4. Set file permissions to 600 (read/write owner only)")
    print("\nCredentials generated successfully!")

if __name__ == "__main__":
    main()