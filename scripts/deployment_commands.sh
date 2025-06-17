#!/bin/bash

# DEAN Deployment Commands Reference Script
# This script provides all commands needed for production deployment
# Run sections individually as needed

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

# Configuration
DEAN_ROOT="/opt/dean"
BACKUP_DIR="/backups/dean"
LOG_DIR="/var/log/dean"

echo -e "${BLUE}DEAN Deployment Commands Reference${NC}"
echo "=================================="
echo ""
echo "This script contains all commands for deploying DEAN to production."
echo "Run each section as needed. Some commands require root privileges."
echo ""

# Function to prompt for continuation
prompt_continue() {
    echo ""
    read -p "Press Enter to view next section, or Ctrl+C to exit..."
    clear
}

# Section 1: System Preparation
echo -e "${BLUE}1. SYSTEM PREPARATION${NC}"
echo "====================="
echo ""
echo "# Update system packages"
echo -e "${YELLOW}sudo apt update && sudo apt upgrade -y${NC}"
echo ""
echo "# Install required packages"
echo -e "${YELLOW}sudo apt install -y \\
    apt-transport-https \\
    ca-certificates \\
    curl \\
    gnupg \\
    lsb-release \\
    git \\
    make \\
    python3-pip \\
    python3-venv \\
    openssl \\
    ufw \\
    fail2ban${NC}"
echo ""
echo "# Create dean user"
echo -e "${YELLOW}sudo useradd -m -s /bin/bash dean
sudo usermod -aG docker dean${NC}"
echo ""
echo "# Create directory structure"
echo -e "${YELLOW}sudo mkdir -p $DEAN_ROOT
sudo mkdir -p $BACKUP_DIR
sudo mkdir -p $LOG_DIR
sudo chown -R dean:dean $DEAN_ROOT $LOG_DIR${NC}"

prompt_continue

# Section 2: Docker Installation
echo -e "${BLUE}2. DOCKER INSTALLATION${NC}"
echo "======================"
echo ""
echo "# Add Docker GPG key"
echo -e "${YELLOW}curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg${NC}"
echo ""
echo "# Add Docker repository"
echo -e "${YELLOW}echo \"deb [arch=\$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \$(lsb_release -cs) stable\" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null${NC}"
echo ""
echo "# Install Docker"
echo -e "${YELLOW}sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin${NC}"
echo ""
echo "# Start Docker"
echo -e "${YELLOW}sudo systemctl start docker
sudo systemctl enable docker${NC}"
echo ""
echo "# Verify Docker installation"
echo -e "${YELLOW}docker --version
docker compose version${NC}"

prompt_continue

# Section 3: NVIDIA GPU Setup (for RTX 3080)
echo -e "${BLUE}3. NVIDIA GPU SETUP (Optional)${NC}"
echo "=============================="
echo ""
echo "# Add NVIDIA GPG key"
echo -e "${YELLOW}distribution=\$(. /etc/os-release;echo \$ID\$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/\$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list${NC}"
echo ""
echo "# Install nvidia-container-runtime"
echo -e "${YELLOW}sudo apt update
sudo apt install -y nvidia-container-toolkit
sudo systemctl restart docker${NC}"
echo ""
echo "# Verify GPU support"
echo -e "${YELLOW}docker run --rm --gpus all nvidia/cuda:11.0-base nvidia-smi${NC}"

prompt_continue

# Section 4: Repository Setup
echo -e "${BLUE}4. REPOSITORY SETUP${NC}"
echo "==================="
echo ""
echo "# Clone repository (as dean user)"
echo -e "${YELLOW}sudo -u dean git clone https://github.com/your-org/dean.git $DEAN_ROOT
cd $DEAN_ROOT${NC}"
echo ""
echo "# Or extract from release package"
echo -e "${YELLOW}sudo -u dean tar -xzf dean-orchestration-v1.0.0.tar.gz -C $DEAN_ROOT --strip-components=1${NC}"
echo ""
echo "# Set permissions"
echo -e "${YELLOW}sudo chown -R dean:dean $DEAN_ROOT
sudo chmod 700 $DEAN_ROOT
sudo chmod 600 $DEAN_ROOT/.env${NC}"

prompt_continue

