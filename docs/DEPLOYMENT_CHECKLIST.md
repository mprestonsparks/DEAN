# DEAN System Deployment Checklist

This comprehensive checklist ensures smooth deployment of the DEAN system by addressing all known configuration issues and providing clear verification steps.

## Pre-Deployment Checklist

### 1. Environment Preparation

- [ ] **Docker Environment**
  ```powershell
  # Verify Docker is running
  docker version
  docker compose version
  ```
  
- [ ] **Run Environment Setup**
  ```powershell
  # Automated setup with secure defaults
  ./scripts/setup_environment.ps1 -Environment production -GenerateSecrets
  ```

- [ ] **Validate Environment**
  ```powershell
  # Run comprehensive validation
  ./scripts/validate_deployment.ps1 -Verbose
  
  # Auto-fix detected issues
  ./scripts/validate_deployment.ps1 -AutoFix
  ```

### 2. Configuration Verification

- [ ] **Check for BOM Characters**
  - Script automatically checks: `nginx/*.conf`, `docker-compose*.yml`, `.env`
  - Auto-fix available with validation script

- [ ] **Environment Variables**
  - [ ] JWT_SECRET_KEY (min 32 chars)
  - [ ] POSTGRES_PASSWORD (secure)
  - [ ] POSTGRES_DB = "dean_production"
  - [ ] REDIS_PASSWORD (secure)
  - [ ] DEAN_SERVICE_API_KEY (min 16 chars)

- [ ] **Database Naming Consistency**
  - Ensure all references use "dean_production"
  - Check: `.env`, `docker-compose.yml`, `postgres/init.sql`

### 3. SSL/TLS Setup

- [ ] **Development Environment**
  ```powershell
  # Generate self-signed certificates
  ./scripts/setup_ssl.ps1 -Environment development
  ```

- [ ] **Production Environment**
  ```powershell
  # Validate existing certificates
  ./scripts/setup_ssl.ps1 -Validate
  
  # Show production setup instructions
  ./scripts/setup_ssl.ps1 -ShowInstructions
  ```

- [ ] **Certificate Files Required**
  - `nginx/certs/server.crt`
  - `nginx/certs/server.key`
  - Alternative names created automatically

### 4. Port Availability

- [ ] **Check Required Ports**
  - Port 80 (HTTP/nginx)
  - Port 443 (HTTPS/nginx)
  - Port 8082 (Orchestrator API)
  - Port 5432 (PostgreSQL)
  - Port 6379 (Redis)

### 5. Directory Structure

- [ ] **Required Directories** (created by setup script)
  ```
  nginx/certs/
  postgres/
  logs/
  data/
  backups/
  monitoring/
  ```

## Deployment Steps

### 1. Initial Deployment

```powershell
# 1. Clone repository and enter directory
git clone <repository-url>
cd DEAN

# 2. Run environment setup
./scripts/setup_environment.ps1 -Environment production -GenerateSecrets

# 3. Review and update .env file
notepad .env

# 4. Validate configuration
./scripts/validate_deployment.ps1

# 5. Deploy the system
./deploy_windows.ps1
```

### 2. Service Startup Order

The deployment script ensures correct startup order:
1. PostgreSQL (with health check)
2. Redis (with health check)
3. Orchestrator (after dependencies)
4. Nginx (after orchestrator)

### 3. Health Verification

```powershell
# Check all services are running
docker ps

# Test HTTP endpoint
curl http://localhost/health

# Test HTTPS endpoint (use browser for self-signed certs)
Start-Process "https://localhost/health"

# Check API documentation
Start-Process "http://localhost:8082/docs"
```

## Post-Deployment Verification

### 1. Service Health Checks

- [ ] **PostgreSQL Connection**
  ```powershell
  docker exec dean-postgres pg_isready
  ```

- [ ] **Redis Connection**
  ```powershell
  docker exec dean-redis redis-cli ping
  ```

- [ ] **Orchestrator API**
  ```powershell
  curl http://localhost:8082/health
  ```

- [ ] **Nginx Proxy**
  ```powershell
  curl http://localhost/health
  ```

### 2. Log Verification

