#!/bin/bash
# Prepare DEAN deployment package for Windows

set -e

echo "📦 Preparing DEAN Deployment Package"
echo "===================================="

# Get the DEAN root directory
DEAN_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKSPACE_ROOT="$(cd "$DEAN_ROOT/.." && pwd)"

# Create deployment directory
DEPLOY_DIR="$DEAN_ROOT/deployment-package"
rm -rf "$DEPLOY_DIR"
mkdir -p "$DEPLOY_DIR"

echo -e "\n📁 Creating deployment structure..."

# Copy necessary files
echo "  ✓ Copying Docker configurations..."
cp -r "$DEAN_ROOT/docker" "$DEPLOY_DIR/"
cp "$DEAN_ROOT/docker-compose.prod.yml" "$DEPLOY_DIR/" 2>/dev/null || echo "  ⚠️  docker-compose.prod.yml not found locally"

# Copy service implementations
echo "  ✓ Copying service implementations..."
mkdir -p "$DEPLOY_DIR/services"
cp -r "$DEAN_ROOT/IndexAgent" "$DEPLOY_DIR/services/" 2>/dev/null || echo "  ⚠️  IndexAgent not found"
cp -r "$DEAN_ROOT/evolution-api" "$DEPLOY_DIR/services/" 2>/dev/null || echo "  ⚠️  evolution-api not found"

# Copy Airflow DAGs and plugins
echo "  ✓ Copying Airflow components..."
mkdir -p "$DEPLOY_DIR/airflow"
cp -r "$DEAN_ROOT/airflow/dags" "$DEPLOY_DIR/airflow/"
cp -r "$DEAN_ROOT/airflow/plugins" "$DEPLOY_DIR/airflow/"

# Copy web dashboard
echo "  ✓ Copying web dashboard..."
cp -r "$DEAN_ROOT/web" "$DEPLOY_DIR/"

# Copy monitoring configurations
echo "  ✓ Preparing monitoring templates..."
mkdir -p "$DEPLOY_DIR/monitoring/prometheus"
mkdir -p "$DEPLOY_DIR/monitoring/grafana/provisioning/dashboards"
mkdir -p "$DEPLOY_DIR/monitoring/grafana/provisioning/datasources"

# Create Prometheus config template
cat > "$DEPLOY_DIR/monitoring/prometheus/prometheus.yml" << 'EOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'dean-orchestration'
    static_configs:
      - targets: ['dean-orchestration:8082']
    metrics_path: '/metrics'
    
  - job_name: 'indexagent'
    static_configs:
      - targets: ['indexagent:8081']
    metrics_path: '/metrics'
    
  - job_name: 'evolution-api'
    static_configs:
      - targets: ['evolution-api:8090']
    metrics_path: '/metrics'
    
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
EOF

# Create Grafana datasource config
cat > "$DEPLOY_DIR/monitoring/grafana/provisioning/datasources/prometheus.yml" << 'EOF'
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: true
EOF

# Create deployment instructions
cat > "$DEPLOY_DIR/DEPLOYMENT_INSTRUCTIONS.md" << 'EOF'
# DEAN Deployment Instructions

## Prerequisites
- Docker and Docker Compose installed
- .env.production file configured with actual API keys
- At least 16GB RAM available
- Ports 8080-8083, 8090, 9090, 3000 available

## Deployment Steps

1. **Load Docker Images**
   ```powershell
   docker load -i images/dean-orchestration.tar.gz
   docker load -i images/dean-indexagent.tar.gz
   docker load -i images/dean-evolution-api.tar.gz
   docker load -i images/dean-airflow.tar.gz
   ```

2. **Verify Environment**
   - Ensure .env.production has actual CLAUDE_API_KEY and GITHUB_TOKEN
   - Check that all placeholders have been replaced with secure values

3. **Initialize Database**
   ```powershell
   docker-compose -f docker-compose.prod.yml up -d postgres
   # Wait for PostgreSQL to be ready
   Start-Sleep -Seconds 30
   ```

4. **Start Services**
   ```powershell
   docker-compose -f docker-compose.prod.yml up -d
   ```