# Section 5: Configuration
echo -e "${BLUE}5. CONFIGURATION${NC}"
echo "================"
echo ""
echo "# Copy and edit environment configuration"
echo -e "${YELLOW}cd $DEAN_ROOT
sudo -u dean cp .env.production.template .env
sudo -u dean vim .env${NC}"
echo ""
echo "# Key configurations to update:"
echo "  - POSTGRES_PASSWORD"
echo "  - REDIS_PASSWORD"
echo "  - JWT_SECRET_KEY"
echo "  - ALLOWED_ORIGINS"
echo "  - Domain/IP settings"
echo ""
echo "# Generate secure passwords"
echo -e "${YELLOW}openssl rand -base64 32  # For database password
openssl rand -base64 64  # For JWT secret${NC}"
echo ""
echo "# Hardware optimization"
echo -e "${YELLOW}sudo ./scripts/optimize_for_hardware.sh${NC}"

prompt_continue

# Section 6: SSL/TLS Setup
echo -e "${BLUE}6. SSL/TLS SETUP${NC}"
echo "================"
echo ""
echo "# Option A: Let's Encrypt (recommended)"
echo -e "${YELLOW}sudo apt install -y certbot
sudo certbot certonly --standalone -d your-domain.com${NC}"
echo ""
echo "# Option B: Self-signed certificate (development)"
echo -e "${YELLOW}openssl req -x509 -nodes -days 365 -newkey rsa:2048 \\
    -keyout $DEAN_ROOT/certs/server.key \\
    -out $DEAN_ROOT/certs/server.crt \\
    -subj \"/C=US/ST=State/L=City/O=Company/CN=your-domain.com\"${NC}"
