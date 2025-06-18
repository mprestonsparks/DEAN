# DEAN System Troubleshooting Guide

This guide provides solutions for common issues encountered during DEAN system deployment and operation, based on real deployment experiences.

## Table of Contents

1. [Configuration Issues](#configuration-issues)
2. [SSL/TLS Problems](#ssltls-problems)
3. [Database Connection Issues](#database-connection-issues)
4. [Service Startup Problems](#service-startup-problems)
5. [Network and Connectivity](#network-and-connectivity)
6. [PowerShell Specific Issues](#powershell-specific-issues)
7. [Docker Issues](#docker-issues)
8. [Performance Problems](#performance-problems)

## Configuration Issues

### BOM (Byte Order Mark) in Configuration Files

**Problem**: Nginx or other services fail to start with syntax errors in configuration files.

**Symptoms**:
```
nginx: [emerg] unknown directive "﻿server" in /etc/nginx/nginx.conf:1
```

**Root Cause**: Configuration files contain invisible BOM characters (often from Windows text editors).

**Solution**:
```powershell
# Automatic detection and removal
./scripts/validate_deployment.ps1 -AutoFix

# Manual check for specific file
$bytes = [System.IO.File]::ReadAllBytes("nginx/nginx.conf")
if ($bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
    Write-Host "BOM detected!"
}

# Remove BOM manually
$content = [System.IO.File]::ReadAllText("nginx/nginx.conf")
[System.IO.File]::WriteAllText("nginx/nginx.conf", $content, [System.Text.UTF8Encoding]::new($false))
```

**Prevention**: 
- Use UTF-8 without BOM encoding
- Configure editors to save without BOM
- Use validation script before deployment

### Environment Variable Mismatches

**Problem**: Services fail to connect due to mismatched environment variables.

**Common Mismatches**:
- Database name: `dean_prod` vs `dean_production`
- Missing required variables
- Placeholder values not replaced

**Solution**:
```powershell
# Validate all environment variables
./scripts/validate_deployment.ps1

# Check specific variable across files
Select-String -Path @(".env", "docker-compose.yml", "docker-compose.prod.yml") -Pattern "POSTGRES_DB"
```

**Best Practice**: Use consistent naming throughout all configuration files.

## SSL/TLS Problems

### Missing SSL Certificates

**Problem**: Nginx fails to start due to missing certificate files.

**Error Message**:
```
nginx: [emerg] cannot load certificate "/etc/nginx/certs/server.crt": BIO_new_file() failed
```

**Solution**:
```powershell
# For development (self-signed)
./scripts/setup_ssl.ps1 -Environment development

# For production
./scripts/setup_ssl.ps1 -ShowInstructions
```

### PowerShell HTTPS Connection Failures

**Problem**: PowerShell cannot connect to HTTPS endpoints with self-signed certificates.

**Error**:
```
Invoke-WebRequest : The underlying connection was closed: Could not establish trust relationship
```

**Solutions**:

1. **For Testing Only** (Not for production):
```powershell
# Bypass certificate validation temporarily
[System.Net.ServicePointManager]::ServerCertificateValidationCallback = {$true}
```

2. **Better Approach**:
```powershell
# Use browser for testing
Start-Process "https://localhost/health"

# Or use curl with insecure flag
curl -k https://localhost/health
```

3. **Production Fix**: Install proper CA-signed certificates.

### Certificate Name Mismatches

**Problem**: Services expect different certificate filenames.

**Solution**: The setup script creates multiple copies:
- `server.crt/server.key` (primary)
- `localhost.crt/localhost.key` (alternative)
- `nginx.crt/nginx.key` (nginx-specific)

## Database Connection Issues

### Database Name Mismatch

**Problem**: Application cannot connect to database.

**Error**:
```
FATAL: database "dean_prod" does not exist
```

**Root Cause**: Inconsistent database naming between `.env` and `docker-compose.yml`.

**Solution**:
1. Ensure `.env` contains:
   ```
   POSTGRES_DB=dean_production
   ```

2. Verify docker-compose.yml uses same name:
   ```yaml
   environment:
     POSTGRES_DB: ${POSTGRES_DB}
   ```

3. Rebuild containers:
   ```powershell
   docker compose down -v  # Warning: removes volumes
   docker compose up -d
   ```

### Connection Pool Exhaustion

**Problem**: Database connections timeout under load.

**Solution**:
```bash
# In .env
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10

# Monitor connections
docker exec dean-postgres psql -U dean_prod -c "SELECT count(*) FROM pg_stat_activity;"
```

## Service Startup Problems

### Service Dependencies Not Ready

**Problem**: Services fail because dependencies aren't ready.

**Solution**: Ensure proper health checks in docker-compose.yml:
```yaml
postgres:
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U dean_prod"]
    interval: 5s
    timeout: 5s
    retries: 5

orchestrator:
  depends_on:
    postgres:
      condition: service_healthy
```

### Port Conflicts

**Problem**: Services cannot bind to required ports.

**Diagnosis**:
```powershell
# Check port usage
netstat -an | findstr :80
netstat -an | findstr :443
netstat -an | findstr :8082
```

**Solutions**:
1. Stop conflicting services
2. Change port mappings in docker-compose.yml
3. Use the validation script to check ports before deployment

## Network and Connectivity

### CORS Errors

**Problem**: Browser blocks API requests due to CORS.

**Browser Console Error**:
```
Access to XMLHttpRequest blocked by CORS policy
```

**Solution**:
1. Update `.env`:
   ```
   CORS_ALLOWED_ORIGINS=http://localhost,https://localhost,http://yourdomain.com
   ```

2. Restart orchestrator:
   ```powershell
   docker compose restart orchestrator
   ```

### Container Network Issues

**Problem**: Containers cannot communicate with each other.

**Diagnosis**:
```powershell
# Test connectivity between containers
docker exec dean-orchestrator ping dean-postgres
docker exec dean-orchestrator curl http://dean-redis:6379
```

**Solution**: Ensure all services are on the same Docker network.

## PowerShell Specific Issues

### Execution Policy Restrictions

**Problem**: PowerShell scripts won't run.

**Error**:
```
cannot be loaded because running scripts is disabled on this system
```

**Solution**:
```powershell
# For current session only
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process

# Or for current user
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Path and Encoding Issues

**Problem**: Scripts fail due to path or encoding problems.

**Solutions**:
1. Use forward slashes in paths: `./scripts/setup.ps1`
2. Save scripts with UTF-8 encoding (no BOM)
3. Use absolute paths when needed

## Docker Issues

### Disk Space

**Problem**: Docker operations fail due to insufficient space.

**Diagnosis**:
```powershell
# Check Docker disk usage
docker system df

# Clean up unused resources
docker system prune -a
```

### Container Logs Filling Disk

**Problem**: Log files grow unbounded.

**Solution**: Configure log rotation in docker-compose.yml:
```yaml
services:
  orchestrator:
    logging:
      driver: "json-file"
      options:
        max-size: "100m"
        max-file: "3"
```

### Docker Daemon Not Running

**Problem**: Docker commands fail with connection errors.

**Solution**:
```powershell
# Windows
Start-Service Docker

# Or restart Docker Desktop
# System tray -> Docker Desktop -> Restart
```

## Performance Problems

### Slow Response Times

**Diagnosis Steps**:
1. Check resource usage:
   ```powershell
   docker stats
   ```

2. Check logs for errors:
   ```powershell
   docker logs dean-orchestrator --tail 100 | Select-String ERROR
   ```

3. Monitor database queries:
   ```sql
   -- Long running queries
   SELECT pid, now() - pg_stat_activity.query_start AS duration, query 
   FROM pg_stat_activity 
   WHERE (now() - pg_stat_activity.query_start) > interval '5 minutes';
   ```

**Solutions**:
- Increase resource limits in .env
- Add database indexes
- Enable caching in Redis

### Memory Leaks

**Symptoms**: Container memory usage grows continuously.

**Monitoring**:
```powershell
# Watch memory usage over time
while ($true) {
    docker stats --no-stream
    Start-Sleep -Seconds 60
}
```

**Solutions**:
1. Set memory limits in docker-compose.yml
2. Enable container restart on failure
3. Investigate application code for leaks

## Quick Diagnostic Commands

```powershell
# System health check
./scripts/troubleshoot.sh

# Service status
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Recent logs from all services
docker compose logs --tail=20

# Database connection test
docker exec dean-postgres pg_isready

# Redis connection test
docker exec dean-redis redis-cli ping

# API health check
curl http://localhost:8082/health

# Nginx status
docker exec dean-nginx nginx -t
```

## Getting Help

If issues persist after trying these solutions:

1. **Collect Diagnostic Information**:
   ```powershell
   # Generate diagnostic report
   ./scripts/generate_diagnostic_report.ps1
   ```

2. **Check Logs**:
   - Application logs: `./logs/`
   - Docker logs: `docker logs <container-name>`
   - System logs: Event Viewer (Windows) or `/var/log/` (Linux)

3. **Community Support**:
   - GitHub Issues: [Report bugs and issues]
   - Documentation: Check `/docs` folder
   - Wiki: Additional troubleshooting tips

---

Last Updated: 2024-01-20
Version: 1.0.0