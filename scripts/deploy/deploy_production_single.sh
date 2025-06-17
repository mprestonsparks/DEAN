#!/bin/bash
# Production deployment script for DEAN system on single machine
# Optimized for i7 CPU with RTX 3080 GPU

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Configuration
DEPLOYMENT_CONFIG="${PROJECT_ROOT}/configs/deployment/production_single_machine.yaml"
LOG_DIR="/var/log/dean"
DATA_DIR="/var/lib/dean"
CERT_DIR="/etc/dean/certs"
BACKUP_DIR="/backup/dean"

# Required environment variables
REQUIRED_ENV_VARS=(
    "JWT_SECRET_KEY"
    "POSTGRES_PASSWORD"
    "REDIS_PASSWORD"
    "DEAN_SERVICE_API_KEY"
)

# Log function
log() {
    echo -e "${2:-$BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

# Error function
error() {
    echo -e "${RED}[ERROR] $1${NC}" >&2
    exit 1
}

# Warning function
warn() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

# Success function
success() {
    echo -e "${GREEN}[SUCCESS] $1${NC}"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        error "This script must be run as root for production deployment"
    fi
}

# Check system resources
check_system_resources() {
    log "Checking system resources..."
    
    # Check CPU cores
    cpu_cores=$(nproc)
    if [[ $cpu_cores -lt 4 ]]; then
        error "Insufficient CPU cores. Found: $cpu_cores, Required: 4+"
    fi
    log "CPU cores: $cpu_cores" "$GREEN"
    
    # Check total memory
    total_memory_gb=$(free -g | awk '/^Mem:/{print $2}')
    if [[ $total_memory_gb -lt 16 ]]; then
        error "Insufficient memory. Found: ${total_memory_gb}GB, Required: 16GB+"
    fi
    log "Total memory: ${total_memory_gb}GB" "$GREEN"
    
    # Check GPU
    if command -v nvidia-smi &> /dev/null; then
        gpu_info=$(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader)
        log "GPU detected: $gpu_info" "$GREEN"
        
        # Check CUDA
        if command -v nvcc &> /dev/null; then
            cuda_version=$(nvcc --version | grep "release" | awk '{print $5}' | cut -d',' -f1)
            log "CUDA version: $cuda_version" "$GREEN"
        else
            warn "CUDA toolkit not found. GPU acceleration may not work properly."
        fi
    else
        error "No NVIDIA GPU detected. RTX 3080 or equivalent required."
    fi
    
    # Check disk space
    available_space_gb=$(df -BG "$PROJECT_ROOT" | awk 'NR==2 {print $4}' | sed 's/G//')
    if [[ $available_space_gb -lt 50 ]]; then
        warn "Low disk space: ${available_space_gb}GB available. Recommend 50GB+"
    else
        log "Available disk space: ${available_space_gb}GB" "$GREEN"
    fi
}

# Check required software
check_dependencies() {
    log "Checking required dependencies..."
    
    local deps=("docker" "docker-compose" "python3" "pip3" "git" "openssl" "jq")
    local missing=()
    
    for dep in "${deps[@]}"; do
        if ! command -v "$dep" &> /dev/null; then
            missing+=("$dep")
        fi
    done
    
    if [ ${#missing[@]} -ne 0 ]; then
        error "Missing dependencies: ${missing[*]}"
    fi
    
    # Check Docker daemon
    if ! docker info &> /dev/null; then
        error "Docker daemon is not running"
    fi
    
    # Check Python version
    python_version=$(python3 --version | awk '{print $2}')
    log "Python version: $python_version" "$GREEN"
    
    success "All dependencies satisfied"
}

# Check environment variables
check_environment() {
    log "Checking environment variables..."
    
    local missing=()
    for var in "${REQUIRED_ENV_VARS[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            missing+=("$var")
        fi
    done
    
    if [ ${#missing[@]} -ne 0 ]; then
        error "Missing required environment variables: ${missing[*]}"
    fi
    
    # Validate JWT secret length
    if [[ ${#JWT_SECRET_KEY} -lt 32 ]]; then
        error "JWT_SECRET_KEY must be at least 32 characters long"
    fi
    
    success "Environment variables validated"
}

# Create required directories
create_directories() {
    log "Creating required directories..."
    
    local dirs=(
        "$LOG_DIR"
        "$DATA_DIR"
        "$CERT_DIR"
        "$BACKUP_DIR"
        "$DATA_DIR/postgresql"
        "$DATA_DIR/redis"
        "$DATA_DIR/evolution"
    )
    
    for dir in "${dirs[@]}"; do
        mkdir -p "$dir"
        chmod 750 "$dir"
        log "Created: $dir"
    done
    
    success "Directories created"
}

# Generate SSL certificates
generate_ssl_certificates() {
    log "Generating SSL certificates..."
    
    if [[ -f "$CERT_DIR/cert.pem" ]] && [[ -f "$CERT_DIR/key.pem" ]]; then
        warn "SSL certificates already exist. Skipping generation."
        return
    fi
    
    # Generate self-signed certificate
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout "$CERT_DIR/key.pem" \
        -out "$CERT_DIR/cert.pem" \
        -subj "/C=US/ST=State/L=City/O=DEAN/CN=localhost" \
        2>/dev/null
    
    # Set permissions
    chmod 600 "$CERT_DIR/key.pem"
    chmod 644 "$CERT_DIR/cert.pem"
    
    success "SSL certificates generated"
}

# Configure firewall
configure_firewall() {
    log "Configuring firewall rules..."
    
    # Check if ufw is available
    if command -v ufw &> /dev/null; then
        # Allow SSH (preserve existing connection)
        ufw allow ssh
        
        # Allow DEAN services (localhost only by default)
        # These can be opened to specific IPs if needed
        ufw allow 8080/tcp comment "Airflow"
        ufw allow 8081/tcp comment "IndexAgent"
        ufw allow 8082/tcp comment "DEAN Orchestration"
        ufw allow 8083/tcp comment "Evolution API"
        
        # Enable firewall
        ufw --force enable
        
        log "Firewall configured with UFW"
    else
        warn "UFW not found. Please configure firewall manually."
    fi
}

# Optimize system settings
optimize_system() {
    log "Optimizing system settings..."
    
    # Increase file descriptor limits
    cat >> /etc/security/limits.conf <<EOF
* soft nofile 65536
* hard nofile 65536
* soft nproc 32768
* hard nproc 32768
EOF
    
    # Optimize kernel parameters
    cat > /etc/sysctl.d/99-dean.conf <<EOF
# Network optimizations
net.core.somaxconn = 1024
net.ipv4.tcp_max_syn_backlog = 2048
net.ipv4.tcp_syncookies = 1
net.ipv4.tcp_tw_reuse = 1
net.ipv4.tcp_fin_timeout = 30

# Memory optimizations
vm.swappiness = 10
vm.dirty_ratio = 15
vm.dirty_background_ratio = 5

# File system optimizations
fs.file-max = 2097152
EOF
    
    # Apply sysctl settings
    sysctl -p /etc/sysctl.d/99-dean.conf > /dev/null
    
    # Configure GPU settings if available
    if command -v nvidia-smi &> /dev/null; then
        # Set GPU to persistence mode
        nvidia-smi -pm 1
        
        # Set power limit (optional, adjust for RTX 3080)
        # nvidia-smi -pl 320
        
        log "GPU optimizations applied"
    fi
    
    success "System optimizations applied"
}

# Build Docker images
build_images() {
    log "Building Docker images for production..."
    
    cd "$PROJECT_ROOT"
    
    # Build with production optimizations
    DOCKER_BUILDKIT=1 docker-compose \
        -f docker-compose.yml \
        -f docker-compose.prod.yml \
        build \
        --no-cache \
        --parallel
    
    success "Docker images built"
}

# Deploy services
deploy_services() {
    log "Deploying DEAN services..."
    
    cd "$PROJECT_ROOT"
    
    # Create production environment file
    cat > .env.production <<EOF
# Environment
DEAN_ENV=production

# Service URLs
INDEXAGENT_API_URL=https://localhost:8081
AIRFLOW_API_URL=https://localhost:8080
EVOLUTION_API_URL=https://localhost:8083
DEAN_ORCHESTRATION_URL=https://localhost:8082

# Security
JWT_SECRET_KEY=${JWT_SECRET_KEY}
DEAN_SERVICE_API_KEY=${DEAN_SERVICE_API_KEY}

# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=dean_production
POSTGRES_USER=dean_prod
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=${REDIS_PASSWORD}

# SSL
SSL_CERT_PATH=${CERT_DIR}/cert.pem
SSL_KEY_PATH=${CERT_DIR}/key.pem

# Logging
LOG_LEVEL=INFO
LOG_DIR=${LOG_DIR}

# Resource limits (from config)
INDEXAGENT_MEMORY_LIMIT=7g
INDEXAGENT_CPU_LIMIT=2.1
AIRFLOW_MEMORY_LIMIT=5.6g
AIRFLOW_CPU_LIMIT=1.4
EVOLUTION_MEMORY_LIMIT=7g
EVOLUTION_CPU_LIMIT=1.75
EOF
    
    # Start services with production configuration
    docker-compose \
        --env-file .env.production \
        -f docker-compose.yml \
        -f docker-compose.prod.yml \
        up -d
    
    log "Waiting for services to start..."
    sleep 30
    
    success "Services deployed"
}

# Initialize databases
initialize_databases() {
    log "Initializing databases..."
    
    # Wait for PostgreSQL
    local retries=30
    while ! docker-compose exec -T postgresql pg_isready -U dean_prod &> /dev/null; do
        retries=$((retries - 1))
        if [[ $retries -eq 0 ]]; then
            error "PostgreSQL failed to start"
        fi
        sleep 2
    done
    
    # Create databases
    docker-compose exec -T postgresql psql -U dean_prod <<EOF
CREATE DATABASE IF NOT EXISTS dean_production;
CREATE DATABASE IF NOT EXISTS indexagent;
CREATE DATABASE IF NOT EXISTS airflow;
CREATE DATABASE IF NOT EXISTS agent_evolution;
EOF
    
    # Run migrations
    log "Running database migrations..."
    
    # IndexAgent migrations
    docker-compose exec -T indexagent python -m alembic upgrade head
    
    # Airflow initialization
    docker-compose exec -T airflow airflow db init
    
    success "Databases initialized"
}

# Configure monitoring
configure_monitoring() {
    log "Configuring monitoring..."
    
    # Create Prometheus configuration
    cat > "$PROJECT_ROOT/configs/prometheus/prometheus.yml" <<EOF
global:
  scrape_interval: 60s
  evaluation_interval: 60s

scrape_configs:
  - job_name: 'dean-orchestration'
    static_configs:
      - targets: ['localhost:8082']
    metrics_path: '/metrics'
    
  - job_name: 'indexagent'
    static_configs:
      - targets: ['localhost:8081']
    metrics_path: '/metrics'
    
  - job_name: 'evolution'
    static_configs:
      - targets: ['localhost:8083']
    metrics_path: '/metrics'
    
  - job_name: 'node'
    static_configs:
      - targets: ['localhost:9100']
EOF
    
    # Start node exporter for system metrics
    docker run -d \
        --name node-exporter \
        --restart unless-stopped \
        -p 9100:9100 \
        -v "/:/host:ro,rslave" \
        prom/node-exporter \
        --path.rootfs=/host
    
    success "Monitoring configured"
}

# Verify deployment
verify_deployment() {
    log "Verifying deployment..."
    
    local services=("orchestration:8082" "indexagent:8081" "airflow:8080" "evolution:8083")
    local failed=()
    
    for service in "${services[@]}"; do
        name="${service%%:*}"
        port="${service##*:}"
        
        if curl -k -s -f "https://localhost:$port/health" > /dev/null; then
            log "Service $name is healthy" "$GREEN"
        else
            failed+=("$name")
            warn "Service $name failed health check"
        fi
    done
    
    if [ ${#failed[@]} -ne 0 ]; then
        error "Deployment verification failed for: ${failed[*]}"
    fi
    
    success "All services are healthy"
}

# Create systemd service
create_systemd_service() {
    log "Creating systemd service..."
    
    cat > /etc/systemd/system/dean.service <<EOF
[Unit]
Description=DEAN Orchestration System
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$PROJECT_ROOT
ExecStart=/usr/local/bin/docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
ExecStop=/usr/local/bin/docker-compose -f docker-compose.yml -f docker-compose.prod.yml down
ExecReload=/usr/local/bin/docker-compose -f docker-compose.yml -f docker-compose.prod.yml restart
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    systemctl enable dean.service
    
    success "Systemd service created"
}

# Setup backup cron
setup_backup() {
    log "Setting up automated backups..."
    
    # Create backup script
    cat > /usr/local/bin/dean-backup.sh <<'EOF'
#!/bin/bash
set -euo pipefail

BACKUP_DIR="/backup/dean"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_PATH="$BACKUP_DIR/backup_$TIMESTAMP"

# Create backup directory
mkdir -p "$BACKUP_PATH"

# Backup PostgreSQL
docker-compose exec -T postgresql pg_dumpall -U dean_prod > "$BACKUP_PATH/postgresql.sql"

# Backup Redis
docker-compose exec -T redis redis-cli --rdb "$BACKUP_PATH/redis.rdb"

# Backup configurations
cp -r /etc/dean "$BACKUP_PATH/configs"

# Compress backup
tar -czf "$BACKUP_PATH.tar.gz" -C "$BACKUP_DIR" "backup_$TIMESTAMP"
rm -rf "$BACKUP_PATH"

# Keep only last 7 days of backups
find "$BACKUP_DIR" -name "backup_*.tar.gz" -mtime +7 -delete

echo "Backup completed: $BACKUP_PATH.tar.gz"
EOF
    
    chmod +x /usr/local/bin/dean-backup.sh
    
    # Add to crontab
    (crontab -l 2>/dev/null; echo "0 2 * * * /usr/local/bin/dean-backup.sh >> $LOG_DIR/backup.log 2>&1") | crontab -
    
    success "Backup automation configured"
}

# Main deployment function
main() {
    log "Starting DEAN production deployment..." "$GREEN"
    
    # Pre-deployment checks
    check_root
    check_system_resources
    check_dependencies
    check_environment
    
    # Setup
    create_directories
    generate_ssl_certificates
    configure_firewall
    optimize_system
    
    # Build and deploy
    build_images
    deploy_services
    initialize_databases
    
    # Post-deployment
    configure_monitoring
    verify_deployment
    create_systemd_service
    setup_backup
    
    # Summary
    echo
    success "DEAN system deployed successfully!"
    echo
    log "Service URLs:"
    log "  Orchestration API: https://localhost:8082" "$BLUE"
    log "  Web Dashboard: https://localhost:8082/" "$BLUE"
    log "  Airflow UI: https://localhost:8080" "$BLUE"
    log "  IndexAgent API: https://localhost:8081" "$BLUE"
    log "  Evolution API: https://localhost:8083" "$BLUE"
    echo
    log "Default credentials:"
    log "  Admin: admin/admin123" "$YELLOW"
    log "  User: user/user123" "$YELLOW"
    log "  Viewer: viewer/viewer123" "$YELLOW"
    echo
    warn "IMPORTANT: Change default passwords immediately!"
    echo
    log "Logs: $LOG_DIR"
    log "Data: $DATA_DIR"
    log "Backups: $BACKUP_DIR"
    echo
    log "To check service status: systemctl status dean"
    log "To view logs: journalctl -u dean -f"
}

# Run main function
main "$@"