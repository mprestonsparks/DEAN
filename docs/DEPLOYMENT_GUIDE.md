# DEAN Orchestration System Deployment Guide

## Table of Contents
1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Deployment Options](#deployment-options)
4. [Security Configuration](#security-configuration)
5. [Single Machine Deployment](#single-machine-deployment)
6. [Distributed Deployment](#distributed-deployment)
7. [SSL/TLS Configuration](#ssltls-configuration)
8. [Post-Deployment](#post-deployment)
9. [Troubleshooting](#troubleshooting)

## Overview

This guide provides step-by-step instructions for deploying the DEAN orchestration system in production environments. It covers security configuration, deployment options, and best practices for maintaining a secure and reliable system.

## Prerequisites

### System Requirements
- **OS**: Ubuntu 20.04+ or RHEL 8+
- **CPU**: 4+ cores recommended
- **RAM**: 16GB minimum, 32GB recommended
- **Storage**: 100GB+ SSD
- **Network**: Static IP, open required ports

### Software Requirements
- Docker 20.10+
- Docker Compose 2.0+
- Python 3.10+
- PostgreSQL 14+ (for production data)
- Redis 6+ (for caching)
- Nginx (for reverse proxy)

### Required Ports
- **8082**: DEAN Orchestrator (HTTPS)
- **8080**: Airflow Web UI
- **8081**: IndexAgent API
- **8083**: Evolution API
- **8091**: DEAN API (includes Economic Governor)
- **5432**: PostgreSQL (internal)
- **6379**: Redis (internal)

## Deployment Options

### 1. Development Deployment
- Single machine with Docker Compose
- Self-signed certificates
- Default credentials (must change!)
- Suitable for testing only

### 2. Production Single Machine
- Single powerful server
- Let's Encrypt certificates
- External PostgreSQL
- Monitoring enabled
- Backup configured

### 3. Production Distributed
- Multiple servers for services
- Load balancing
- High availability
- Kubernetes orchestration
- Centralized logging

## Security Configuration

### Pre-Deployment Security Checklist

```bash
# 1. Generate secure passwords
export ADMIN_PASSWORD=$(openssl rand -base64 32)
export DB_PASSWORD=$(openssl rand -base64 32)
export JWT_SECRET=$(openssl rand -base64 64)
export AIRFLOW_PASSWORD=$(openssl rand -base64 32)

# 2. Create secrets file
cat > .env.production << EOF
# Database
POSTGRES_PASSWORD=${DB_PASSWORD}
POSTGRES_USER=dean_prod
POSTGRES_DB=dean_production

# Authentication
JWT_SECRET_KEY=${JWT_SECRET}
ADMIN_PASSWORD=${ADMIN_PASSWORD}
AIRFLOW_USERNAME=airflow
AIRFLOW_PASSWORD=${AIRFLOW_PASSWORD}

# Security
ENFORCE_HTTPS=true
ALLOWED_ORIGINS=https://your-domain.com
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_HTTPONLY=true
SESSION_COOKIE_SAMESITE=strict

# API Keys
SERVICE_API_KEY=$(openssl rand -base64 32)
EVOLUTION_SERVICE_KEY=$(openssl rand -base64 32)
INDEXAGENT_SERVICE_KEY=$(openssl rand -base64 32)

# Economic Governor Settings
ECONOMIC_TOTAL_BUDGET=1000000
DEAN_API_URL=http://localhost:8091
EOF

# 3. Secure the secrets file
chmod 600 .env.production
```

### Firewall Configuration

```bash
# Ubuntu/Debian
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 443/tcp  # HTTPS
sudo ufw allow 80/tcp   # HTTP (redirect to HTTPS)
sudo ufw enable

# RHEL/CentOS
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --reload
```

## Single Machine Deployment

### Step 1: Prepare the Server

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    nginx \
    certbot \
    python3-certbot-nginx

# Install Docker
curl -fsSL https://get.docker.com | sudo bash
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### Step 2: Clone and Configure

```bash
# Clone repository
git clone https://github.com/your-org/dean-orchestration.git
cd dean-orchestration

# Copy production configuration
cp configs/deployment/production_single_machine.yaml config.yaml
cp docker-compose.prod.yml docker-compose.yml

# Load environment variables
source .env.production
```

### Step 3: SSL/TLS Setup

```bash
# Get Let's Encrypt certificate
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# Configure Nginx reverse proxy
sudo cat > /etc/nginx/sites-available/dean << 'EOF'
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Main orchestrator
    location / {
        proxy_pass https://localhost:8082;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
    
    # Airflow UI (with additional auth)
    location /airflow/ {
        auth_basic "Airflow Admin";
        auth_basic_user_file /etc/nginx/.htpasswd;
        
        proxy_pass http://localhost:8080/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}

server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}
EOF

sudo ln -s /etc/nginx/sites-available/dean /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

### Step 4: Deploy Services

```bash
# Initialize database
./scripts/deploy/init_database.sh

# Deploy with production settings
./scripts/deploy/deploy_production_single.sh

# Verify deployment
./scripts/deploy/health_check.sh
```

### Step 5: Post-Deployment Security

```bash
# 1. Change default admin password
docker exec -it dean-orchestrator dean-cli user change-password \
    --username admin \
    --old-password admin123 \
    --new-password "$ADMIN_PASSWORD"

# 2. Create service accounts
docker exec -it dean-orchestrator dean-cli user create \
    --username evolution-service \
    --password "$EVOLUTION_SERVICE_KEY" \
    --roles service

# 3. Generate API keys for monitoring
docker exec -it dean-orchestrator dean-cli apikey create \
    --name "Prometheus Monitoring" \
    --roles viewer \
    --description "Read-only access for metrics"

# 4. Verify security settings
docker exec -it dean-orchestrator dean-cli security verify
```

## Distributed Deployment

### Architecture Overview

```
                    ┌─────────────┐
                    │ Load Balancer│
                    └──────┬──────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
   ┌────▼────┐       ┌────▼────┐       ┌────▼────┐
   │ DEAN-1  │       │ DEAN-2  │       │ DEAN-3  │
   │(Primary)│       │(Replica)│       │(Replica)│
   └────┬────┘       └────┬────┘       └────┬────┘
        │                  │                  │
        └──────────────────┼──────────────────┘
                           │
                    ┌──────▼──────┐
                    │  PostgreSQL  │
                    │   Cluster    │
                    └─────────────┘
```

### Kubernetes Deployment

```yaml
# dean-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dean-orchestrator
spec:
  replicas: 3
  selector:
    matchLabels:
      app: dean-orchestrator
  template:
    metadata:
      labels:
        app: dean-orchestrator
    spec:
      containers:
      - name: dean
        image: dean-orchestrator:latest
        ports:
        - containerPort: 8082
        env:
        - name: JWT_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: dean-secrets
              key: jwt-secret
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: dean-secrets
              key: database-url
        livenessProbe:
          httpGet:
            path: /health
            port: 8082
            scheme: HTTPS
          initialDelaySeconds: 30
          periodSeconds: 10
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
```

## SSL/TLS Configuration

### Self-Signed Certificates (Development)

```bash
# Generate self-signed certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout ./certs/server.key \
    -out ./certs/server.crt \
    -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
```

### Production Certificates

```bash
# Using Let's Encrypt with auto-renewal
sudo certbot certonly --standalone -d your-domain.com
sudo systemctl enable certbot.timer

# Configure auto-renewal hook
sudo cat > /etc/letsencrypt/renewal-hooks/deploy/dean-reload.sh << 'EOF'
#!/bin/bash
docker exec dean-orchestrator supervisorctl restart all
EOF
sudo chmod +x /etc/letsencrypt/renewal-hooks/deploy/dean-reload.sh
```

## Economic Governor Configuration

The Economic Governor manages token budgets and resource allocation across the DEAN system. It is now exposed via REST API endpoints through the DEAN API service.

### API Endpoints

The Economic Governor provides the following endpoints:

- **GET /api/v1/economy/metrics** - System-wide economic metrics
- **GET /api/v1/economy/agent/{agent_id}** - Individual agent budget status
- **POST /api/v1/economy/use-tokens** - Record token usage
- **POST /api/v1/economy/allocate** - Allocate tokens to agents
- **POST /api/v1/economy/rebalance** - Trigger budget rebalancing

### Configuration

```bash
# Environment variables for Economic Governor
ECONOMIC_TOTAL_BUDGET=1000000      # Total system token budget
ECONOMIC_BASE_ALLOCATION=1000      # Base tokens per new agent
ECONOMIC_PERFORMANCE_MULTIPLIER=1.5 # Performance bonus multiplier
ECONOMIC_DECAY_RATE=0.1            # Decay rate for inactive agents
ECONOMIC_RESERVE_RATIO=0.2         # Reserve budget ratio

# Database tables (auto-created)
# - token_allocations: Tracks token allocations to agents
# - token_usage: Records token consumption by actions
```

### Integration with Airflow DAGs

The DEAN evolution DAGs use the Economic Governor API client instead of direct imports:

```python
from dean.utils.economic_client import EconomicGovernorClient

# Check global budget
client = EconomicGovernorClient()
metrics = client.get_system_metrics()

# Record token usage
client.use_tokens(
    agent_id="agent_001",
    tokens=100,
    action_type="optimization",
    task_success=0.8,
    quality_score=0.9
)
```

### Monitoring Economic Health

```bash
# Check economic metrics
curl -X GET https://localhost:8091/api/v1/economy/metrics

# View top performers
curl -X GET https://localhost:8091/api/v1/economy/metrics | jq '.top_performers'

# Check specific agent budget
curl -X GET https://localhost:8091/api/v1/economy/agent/agent_001
```

### Troubleshooting Economic Issues

1. **Insufficient Budget Errors**
```bash
# Check available budget
curl https://localhost:8091/api/v1/economy/metrics | jq '.global_budget.available'

# Trigger rebalancing
curl -X POST https://localhost:8091/api/v1/economy/rebalance
```

2. **Token Allocation Failures**
```bash
# Check agent existence in economic system
curl https://localhost:8091/api/v1/economy/agent/{agent_id}

# Manually allocate tokens if needed
curl -X POST https://localhost:8091/api/v1/economy/allocate \
  -H "Content-Type: application/json" \
  -d '{"agent_id": "agent_001", "performance": 0.8, "generation": 1}'
```

## Post-Deployment

### Security Hardening

1. **SELinux Configuration** (RHEL/CentOS)
```bash
sudo setsebool -P httpd_can_network_connect 1
sudo semanage port -a -t http_port_t -p tcp 8082
```

2. **System Hardening**
```bash
# Disable root SSH
sudo sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config

# Configure fail2ban
sudo apt install fail2ban
sudo systemctl enable fail2ban
```

### Monitoring Setup

```bash
# Deploy Prometheus
docker run -d \
    --name prometheus \
    --network dean-network \
    -p 9090:9090 \
    -v $(pwd)/monitoring/prometheus.yml:/etc/prometheus/prometheus.yml \
    prom/prometheus

# Deploy Grafana
docker run -d \
    --name grafana \
    --network dean-network \
    -p 3000:3000 \
    -e "GF_SECURITY_ADMIN_PASSWORD=$ADMIN_PASSWORD" \
    grafana/grafana
```

### Backup Configuration

```bash
# Create backup script
cat > /opt/dean/backup.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/dean"

# Backup database
docker exec dean-postgres pg_dump -U dean_prod dean_production | \
    gzip > "${BACKUP_DIR}/db_${DATE}.sql.gz"

# Backup configuration
tar czf "${BACKUP_DIR}/config_${DATE}.tar.gz" \
    /opt/dean/configs \
    /opt/dean/.env.production

# Cleanup old backups (keep 30 days)
find "${BACKUP_DIR}" -type f -mtime +30 -delete
EOF

# Schedule daily backups
echo "0 2 * * * /opt/dean/backup.sh" | sudo crontab -
```

## Troubleshooting

### Common Issues

1. **Authentication Failures**
```bash
# Check JWT secret configuration
docker exec dean-orchestrator env | grep JWT

# Verify token generation
docker exec dean-orchestrator dean-cli auth test-token

# Check logs
docker logs dean-orchestrator --tail 100 | grep -i auth
```

2. **SSL/TLS Issues**
```bash
# Test certificate
openssl s_client -connect your-domain.com:443 -servername your-domain.com

# Check certificate expiry
echo | openssl s_client -connect your-domain.com:443 2>/dev/null | \
    openssl x509 -noout -dates
```

3. **Service Communication**
```bash
# Test internal connectivity
docker exec dean-orchestrator curl -k https://evolution-api:8083/health

# Check service discovery
docker exec dean-orchestrator nslookup evolution-api
```

### Health Checks

```bash
# Comprehensive health check
./scripts/deploy/health_check.sh --verbose

# Individual service checks
curl -k https://localhost:8082/health
curl -k https://localhost:8081/health
curl -k https://localhost:8083/health
```

### Emergency Procedures

```bash
# Emergency shutdown
./scripts/deploy/emergency_shutdown.sh

# Rollback to previous version
./scripts/deploy/rollback.sh --version previous

# Reset authentication system
docker exec dean-orchestrator dean-cli security reset --confirm
```

## Maintenance

### Regular Tasks

- **Daily**: Check logs and alerts
- **Weekly**: Review security events
- **Monthly**: Update dependencies
- **Quarterly**: Rotate credentials
- **Annually**: Full security audit

### Update Procedure

```bash
# 1. Backup current state
./scripts/deploy/backup_all.sh

# 2. Pull latest changes
git pull origin main

# 3. Test in staging
./scripts/deploy/test_staging.sh

# 4. Deploy updates
./scripts/deploy/rolling_update.sh

# 5. Verify deployment
./scripts/deploy/post_update_check.sh
```

## Support

For deployment issues:
- Documentation: https://dean-docs.example.com
- Support Email: support@dean-system.example.com
- Emergency: Follow escalation procedure