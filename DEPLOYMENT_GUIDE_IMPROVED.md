# DEAN System Deployment Guide (Improved)

This guide provides streamlined deployment instructions for the DEAN system, addressing common issues and providing automated solutions.

## Quick Start (Development)

For a quick local development setup:

```bash
cd DEAN
./quick_start.sh
```

This will:
- Create a development .env file with secure defaults
- Generate self-signed SSL certificates
- Start all services
- Display access URLs

## Production Deployment

### Prerequisites

1. **System Requirements**:
   - Docker 20.10+ and Docker Compose 1.29+
   - 16GB+ RAM (8GB for Docker)
   - 50GB+ free disk space
   - Ports 80, 443, 8080-8083 available

2. **Environment Setup**:
   ```bash
   # Copy environment template
   cp .env.template .env
   
   # Edit .env with production values
   # IMPORTANT: Change all CHANGE_ME values!
   nano .env
   ```

### Automated Deployment

Use the comprehensive deployment script:

```bash
cd DEAN
./scripts/deploy/deploy_dean_system.sh
```

This script:
1. Validates environment variables
2. Checks port availability
3. Generates SSL certificates (if needed)
4. Builds Docker images
5. Starts services in correct order
6. Verifies deployment health

### Manual Deployment Steps

If you prefer manual control:

#### 1. Validate Environment
```bash
./scripts/deploy/validate_environment.sh
```

#### 2. Check Ports
```bash
./scripts/deploy/check_ports.sh
```

#### 3. Setup SSL Certificates
```bash
# For self-signed (development/testing)
USE_SELF_SIGNED=true ./scripts/deploy/setup_ssl_certificates.sh

# For production (place certificates first)
cp /path/to/your/cert.pem ./certs/server.crt
cp /path/to/your/key.pem ./certs/server.key
```

#### 4. Start Services
```bash
# Use improved docker-compose with better health checks
docker-compose -f docker-compose.prod.improved.yml up -d
```

## Troubleshooting

### Quick Diagnostics

Run the troubleshooting script:

```bash
./scripts/troubleshoot.sh
```

### Common Issues and Solutions

#### 1. Nginx SSL Certificate Error

**Error**: `nginx: [emerg] cannot load certificate "/etc/nginx/certs/server.crt"`

**Solution**:
```bash
# Generate certificates
./scripts/deploy/setup_ssl_certificates.sh

# Verify certificates exist
ls -la ./certs/

# Restart nginx
docker-compose -f docker-compose.prod.yml restart nginx
```

#### 2. Port Conflicts

**Error**: `bind: address already in use`

**Solution**:
```bash
# Check what's using the ports
./scripts/deploy/check_ports.sh

# Option 1: Stop conflicting service
sudo systemctl stop apache2  # Example

# Option 2: Change DEAN ports in .env
echo "NGINX_HTTP_PORT=8080" >> .env
echo "NGINX_HTTPS_PORT=8443" >> .env

# Option 3: Use no-nginx configuration
docker-compose -f docker-compose.no-nginx.yml up -d
```

#### 3. Database Connection Failed

**Error**: `FATAL: password authentication failed`

**Solution**:
```bash
# Check environment variables
grep POSTGRES .env

# Ensure containers can communicate
docker network ls
docker network inspect dean_network

# Test connection manually
docker exec -it dean-postgres psql -U $POSTGRES_USER
```

#### 4. Service Won't Start

**Error**: Container exits immediately

**Solution**:
```bash
# Check logs
docker-compose -f docker-compose.prod.yml logs [service-name]

# Check resource limits
docker stats

# Increase Docker resources in Docker Desktop settings
```

## Monitoring

### Enable Monitoring Stack

```bash
# Start monitoring services
docker-compose -f monitoring/docker-compose.monitoring.yml up -d

# Access:
# - Prometheus: http://localhost:9090
# - Grafana: http://localhost:3000 (admin/admin)
```

### View Metrics

1. Grafana dashboards available at `http://localhost:3000`
2. Prometheus metrics at `http://localhost:9090/targets`
3. Node exporter metrics at `http://localhost:9100/metrics`

## Backup and Recovery

### Automated Backups

Schedule the backup script:

```bash
# Add to crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * /path/to/DEAN/infra/scripts/backup_dean_data.sh
```

### Manual Backup

```bash
# Backup all data
./infra/scripts/backup_dean_data.sh

# Backup specific database
docker exec dean-postgres pg_dump -U $POSTGRES_USER $POSTGRES_DB > backup_$(date +%Y%m%d).sql
```

## Security Considerations

1. **Change Default Passwords**: 
   - All CHANGE_ME values in .env
   - Grafana admin password
   - Any default application passwords

2. **SSL/TLS**:
   - Use proper certificates in production
   - Configure HTTPS redirect in nginx
   - Enable HSTS headers

3. **Firewall**:
   - Limit access to management ports
   - Use IP whitelisting for sensitive endpoints

4. **Secrets Management**:
   - Consider using Docker secrets
   - Rotate JWT keys regularly
   - Use strong passwords (32+ characters)

## Scaling Considerations

### Horizontal Scaling

For multi-node deployment:

1. Use external PostgreSQL
2. Configure Redis cluster
3. Use load balancer for orchestrator
4. Share volumes via NFS/EFS

### Resource Optimization

Adjust in `.env`:
```bash
# CPU limits
ORCHESTRATOR_CPU_LIMIT=4.0

# Memory limits
ORCHESTRATOR_MEMORY_LIMIT=4g

# Connection pools
POSTGRES_MAX_CONNECTIONS=200
```

## Maintenance

### Updates

```bash
# Pull latest changes
git pull

# Rebuild and restart
docker-compose -f docker-compose.prod.yml up -d --build
```

### Health Checks

```bash
# Check all services
curl https://localhost/health

# Check specific service
docker exec dean-orchestrator curl localhost:8082/health
```

### Log Management

```bash
# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Clean old logs
docker-compose -f docker-compose.prod.yml logs --no-color > logs_$(date +%Y%m%d).txt
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d
```

## Support

- Check logs first: `docker-compose logs [service]`
- Run diagnostics: `./scripts/troubleshoot.sh`
- Review documentation in `/docs`
- GitHub Issues: https://github.com/your-org/DEAN/issues

## Quick Reference

### Essential Commands

```bash
# Start system
./quick_start.sh  # Development
./scripts/deploy/deploy_dean_system.sh  # Production

# Stop system
docker-compose -f docker-compose.prod.yml down

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Restart service
docker-compose -f docker-compose.prod.yml restart [service]

# Check health
curl https://localhost/health

# Troubleshoot
./scripts/troubleshoot.sh
```

### Service URLs

- Dashboard: https://localhost
- API: https://localhost/api/v1/
- Airflow: http://localhost:8080
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000

### Default Ports

| Service | Port | Configurable Via |
|---------|------|------------------|
| HTTP | 80 | NGINX_HTTP_PORT |
| HTTPS | 443 | NGINX_HTTPS_PORT |
| Orchestrator | 8082 | ORCHESTRATOR_PORT |
| Airflow | 8080 | AIRFLOW_PORT |
| IndexAgent | 8081 | INDEXAGENT_PORT |
| PostgreSQL | 5432 | POSTGRES_PORT |
| Redis | 6379 | REDIS_PORT |
| Prometheus | 9090 | PROMETHEUS_PORT |
| Grafana | 3000 | GRAFANA_PORT |