```powershell
# Check for errors in logs
docker logs dean-orchestrator --tail 50
docker logs dean-nginx --tail 50
docker logs dean-postgres --tail 50
```

### 3. Database Verification

```powershell
# Verify database creation
docker exec dean-postgres psql -U dean_prod -d dean_production -c "\dt"
```

## Troubleshooting Guide

### Common Issues and Solutions

#### 1. BOM Character in Configuration Files
**Symptom**: Nginx fails to start with syntax errors
**Solution**: 
```powershell
./scripts/validate_deployment.ps1 -AutoFix
```

#### 2. Database Connection Failed
**Symptom**: "database dean_prod does not exist"
**Solution**: Ensure POSTGRES_DB="dean_production" in .env

#### 3. SSL Certificate Missing
**Symptom**: Nginx fails with "cannot load certificate"
**Solution**: 
```powershell
./scripts/setup_ssl.ps1 -Environment development
```

#### 4. Port Already in Use
**Symptom**: "bind: address already in use"
**Solution**: 
- Stop conflicting services
- Or update port mappings in docker-compose.yml

#### 5. PowerShell HTTPS Issues
**Symptom**: SSL/TLS errors with self-signed certificates
**Solution**: Use web browser for HTTPS testing with self-signed certs

### Quick Diagnostics

```powershell
# Run comprehensive troubleshooting
./scripts/troubleshoot.sh

# Check specific service
docker logs <service-name> --tail 100

# Interactive debugging
docker exec -it <service-name> /bin/bash
```

## Production Deployment Considerations

### Security Hardening

1. **Replace Self-Signed Certificates**
   - Use Let's Encrypt or commercial CA
   - Update certificate paths in .env

2. **Update Default Passwords**
   - Change all passwords in .env
   - Use strong, unique passwords

3. **Configure CORS**
   - Update CORS_ALLOWED_ORIGINS for your domain
   - Remove localhost entries

4. **Firewall Rules**
   - Only expose ports 80/443 publicly
   - Restrict database access

### Performance Optimization

1. **Resource Limits**
   - Review and adjust in .env:
     - ORCHESTRATOR_MEMORY_LIMIT
     - POSTGRES_MEMORY_LIMIT
     - CPU limits

2. **Database Tuning**
   - Adjust PostgreSQL configuration
   - Set appropriate connection pool sizes

3. **Monitoring Setup**
   - Enable Prometheus/Grafana
   - Configure alerts

### Backup Configuration

1. **Enable Automated Backups**
   ```bash
   BACKUP_ENABLED=true
   BACKUP_SCHEDULE="0 2 * * *"
   BACKUP_RETENTION_DAYS=30
   ```

2. **Test Restore Process**
   - Document restore procedures
   - Test regularly

## Maintenance Procedures

### Regular Tasks

- [ ] **Weekly**: Review logs for errors
- [ ] **Monthly**: Update SSL certificates (if needed)
- [ ] **Quarterly**: Update dependencies
- [ ] **Annually**: Review and update passwords

### Update Procedure

```powershell
# 1. Backup current configuration
./scripts/backup_config.ps1

# 2. Pull updates
git pull

# 3. Re-run validation
./scripts/validate_deployment.ps1

# 4. Apply updates
docker compose down
docker compose up -d
```

## Emergency Procedures

### System Recovery

1. **Service Failure**
   ```powershell
   # Restart specific service
   docker compose restart <service-name>
   
   # Full system restart
   docker compose down
   docker compose up -d
   ```

2. **Database Recovery**
   ```powershell
   # Restore from backup
   ./scripts/restore_database.ps1 -BackupFile <path>
   ```

3. **Configuration Rollback**
   ```powershell
   # Restore previous configuration
   cp .env.backup.<timestamp> .env
   docker compose down
   docker compose up -d
   ```

## Validation Scripts

All validation can be automated:

```powershell
# Pre-deployment validation
./scripts/validate_deployment.ps1

# Post-deployment verification
./scripts/verify_deployment.ps1

# Continuous monitoring
./scripts/monitor_health.ps1
```

---

Last Updated: 2024-01-20
Version: 1.0.0