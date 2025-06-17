# DEAN Comprehensive Deployment Guide

This guide provides detailed instructions for deploying the DEAN system in production environments.

## Table of Contents
1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Environment Preparation](#environment-preparation)
3. [SSL Certificate Setup](#ssl-certificate-setup)
4. [Database Configuration](#database-configuration)
5. [Step-by-Step Deployment](#step-by-step-deployment)
6. [Post-Deployment Verification](#post-deployment-verification)
7. [Troubleshooting Guide](#troubleshooting-guide)
8. [Maintenance Procedures](#maintenance-procedures)

## Pre-Deployment Checklist

Before beginning deployment, ensure all requirements are met:

### System Requirements
- [ ] Docker 20.10+ installed
- [ ] Docker Compose 1.29+ installed
- [ ] Python 3.8+ installed
- [ ] At least 10GB free disk space
- [ ] Required ports available: 80, 443, 8082, 5432, 6379

### Configuration Files
- [ ] `.env` file created from `.env.production.template`
- [ ] All placeholder values replaced with actual values
- [ ] No BOM characters in configuration files
- [ ] SSL certificates generated or obtained

### Validation
Run the pre-deployment validation script:
```bash
python scripts/pre_deployment_check.py
```

All errors must be resolved before proceeding.

## Environment Preparation

### 1. Clone Repository
```bash
git clone https://github.com/your-org/DEAN.git
cd DEAN
```

### 2. Create Environment File
```bash
cp .env.production.template .env
```

### 3. Configure Environment Variables

Edit `.env` and set all required values:

#### Critical Variables (MUST be changed)
```bash
# Security
JWT_SECRET_KEY=<generate-with: openssl rand -hex 32>
DEAN_API_KEY=<generate-with: openssl rand -hex 32>

# Database
POSTGRES_PASSWORD=<strong-password>
POSTGRES_DB=dean_production  # MUST be dean_production

# Redis
REDIS_PASSWORD=<strong-password>
```

#### Service Configuration
```bash
# Environment
ENV=production
LOG_LEVEL=INFO
DEBUG=false

# Database URL (constructed from components)
DATABASE_URL=postgresql://dean_prod:${POSTGRES_PASSWORD}@dean-postgres:5432/dean_production
```

See [ENVIRONMENT_VARIABLES.md](../ENVIRONMENT_VARIABLES.md) for complete reference.

### 4. Validate Environment
```bash
python scripts/validate_environment.py --mode production
```

## SSL Certificate Setup

### Option 1: Self-Signed (Development/Testing)
```bash
python scripts/manage_ssl_certificates.py --generate-dev
```

### Option 2: Let's Encrypt (Recommended for Production)
```bash
# Install certbot
sudo apt-get install certbot

# Generate certificates
sudo certbot certonly --standalone -d your-domain.com

# Copy to DEAN
python scripts/manage_ssl_certificates.py --setup-production \
    --cert /etc/letsencrypt/live/your-domain.com/fullchain.pem \
    --key /etc/letsencrypt/live/your-domain.com/privkey.pem
```

### Option 3: Commercial Certificate
```bash
python scripts/manage_ssl_certificates.py --setup-production \
    --cert /path/to/your-certificate.crt \
    --key /path/to/your-private.key
```

### Verify Certificate Setup
```bash
python scripts/manage_ssl_certificates.py --status
```

## Database Configuration

### Important Notes
- Database name MUST be `dean_production`
- Database user is `dean_prod`
- Never use `dean_prod` as the database name

### Initialization
The database is automatically initialized on first run using scripts in `postgres/`:
- `00-create-schema.sql` - Creates schema and permissions
- `01-init-database.sql` - Creates tables and indexes
- `02-init-extensions.sql` - Enables required PostgreSQL extensions

## Step-by-Step Deployment

### 1. Final Pre-Deployment Check
```bash
# Run comprehensive validation
python scripts/pre_deployment_check.py --export pre_deployment_report.txt

# Check for BOM characters
python scripts/check_bom.py

# Validate database configuration
python scripts/verify_database_fix.py
```

### 2. Build Images
```bash
# Build all services
docker-compose -f docker-compose.prod.yml build
```

### 3. Start Database Services First
```bash
# Start PostgreSQL and Redis
docker-compose -f docker-compose.prod.yml up -d postgres-prod redis-prod

# Wait for services to be ready
sleep 30

# Verify database is accessible
docker exec dean-postgres psql -U dean_prod -d dean_production -c "SELECT 1;"
```

### 4. Start Application Services
```bash
# Start remaining services
docker-compose -f docker-compose.prod.yml up -d

# Monitor startup logs
docker-compose -f docker-compose.prod.yml logs -f
```

### 5. Verify Deployment
```bash
# Check all containers are running
docker-compose -f docker-compose.prod.yml ps

# Test health endpoints
curl http://localhost:8082/health
curl https://localhost/health
```

## Post-Deployment Verification

### 1. Service Health Checks
```bash
# Orchestrator
curl -f http://localhost:8082/health || echo "Orchestrator health check failed"

# Database connectivity
docker exec dean-orchestrator python scripts/test_db_connection.py

# Redis connectivity
docker exec dean-redis redis-cli ping
```

### 2. SSL Certificate Verification
```bash
# Check HTTPS
curl -k https://localhost/ || echo "HTTPS not working"

# Verify certificate
openssl s_client -connect localhost:443 -servername localhost < /dev/null
```

### 3. Log Analysis
```bash
# Check for errors
docker-compose -f docker-compose.prod.yml logs | grep -i error

# Monitor real-time logs
docker-compose -f docker-compose.prod.yml logs -f --tail=100
```

### 4. API Testing
```bash
# Test authentication
curl -X POST http://localhost:8082/auth/token \
    -H "Content-Type: application/json" \
    -d '{"api_key": "'$DEAN_API_KEY'"}'

# Test authenticated endpoint
TOKEN=$(curl -s -X POST http://localhost:8082/auth/token \
    -H "Content-Type: application/json" \
    -d '{"api_key": "'$DEAN_API_KEY'"}' | jq -r .access_token)

curl -H "Authorization: Bearer $TOKEN" http://localhost:8082/agents
```

## Troubleshooting Guide

### Common Issues and Solutions

#### 1. Database Connection Errors
**Error**: `database "dean_prod" does not exist`

**Solution**:
```bash
# Check environment variables
docker exec dean-orchestrator printenv | grep POSTGRES

# Verify database name
echo $POSTGRES_DB  # Should be "dean_production"

# Fix if needed
export POSTGRES_DB=dean_production
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d
```

#### 2. SSL Certificate Errors
**Error**: `nginx: [emerg] cannot load certificate`

**Solution**:
```bash
# Check certificate files exist
ls -la certs/

# Generate certificates if missing
python scripts/manage_ssl_certificates.py --generate-dev

# Restart nginx
docker-compose -f docker-compose.prod.yml restart nginx
```

#### 3. Port Conflicts
**Error**: `bind: address already in use`

**Solution**:
```bash
# Find process using port
sudo lsof -i :80
sudo lsof -i :443

# Stop conflicting service or change DEAN ports in docker-compose.prod.yml
```

#### 4. Memory Issues
**Error**: Container killed due to memory limits

**Solution**:
```bash
# Increase Docker memory allocation
# Edit docker-compose.prod.yml and add memory limits:
services:
  orchestrator:
    mem_limit: 2g
    memswap_limit: 2g
```

#### 5. BOM Character Issues
**Error**: YAML parsing errors

**Solution**:
```bash
# Check for BOM
python scripts/check_bom.py

# Remove BOM if found
python scripts/check_bom.py --fix
```

### Debug Commands

```bash
# Container logs
docker logs dean-orchestrator
docker logs dean-postgres
docker logs dean-nginx

# Shell access
docker exec -it dean-orchestrator /bin/bash
docker exec -it dean-postgres psql -U dean_prod -d dean_production

# Network debugging
docker network ls
docker network inspect dean_network

# Resource usage
docker stats

# Clean restart
docker-compose -f docker-compose.prod.yml down -v
docker-compose -f docker-compose.prod.yml up -d
```

## Maintenance Procedures

### Daily Tasks
1. Check service health endpoints
2. Review error logs
3. Monitor disk space
4. Verify backup completion

### Weekly Tasks
1. Review performance metrics
2. Check for security updates
3. Rotate logs
4. Test disaster recovery

### Monthly Tasks
1. Update SSL certificates (if needed)
2. Review and update dependencies
3. Performance optimization
4. Security audit

### Backup Procedures
```bash
# Database backup
docker exec dean-postgres pg_dump -U dean_prod dean_production > backup_$(date +%Y%m%d).sql

# Full system backup
tar -czf dean_backup_$(date +%Y%m%d).tar.gz \
    --exclude='logs' \
    --exclude='__pycache__' \
    .env postgres/data redis/data certs/
```

### Update Procedures
```bash
# Pull latest changes
git pull origin main

# Rebuild images
docker-compose -f docker-compose.prod.yml build

# Rolling update
docker-compose -f docker-compose.prod.yml up -d --no-deps orchestrator
```

### Monitoring Setup
```bash
# Prometheus metrics
curl http://localhost:9090/metrics

# Health check automation
*/5 * * * * /path/to/dean/scripts/health_check.sh
```

## Security Considerations

1. **Always use strong passwords** - No defaults in production
2. **Enable SSL/TLS** - Never run HTTP-only in production
3. **Restrict network access** - Use firewalls
4. **Regular updates** - Keep dependencies current
5. **Monitor logs** - Set up alerting for suspicious activity
6. **Backup encryption** - Encrypt all backups
7. **Access control** - Limit who can access production

## Support and Resources

- **Documentation**: `/docs` directory
- **Environment Variables**: [ENVIRONMENT_VARIABLES.md](../ENVIRONMENT_VARIABLES.md)
- **API Reference**: [API.md](../api/API.md)
- **Issue Tracker**: GitHub Issues
- **Logs Location**: `./logs` directory

## Quick Reference Card

```bash
# Start system
docker-compose -f docker-compose.prod.yml up -d

# Stop system
docker-compose -f docker-compose.prod.yml down

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Restart service
docker-compose -f docker-compose.prod.yml restart orchestrator

# Check status
docker-compose -f docker-compose.prod.yml ps

# Run validation
python scripts/pre_deployment_check.py

# Test database
docker exec dean-orchestrator python scripts/test_db_connection.py
```

Remember: Always validate before deploying, always backup before updating, and always monitor after deployment.