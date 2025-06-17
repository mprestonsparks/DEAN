# DEAN Production Deployment Guide

This comprehensive guide provides everything needed to deploy the DEAN Orchestration System in a production environment. Follow this guide step-by-step for a successful deployment.

## Table of Contents

1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Step-by-Step Deployment](#step-by-step-deployment)
3. [Production Configuration](#production-configuration)
4. [Security Hardening](#security-hardening)
5. [Performance Optimization](#performance-optimization)
6. [Monitoring Setup](#monitoring-setup)
7. [Backup and Recovery](#backup-and-recovery)
8. [Troubleshooting](#troubleshooting)

---

## Pre-Deployment Checklist

### System Requirements Verification

- [ ] **Hardware Requirements Met**
  - CPU: 8+ cores (Intel i7 or equivalent)
  - RAM: 32GB minimum
  - Storage: 100GB+ SSD
  - Network: Stable internet, static IP

- [ ] **Software Prerequisites Installed**
  - Docker 20.10+
  - Docker Compose 2.0+
  - Python 3.10+
  - Git (latest version)

- [ ] **Infrastructure Prepared**
  - Domain name configured
  - SSL certificates obtained
  - Firewall rules defined
  - Backup storage configured

- [ ] **Security Preparations**
  - Admin accounts created
  - Password policy defined
  - Access control lists prepared
  - Security team notified

### Pre-Deployment Validation

```bash
# Run system validation
./scripts/pre_deployment_check.sh

# Expected output: All checks should pass
```

---

## Step-by-Step Deployment

### 1. Clone and Prepare Repository

```bash
# Clone the repository
git clone https://github.com/your-org/dean-orchestration.git
cd dean-orchestration/DEAN

# Checkout stable release
git checkout tags/v1.0.0

# Set correct permissions
chmod +x scripts/*.sh
chmod 600 .env.production
```

### 2. Configure Production Environment

```bash
# Copy production template
cp .env.production.template .env

# Edit configuration
vim .env
```

**Critical Configuration Items**:
```bash
# Environment
DEAN_ENV=production
DEBUG=false

# Database (use strong passwords)
POSTGRES_PASSWORD=<generate-strong-password>
POSTGRES_HOST=postgres-prod
POSTGRES_DB=dean_production

# Redis
REDIS_PASSWORD=<generate-strong-password>

# JWT Security
JWT_SECRET_KEY=<generate-with-openssl>
JWT_ALGORITHM=HS256

# SSL/TLS
ENFORCE_HTTPS=true
SSL_CERT_PATH=/certs/production.crt
SSL_KEY_PATH=/certs/production.key

# Allowed Origins (your domains only)
ALLOWED_ORIGINS=https://dean.yourcompany.com

# Resource Limits
MAX_WORKERS=16
MAX_MEMORY_PER_WORKER=2G
```

### 3. Install SSL Certificates

```bash
# Create certificate directory
mkdir -p certs

# Copy your certificates
cp /path/to/your/domain.crt certs/production.crt
cp /path/to/your/domain.key certs/production.key

# Set permissions
chmod 600 certs/*
```

### 4. Build Production Images

```bash
# Build with production optimizations
docker-compose -f docker-compose.prod.yml build --no-cache

# Verify images
docker images | grep dean
```

### 5. Initialize Database

```bash
# Start only database service
docker-compose -f docker-compose.prod.yml up -d postgres-prod

# Wait for initialization
sleep 10

# Run migrations
docker-compose -f docker-compose.prod.yml run --rm orchestrator python -m alembic upgrade head

# Create initial admin user
docker-compose -f docker-compose.prod.yml run --rm orchestrator python scripts/create_admin.py
```

### 6. Start All Services

```bash
# Start in detached mode
docker-compose -f docker-compose.prod.yml up -d

# Verify all services are running
docker-compose -f docker-compose.prod.yml ps

# Check logs
docker-compose -f docker-compose.prod.yml logs -f
```

### 7. Verify Deployment

```bash
# Run production validation
./scripts/final_validation.sh --production

# Test endpoints
curl -k https://your-domain.com/health
curl -k https://your-domain.com/api/docs
```

---

## Production Configuration

### Docker Compose Production Override

Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  orchestrator:
    image: dean/orchestrator:1.0.0
    restart: always
    environment:
      - DEAN_ENV=production
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G
        reservations:
          cpus: '2'
          memory: 4G
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8082/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  postgres-prod:
    image: postgres:15-alpine
    restart: always
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backups/postgres:/backups
    environment:
      - POSTGRES_PASSWORD_FILE=/run/secrets/db_password
    secrets:
      - db_password
    deploy:
      resources:
        limits:
          memory: 4G

  redis-prod:
    image: redis:7-alpine
    restart: always
    command: redis-server --requirepass ${REDIS_PASSWORD} --maxmemory 2gb --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data
    deploy:
      resources:
        limits:
          memory: 2G

  nginx:
    image: nginx:alpine
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.prod.conf:/etc/nginx/nginx.conf:ro
      - ./certs:/etc/nginx/certs:ro
    depends_on:
      - orchestrator

volumes:
  postgres_data:
    driver: local
  redis_data:
    driver: local

secrets:
  db_password:
    file: ./secrets/db_password.txt
```

### Nginx Production Configuration

Create `nginx/nginx.prod.conf`:

```nginx
events {
    worker_connections 1024;
}

http {
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self' https:; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline';" always;

    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=auth:10m rate=5r/m;

    # Upstream servers
    upstream orchestrator {
        server orchestrator:8082;
    }

    upstream evolution {
        server evolution-api:8083;
    }

    upstream indexagent {
        server indexagent:8081;
    }

    # HTTP to HTTPS redirect
    server {
        listen 80;
        server_name dean.yourcompany.com;
        return 301 https://$server_name$request_uri;
    }

    # HTTPS server
    server {
        listen 443 ssl http2;
        server_name dean.yourcompany.com;

        ssl_certificate /etc/nginx/certs/production.crt;
        ssl_certificate_key /etc/nginx/certs/production.key;

        # API endpoints
        location /api/ {
            limit_req zone=api burst=20 nodelay;
            proxy_pass http://orchestrator;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Authentication endpoints (stricter rate limit)
        location /auth/ {
            limit_req zone=auth burst=5 nodelay;
            proxy_pass http://orchestrator;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }

        # WebSocket support
        location /ws {
            proxy_pass http://evolution;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_read_timeout 86400;
        }

        # Static files
        location / {
            root /usr/share/nginx/html;
            try_files $uri $uri/ /index.html;
        }
    }
}
```

---

## Security Hardening

### 1. Run Security Hardening Script

```bash
# Execute hardening
sudo ./scripts/production_hardening.sh

# Verify hardening
./scripts/security_audit.py --production
```

### 2. Configure Fail2ban

```bash
# Install fail2ban
sudo apt-get install fail2ban

# Configure for DEAN
sudo cp configs/fail2ban/dean.conf /etc/fail2ban/filter.d/
sudo cp configs/fail2ban/dean.local /etc/fail2ban/jail.d/

# Restart fail2ban
sudo systemctl restart fail2ban
```

### 3. Enable Audit Logging

```bash
# Configure auditd
sudo apt-get install auditd
sudo auditctl -w /opt/dean -p wa -k dean_changes
sudo auditctl -w /etc/dean -p wa -k dean_config
```

### 4. Network Security

```bash
# Configure UFW firewall
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp  # SSH
sudo ufw allow 80/tcp  # HTTP
sudo ufw allow 443/tcp # HTTPS
sudo ufw enable
```

---

## Performance Optimization

### 1. Database Optimization

```sql
-- Connect to PostgreSQL
docker exec -it postgres-prod psql -U dean -d dean_production

-- Optimize settings
ALTER SYSTEM SET shared_buffers = '4GB';
ALTER SYSTEM SET effective_cache_size = '12GB';
ALTER SYSTEM SET maintenance_work_mem = '1GB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;
ALTER SYSTEM SET random_page_cost = 1.1;

-- Create indexes
CREATE INDEX CONCURRENTLY idx_agents_created ON agents(created_at);
CREATE INDEX CONCURRENTLY idx_trials_status ON evolution_trials(status);
CREATE INDEX CONCURRENTLY idx_patterns_confidence ON patterns(confidence);

-- Analyze tables
ANALYZE;
```

### 2. Redis Optimization

```bash
# Edit Redis configuration
docker exec -it redis-prod redis-cli

# Set performance parameters
CONFIG SET maxmemory-policy allkeys-lru
CONFIG SET tcp-keepalive 60
CONFIG SET timeout 300
CONFIG REWRITE
```

### 3. Application Optimization

```python
# In .env file
# Increase worker processes
UVICORN_WORKERS=8
MAX_WORKERS=16

# Enable response caching
ENABLE_CACHE=true
CACHE_TTL=300

# Connection pooling
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40
```

---

## Monitoring Setup

### 1. Prometheus Configuration

Create `monitoring/prometheus.yml`:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'dean-orchestrator'
    static_configs:
      - targets: ['orchestrator:8082']
    metrics_path: '/metrics'

  - job_name: 'dean-evolution'
    static_configs:
      - targets: ['evolution-api:8083']
    metrics_path: '/metrics'

  - job_name: 'dean-indexagent'
    static_configs:
      - targets: ['indexagent:8081']
    metrics_path: '/metrics'

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']
```

### 2. Grafana Dashboards

Import provided dashboards:

```bash
# Import dashboards
curl -X POST http://admin:admin@localhost:3000/api/dashboards/import \
  -H "Content-Type: application/json" \
  -d @monitoring/dashboards/dean-overview.json

curl -X POST http://admin:admin@localhost:3000/api/dashboards/import \
  -H "Content-Type: application/json" \
  -d @monitoring/dashboards/dean-performance.json
```

### 3. Alert Rules

Create `monitoring/alerts.yml`:

```yaml
groups:
  - name: dean_alerts
    interval: 30s
    rules:
      - alert: ServiceDown
        expr: up == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Service {{ $labels.job }} is down"

      - alert: HighMemoryUsage
        expr: container_memory_usage_bytes / container_spec_memory_limit_bytes > 0.9
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage in {{ $labels.container_name }}"

      - alert: HighResponseTime
        expr: http_request_duration_seconds{quantile="0.95"} > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High response time for {{ $labels.handler }}"
```

---

## Backup and Recovery

### 1. Automated Backup Setup

```bash
# Create backup script
cat > /opt/dean/scripts/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/backups/dean"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Database backup
docker exec postgres-prod pg_dump -U dean dean_production | gzip > "$BACKUP_DIR/db_$TIMESTAMP.sql.gz"

# Redis backup
docker exec redis-prod redis-cli BGSAVE
sleep 5
docker cp redis-prod:/data/dump.rdb "$BACKUP_DIR/redis_$TIMESTAMP.rdb"

# Configuration backup
tar -czf "$BACKUP_DIR/config_$TIMESTAMP.tar.gz" /opt/dean/.env /opt/dean/configs/

# Cleanup old backups (keep 30 days)
find "$BACKUP_DIR" -type f -mtime +30 -delete
EOF

chmod +x /opt/dean/scripts/backup.sh

# Add to crontab
echo "0 2 * * * /opt/dean/scripts/backup.sh" | crontab -
```

### 2. Recovery Procedures

```bash
# Database recovery
gunzip < /backups/dean/db_20240115_020000.sql.gz | docker exec -i postgres-prod psql -U dean dean_production

# Redis recovery
docker cp /backups/dean/redis_20240115_020000.rdb redis-prod:/data/dump.rdb
docker exec redis-prod redis-cli SHUTDOWN NOSAVE
docker restart redis-prod

# Configuration recovery
tar -xzf /backups/dean/config_20240115_020000.tar.gz -C /
```

---

## Troubleshooting

### Common Issues and Solutions

#### 1. Services Won't Start

```bash
# Check logs
docker-compose -f docker-compose.prod.yml logs --tail=100

# Verify permissions
ls -la /opt/dean/
ls -la /opt/dean/certs/

# Check disk space
df -h

# Verify Docker daemon
systemctl status docker
```

#### 2. Authentication Failures

```bash
# Check JWT secret
grep JWT_SECRET .env

# Verify Redis connection
docker exec redis-prod redis-cli ping

# Check user database
docker exec postgres-prod psql -U dean -d dean_production -c "SELECT * FROM users;"
```

#### 3. Performance Issues

```bash
# Check resource usage
docker stats

# Database connections
docker exec postgres-prod psql -U dean -c "SELECT count(*) FROM pg_stat_activity;"

# Redis memory
docker exec redis-prod redis-cli info memory

# API response times
curl -w "@curl-format.txt" -o /dev/null -s https://your-domain/api/health
```

#### 4. WebSocket Connection Issues

```bash
# Test WebSocket endpoint
wscat -c wss://your-domain/ws

# Check Nginx logs
docker logs nginx --tail=50

# Verify upgrade headers
curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" https://your-domain/ws
```

### Emergency Procedures

#### System Recovery

```bash
# Stop all services
docker-compose -f docker-compose.prod.yml down

# Restore from backup
./scripts/restore_from_backup.sh

# Start services
docker-compose -f docker-compose.prod.yml up -d

# Verify system health
./scripts/health_check.sh --production
```

#### Rollback Procedure

```bash
# Tag current version
docker tag dean/orchestrator:latest dean/orchestrator:rollback

# Restore previous version
docker tag dean/orchestrator:v0.9.9 dean/orchestrator:latest

# Restart services
docker-compose -f docker-compose.prod.yml up -d
```

---

## Post-Deployment Verification

### Final Checklist

- [ ] All services are running
- [ ] HTTPS is working correctly
- [ ] Authentication is functional
- [ ] API endpoints respond correctly
- [ ] WebSocket connections work
- [ ] Monitoring is active
- [ ] Backups are scheduled
- [ ] Security scans pass
- [ ] Performance meets requirements
- [ ] Documentation is accessible

### Success Metrics

Monitor these metrics post-deployment:

1. **Availability**: > 99.9% uptime
2. **Response Time**: < 200ms average
3. **Error Rate**: < 0.1%
4. **CPU Usage**: < 60% average
5. **Memory Usage**: < 70% average

---

## Support Information

### Documentation References

- Architecture Guide: `/docs/ARCHITECTURE.md`
- API Reference: `/docs/api/`
- Security Guide: `/docs/SECURITY_GUIDE.md`
- Operations Runbook: `/docs/OPERATIONS_RUNBOOK.md`

### Contact Information

- Operations Team: ops@yourcompany.com
- Security Team: security@yourcompany.com
- On-Call: +1-XXX-XXX-XXXX

### Useful Commands Reference

```bash
# Service management
docker-compose -f docker-compose.prod.yml [up|down|restart|logs|ps]

# Health checks
./scripts/health_check.sh --production

# Security audit
./scripts/security_audit.py --production

# Performance test
./scripts/performance_test.py --production

# Backup
./scripts/backup.sh

# Monitoring
curl http://localhost:9090/metrics  # Prometheus
curl http://localhost:3000          # Grafana
```

---

**Last Updated**: 2025-06-15
**Version**: 1.0.0
**Status**: Production Ready