5. **Verify Deployment**
   ```powershell
   # Check service health
   curl http://localhost:8082/health  # DEAN orchestration
   curl http://localhost:8081/health  # IndexAgent
   curl http://localhost:8090/health  # Evolution API
   
   # Access web interfaces
   # DEAN Dashboard: http://localhost:8083
   # Airflow: http://localhost:8080 (admin / password from .env)
   # Grafana: http://localhost:3000 (admin / password from .env)
   # Prometheus: http://localhost:9090
   ```

## Service URLs
- DEAN API: http://localhost:8082
- DEAN Dashboard: http://localhost:8083
- IndexAgent API: http://localhost:8081
- Evolution API: http://localhost:8090
- Airflow: http://localhost:8080
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000

## Troubleshooting
- Check logs: `docker-compose -f docker-compose.prod.yml logs <service-name>`
- Restart service: `docker-compose -f docker-compose.prod.yml restart <service-name>`
- Full restart: `docker-compose -f docker-compose.prod.yml down && docker-compose -f docker-compose.prod.yml up -d`
EOF

echo -e "\n📝 Creating deployment scripts..."

# Create Windows deployment script
cat > "$DEPLOY_DIR/deploy.ps1" << 'EOF'
# DEAN Windows Deployment Script

param(
    [string]$Action = "deploy"
)

$ErrorActionPreference = "Stop"

Write-Host "DEAN Deployment Script" -ForegroundColor Cyan
Write-Host "=====================" -ForegroundColor Cyan

# Check prerequisites
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error "Docker is not installed or not in PATH"
    exit 1
}

# Check for .env.production
if (-not (Test-Path ".env.production")) {
    Write-Error ".env.production file not found. Please ensure it exists with proper credentials."
    exit 1
}

# Check for required API keys in .env.production
$envContent = Get-Content ".env.production"
if ($envContent -match "YOUR_CLAUDE_API_KEY_HERE") {
    Write-Error "CLAUDE_API_KEY not set in .env.production"
    exit 1
}
if ($envContent -match "YOUR_GITHUB_TOKEN_HERE") {
    Write-Error "GITHUB_TOKEN not set in .env.production"
    exit 1
}

switch ($Action) {
    "deploy" {
        Write-Host "`nDeploying DEAN services..." -ForegroundColor Green
        
        # Load images if they exist
        if (Test-Path "images") {
            Write-Host "Loading Docker images..." -ForegroundColor Yellow
            Get-ChildItem "images/*.tar.gz" | ForEach-Object {
                Write-Host "  Loading $($_.Name)..."
                docker load -i $_.FullName
            }
        }
        
        # Start services
        Write-Host "`nStarting services..." -ForegroundColor Yellow
        docker-compose -f docker-compose.prod.yml up -d
        
        Write-Host "`n✅ Deployment complete!" -ForegroundColor Green
    }
    
    "stop" {
        Write-Host "Stopping DEAN services..." -ForegroundColor Yellow
        docker-compose -f docker-compose.prod.yml down
        Write-Host "✅ Services stopped" -ForegroundColor Green
    }
    
    "status" {
        Write-Host "DEAN Service Status:" -ForegroundColor Cyan
        docker-compose -f docker-compose.prod.yml ps
    }
    
    "logs" {
        docker-compose -f docker-compose.prod.yml logs -f
    }
    
    default {
        Write-Host "Usage: deploy.ps1 [-Action deploy|stop|status|logs]" -ForegroundColor Yellow
    }
}
EOF

echo -e "\n✅ Deployment package prepared at: $DEPLOY_DIR"
echo -e "\n📋 Next steps:"
echo "1. Build Docker images: ./scripts/build_images.sh"
echo "2. Save images for transfer:"
echo "   mkdir -p $DEPLOY_DIR/images"
echo "   docker save dean/orchestration:production | gzip > $DEPLOY_DIR/images/dean-orchestration.tar.gz"
echo "   docker save dean/indexagent:production | gzip > $DEPLOY_DIR/images/dean-indexagent.tar.gz"
echo "   docker save dean/evolution-api:production | gzip > $DEPLOY_DIR/images/dean-evolution-api.tar.gz"
echo "   docker save dean/airflow:production | gzip > $DEPLOY_DIR/images/dean-airflow.tar.gz"
echo "3. Transfer $DEPLOY_DIR to Windows deployment PC"
echo "4. Run deploy.ps1 on Windows PC"