# DEAN Secret Management Guide

## Introduction

This guide provides comprehensive instructions for managing secrets in the DEAN system using Infisical. All secrets are centrally managed, encrypted, and distributed through Infisical's secure platform.

## Table of Contents

1. [Secret Organization](#secret-organization)
2. [Accessing Infisical](#accessing-infisical)
3. [Managing Secrets](#managing-secrets)
4. [Service Integration](#service-integration)
5. [Secret Rotation](#secret-rotation)
6. [Troubleshooting](#troubleshooting)
7. [Best Practices](#best-practices)

## Secret Organization

### Secret Paths Structure

```
/dean/
├── common/                 # Shared across all services
│   ├── DEAN_ENV
│   ├── LOG_LEVEL
│   └── DEAN_ORGANIZATION
├── database/              # Database credentials
│   ├── POSTGRES_USER
│   ├── POSTGRES_PASSWORD
│   ├── POSTGRES_DB
│   └── DATABASE_URL
├── redis/                 # Redis configuration
│   ├── REDIS_PASSWORD
│   └── REDIS_URL
├── orchestration/         # DEAN orchestration service
│   ├── DEAN_SERVICE_API_KEY
│   ├── DEAN_JWT_SECRET_KEY
│   └── DEAN_ADMIN_PASSWORD
├── indexagent/           # IndexAgent service
│   ├── INDEXAGENT_API_KEY
│   └── CLAUDE_API_KEY
├── evolution/            # Evolution API service
│   └── EVOLUTION_API_KEY
├── airflow/              # Airflow configuration
│   ├── AIRFLOW_ADMIN_PASSWORD
│   ├── AIRFLOW__CORE__FERNET_KEY
│   └── AIRFLOW__WEBSERVER__SECRET_KEY
├── monitoring/           # Monitoring services
│   ├── prometheus/
│   └── grafana/
├── external/             # External service credentials
│   ├── CLAUDE_API_KEY
│   └── GITHUB_TOKEN
├── service-tokens/       # Service authentication tokens
└── pki/                  # PKI certificates and keys
    ├── ca/
    └── services/
```

### Secret Naming Conventions

- **Environment Variables**: UPPERCASE_WITH_UNDERSCORES
- **API Keys**: SERVICE_API_KEY format
- **URLs**: SERVICE_URL format
- **Passwords**: SERVICE_PASSWORD format
- **Tokens**: SERVICE_TOKEN format

## Accessing Infisical

### Web Interface

1. Navigate to http://10.7.0.2:8090
2. Login with admin credentials:
   - Email: admin@dean-system.local
   - Password: [From initial setup]

### CLI Access

```bash
# Install Infisical CLI
curl -1sLf 'https://dl.cloudsmith.io/public/infisical/infisical-cli/setup.alpine.sh' | sudo -E bash
sudo apk add infisical

# Login
infisical login --domain http://10.7.0.2:8090

# Set default project
infisical init
```

### API Access

```python
import requests

# Get access token
response = requests.post(
    "http://10.7.0.2:8090/api/v1/auth/login",
    json={
        "email": "admin@dean-system.local",
        "password": "your_password"
    }
)
access_token = response.json()["accessToken"]

# Use token for API calls
headers = {"Authorization": f"Bearer {access_token}"}
```

## Managing Secrets

### Creating Secrets

#### Via Web UI

1. Navigate to your project
2. Select environment (production)
3. Click "Add Secret"
4. Enter:
   - Path: /dean/service_name
   - Key: SECRET_NAME
   - Value: secret_value
   - Comment: Description
5. Click "Create"

#### Via CLI

```bash
# Create a single secret
infisical secrets set DATABASE_PASSWORD="new_password" \
  --env=production \
  --path=/dean/database

# Create multiple secrets
infisical secrets set \
  API_KEY="key123" \
  API_SECRET="secret456" \
  --env=production \
  --path=/dean/myservice
```

#### Via API

```python
# Create secret
response = requests.post(
    "http://10.7.0.2:8090/api/v3/secrets",
    headers=headers,
    json={
        "workspaceId": workspace_id,
        "environment": "production",
        "secretPath": "/dean/database",
        "secretKey": "DATABASE_PASSWORD",
        "secretValue": "secure_password",
        "secretComment": "Updated via API"
    }
)
```

### Reading Secrets

#### Via CLI

```bash
# Get single secret
infisical secrets get DATABASE_PASSWORD \
  --env=production \
  --path=/dean/database

# Get all secrets in path
infisical secrets \
  --env=production \
  --path=/dean/database

# Export as environment variables
infisical run --env=production --path=/dean/database -- env
```

#### In Application Code

```python
# Using Infisical SDK
from infisical import InfisicalClient

client = InfisicalClient(
    token="your_service_token",
    site_url="http://10.7.0.2:8090"
)

# Get secret
secret = client.get_secret(
    secret_name="DATABASE_PASSWORD",
    environment="production",
    path="/dean/database"
)

database_password = secret.secret_value
```

### Updating Secrets

#### Via Web UI

1. Navigate to the secret
2. Click "Edit"
3. Update the value
4. Add version comment
5. Save changes

#### Via CLI

```bash
# Update existing secret
infisical secrets set DATABASE_PASSWORD="updated_password" \
  --env=production \
  --path=/dean/database \
  --override
```

### Deleting Secrets

#### Via CLI

```bash
# Delete a secret
infisical secrets delete DATABASE_PASSWORD \
  --env=production \
  --path=/dean/database
```

**Warning**: Deleting secrets may break running services. Always verify dependencies first.

## Service Integration

### Docker Integration

Services use Infisical CLI to inject secrets at runtime:

```dockerfile
# In Dockerfile
RUN curl -1sLf 'https://dl.cloudsmith.io/public/infisical/infisical-cli/setup.alpine.sh' | sh
RUN apk add infisical

# In docker-compose.yml
command: >
  sh -c "
  infisical run --env=production --path=/dean/myservice -- 
  python main.py
  "
```

### Environment Variable Injection

```yaml
# docker-compose.yml with Infisical agent
services:
  myservice:
    image: myservice:latest
    environment:
      INFISICAL_TOKEN: ${SERVICE_TOKEN}
    command: >
      infisical run --env=production --path=/dean/myservice -- 
      python main.py
```

### File-Based Secrets

```bash
# Export secrets to file
infisical secrets export \
  --env=production \
  --path=/dean/myservice \
  --format=dotenv > /run/secrets/myservice.env

# Use in application
source /run/secrets/myservice.env
```

## Secret Rotation

### Automated Rotation

Configure automatic rotation in Infisical:

1. Navigate to secret
2. Click "Configure Rotation"
3. Set rotation period:
   - Passwords: 90 days
   - API Keys: 180 days
   - Tokens: 365 days
4. Enable notifications

### Manual Rotation Process

#### Step 1: Generate New Secret

```bash
# Generate secure password
openssl rand -base64 32

# Or use Python
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

#### Step 2: Update in Infisical

```bash
# Update secret with rotation flag
infisical secrets set DATABASE_PASSWORD="new_secure_password" \
  --env=production \
  --path=/dean/database \
  --override \
  --comment="Rotation: $(date)"
```

#### Step 3: Deploy Services

```bash
# Restart services to pick up new secrets
docker-compose restart dean-orchestration indexagent
```

#### Step 4: Verify

```bash
# Check service health
curl http://localhost:8082/health
curl http://localhost:8081/health
```

#### Step 5: Clean Up

Mark old secret version as deprecated in Infisical UI.

### Emergency Rotation

For compromised credentials:

```bash
# 1. Generate new credentials immediately
NEW_PASSWORD=$(openssl rand -base64 32)

# 2. Update in Infisical
infisical secrets set DATABASE_PASSWORD="$NEW_PASSWORD" \
  --env=production \
  --path=/dean/database \
  --override \
  --comment="EMERGENCY ROTATION - Compromised credential"

# 3. Force restart all services
docker-compose down
docker-compose up -d

# 4. Verify no unauthorized access
# Check audit logs in Infisical UI
```

## Troubleshooting

### Common Issues

#### Service Cannot Access Secrets

**Symptoms**: Service fails to start with "secret not found" errors

**Solutions**:
1. Verify service token is valid:
   ```bash
   infisical service-token test --token=$SERVICE_TOKEN
   ```

2. Check secret path exists:
   ```bash
   infisical secrets --env=production --path=/dean/myservice
   ```

3. Verify network connectivity:
   ```bash
   docker exec myservice curl http://infisical:8090/api/status
   ```

#### Secret Access Denied

**Symptoms**: 403 Forbidden when accessing secrets

**Solutions**:
1. Check service token permissions in Infisical UI
2. Verify environment and path match exactly
3. Ensure service token hasn't expired

#### Stale Secrets

**Symptoms**: Service using old secret values

**Solutions**:
1. Clear Infisical agent cache:
   ```bash
   docker exec infisical-agent rm -rf /app/cache/*
   ```

2. Force service restart:
   ```bash
   docker-compose restart myservice
   ```

3. Verify secret version in Infisical UI

### Debug Commands

```bash
# Test Infisical connectivity
curl http://10.7.0.2:8090/api/status

# Check service token
infisical service-tokens test --token=$TOKEN

# List available secrets
infisical secrets --env=production --path=/dean

# Debug secret injection
infisical run --env=production --path=/dean/myservice -- env | grep MY_SECRET

# Check Infisical agent logs
docker logs infisical-agent

# Verify secret in container
docker exec myservice printenv | grep SECRET_NAME
```

## Best Practices

### Security Best Practices

1. **Never hardcode secrets** in code or configuration files
2. **Use service tokens** instead of user credentials for automation
3. **Rotate secrets regularly** according to policy
4. **Limit secret access** to only required services
5. **Enable audit logging** for all secret access
6. **Use strong passwords**: Minimum 32 characters for critical secrets
7. **Implement secret scanning** in CI/CD pipelines

### Operational Best Practices

1. **Version secrets** with meaningful comments
2. **Test secret rotation** in staging first
3. **Monitor secret expiration** dates
4. **Document secret dependencies** between services
5. **Backup Infisical** regularly
6. **Use separate environments** (dev, staging, prod)
7. **Implement break-glass procedures** for emergencies

### Development Best Practices

1. **Use Infisical CLI** for local development:
   ```bash
   infisical run --env=development -- npm start
   ```

2. **Never commit .env files** with real secrets

3. **Use secret references** in configuration:
   ```yaml
   database:
     url: ${DATABASE_URL}  # Injected by Infisical
   ```

4. **Implement fallback** for missing secrets:
   ```python
   api_key = os.getenv('API_KEY')
   if not api_key:
       logger.error("API_KEY not found")
       sys.exit(1)
   ```

### Naming Conventions

1. **Be descriptive**: `POSTGRES_PASSWORD` not `DB_PASS`
2. **Include service name**: `INDEXAGENT_API_KEY` not just `API_KEY`
3. **Use consistent format**: Always UPPERCASE_WITH_UNDERSCORES
4. **Group related secrets**: Use paths like `/dean/database/*`

### Access Control

1. **Principle of least privilege**: Only grant necessary access
2. **Use service tokens**: One per service/environment
3. **Regular access reviews**: Audit who has access quarterly
4. **Immediate revocation**: Remove access when no longer needed

## Quick Reference

### Essential Commands

```bash
# Login
infisical login --domain http://10.7.0.2:8090

# List secrets
infisical secrets --env=production --path=/dean

# Get secret
infisical secrets get SECRET_NAME --env=production --path=/dean/service

# Set secret
infisical secrets set SECRET_NAME="value" --env=production --path=/dean/service

# Delete secret
infisical secrets delete SECRET_NAME --env=production --path=/dean/service

# Run with secrets
infisical run --env=production --path=/dean/service -- command

# Export secrets
infisical export --env=production --path=/dean/service --format=dotenv
```

### Service Token Management

```bash
# Create service token (via API or UI)
# Test service token
infisical service-tokens test --token=st.xxx

# Use in Docker
docker run -e INFISICAL_TOKEN=st.xxx myimage
```

### Emergency Contacts

- **Infisical Admin**: admin@dean-system.local
- **Security Team**: security@dean-system.local
- **On-Call**: +1-XXX-XXX-XXXX

## Appendix

### A. Secret Types Reference

| Type | Example | Rotation Period | Storage Path |
|------|---------|----------------|--------------|
| Database Password | 32+ chars | 90 days | /dean/database |
| API Key | UUID format | 180 days | /dean/service |
| JWT Secret | 64+ chars | 365 days | /dean/auth |
| Service Token | st.xxx format | 365 days | /dean/service-tokens |
| TLS Certificate | PEM format | 365 days | /dean/pki/services |

### B. Compliance Requirements

- **Audit**: All secret access logged for 90 days
- **Encryption**: AES-256-GCM at rest, TLS 1.3 in transit
- **Access Control**: RBAC with principle of least privilege
- **Rotation**: Mandatory rotation periods enforced
- **Backup**: Daily encrypted backups with 30-day retention