echo ""
echo "# Set certificate permissions"
echo -e "${YELLOW}sudo chown dean:dean $DEAN_ROOT/certs/*
sudo chmod 600 $DEAN_ROOT/certs/*${NC}"

prompt_continue

# Section 7: Firewall Configuration
echo -e "${BLUE}7. FIREWALL CONFIGURATION${NC}"
echo "========================"
echo ""
echo "# Configure UFW firewall"
echo -e "${YELLOW}sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw --force enable${NC}"
echo ""
echo "# Verify firewall status"
echo -e "${YELLOW}sudo ufw status verbose${NC}"

prompt_continue

# Section 8: Service Startup
echo -e "${BLUE}8. SERVICE STARTUP${NC}"
echo "=================="
echo ""
echo "# Build Docker images"
echo -e "${YELLOW}cd $DEAN_ROOT
sudo -u dean docker compose -f docker-compose.prod.yml build${NC}"
echo ""
echo "# Start infrastructure services first"
echo -e "${YELLOW}sudo -u dean docker compose -f docker-compose.prod.yml up -d postgres-prod redis-prod${NC}"
echo ""
echo "# Wait for database to be ready"
echo -e "${YELLOW}sleep 10${NC}"
echo ""
echo "# Run database migrations"
echo -e "${YELLOW}sudo -u dean docker compose -f docker-compose.prod.yml run --rm orchestrator python -m alembic upgrade head${NC}"
echo ""
echo "# Start all services"
echo -e "${YELLOW}sudo -u dean docker compose -f docker-compose.prod.yml up -d${NC}"
echo ""
echo "# With hardware optimization"
echo -e "${YELLOW}sudo -u dean docker compose -f docker-compose.prod.yml -f docker-compose.hardware.yml up -d${NC}"

prompt_continue

# Section 9: Verification Commands
echo -e "${BLUE}9. VERIFICATION COMMANDS${NC}"
echo "======================="
echo ""
echo "# Check service status"
echo -e "${YELLOW}docker compose -f docker-compose.prod.yml ps${NC}"
echo ""
echo "# View logs"
echo -e "${YELLOW}docker compose -f docker-compose.prod.yml logs -f --tail=50${NC}"
echo ""
echo "# Test health endpoints"
echo -e "${YELLOW}curl -k https://localhost/health
curl -k https://localhost:8082/health
curl -k https://localhost:8083/health${NC}"
echo ""
echo "# Run validation script"
echo -e "${YELLOW}cd $DEAN_ROOT
./scripts/final_validation.sh --production${NC}"
echo ""
echo "# Check resource usage"
echo -e "${YELLOW}docker stats${NC}"

prompt_continue

# Section 10: Security Hardening
echo -e "${BLUE}10. SECURITY HARDENING${NC}"
echo "======================"
echo ""
echo "# Run hardening script"
echo -e "${YELLOW}cd $DEAN_ROOT
sudo ./scripts/production_hardening.sh${NC}"
echo ""
echo "# Restart services after hardening"
echo -e "${YELLOW}docker compose -f docker-compose.prod.yml restart${NC}"
echo ""
echo "# Verify security settings"
echo -e "${YELLOW}./scripts/security_audit.py --production${NC}"

prompt_continue

# Section 11: Monitoring Setup
echo -e "${BLUE}11. MONITORING SETUP${NC}"
echo "===================="
echo ""
echo "# Start Prometheus"
echo -e "${YELLOW}docker run -d \\
    --name prometheus \\
    -p 9090:9090 \\
    -v $DEAN_ROOT/monitoring/prometheus.yml:/etc/prometheus/prometheus.yml \\
    prom/prometheus${NC}"
echo ""
echo "# Start Grafana"
echo -e "${YELLOW}docker run -d \\
    --name grafana \\
    -p 3000:3000 \\
    -e \"GF_SECURITY_ADMIN_PASSWORD=your-password\" \\
    grafana/grafana${NC}"
echo ""
echo "# Import dashboards"
echo "Access Grafana at http://localhost:3000"
echo "Import dashboards from $DEAN_ROOT/monitoring/dashboards/"

prompt_continue

# Section 12: Backup Configuration
echo -e "${BLUE}12. BACKUP CONFIGURATION${NC}"
echo "======================="
echo ""
echo "# Create backup script"
echo -e "${YELLOW}sudo cp $DEAN_ROOT/scripts/utilities/backup_restore.sh /usr/local/bin/dean-backup
sudo chmod +x /usr/local/bin/dean-backup${NC}"
echo ""
echo "# Add to crontab"
echo -e "${YELLOW}sudo crontab -e
# Add this line:
0 2 * * * /usr/local/bin/dean-backup backup${NC}"
echo ""
echo "# Test backup"
echo -e "${YELLOW}sudo /usr/local/bin/dean-backup backup${NC}"

prompt_continue

# Section 13: Systemd Service
echo -e "${BLUE}13. SYSTEMD SERVICE (Optional)${NC}"
echo "=============================="
echo ""
echo "# Create systemd service"
echo -e "${YELLOW}sudo tee /etc/systemd/system/dean.service > /dev/null << EOF
[Unit]
Description=DEAN Orchestration System
After=docker.service
Requires=docker.service

[Service]
Type=simple
User=dean
WorkingDirectory=$DEAN_ROOT
ExecStart=/usr/bin/docker compose -f docker-compose.prod.yml up
ExecStop=/usr/bin/docker compose -f docker-compose.prod.yml down
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF${NC}"
echo ""
echo "# Enable service"
echo -e "${YELLOW}sudo systemctl daemon-reload
sudo systemctl enable dean
sudo systemctl start dean${NC}"

prompt_continue

# Section 14: Post-Deployment
echo -e "${BLUE}14. POST-DEPLOYMENT${NC}"
echo "==================="
echo ""
echo "# Create admin user"
echo -e "${YELLOW}docker exec -it dean-orchestrator python scripts/create_admin.py${NC}"
echo ""
echo "# Access the system"
echo "Dashboard: https://your-domain.com"
echo "API Docs: https://your-domain.com/docs"
echo "Health Monitor: https://your-domain.com/health.html"
echo ""
echo "# Monitor logs"
echo -e "${YELLOW}tail -f $LOG_DIR/*.log${NC}"
echo ""
echo "# Performance tuning (if needed)"
echo -e "${YELLOW}sudo ./tune_performance.sh${NC}"

echo ""
echo -e "${GREEN}Deployment command reference complete!${NC}"
echo ""
echo "Important files:"
echo "  - Configuration: $DEAN_ROOT/.env"
echo "  - Logs: $LOG_DIR/"
echo "  - Backups: $BACKUP_DIR/"
echo "  - Certificates: $DEAN_ROOT/certs/"
echo ""
echo "For troubleshooting, refer to:"
echo "  - Operations Runbook: $DEAN_ROOT/docs/OPERATIONS_RUNBOOK.md"
echo "  - Security Guide: $DEAN_ROOT/docs/SECURITY_GUIDE.md"