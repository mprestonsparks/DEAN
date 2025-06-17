#!/bin/bash

# DEAN Orchestration System - One-Command Installation Script
# This script checks requirements and sets up the complete DEAN system

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DEAN_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MIN_DOCKER_VERSION="20.10"
MIN_PYTHON_VERSION="3.10"
MIN_RAM_GB=16
MIN_CPU_CORES=4

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║            DEAN Orchestration System Installer               ║"
echo "║                                                              ║"
echo "║         Distributed Evolutionary Agent Network               ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""

# Function to compare versions
version_ge() {
    test "$(printf '%s\n' "$@" | sort -V | head -n 1)" = "$2"
}

# Function to check command exists
check_command() {
    if command -v "$1" &> /dev/null; then
        return 0
    else
        return 1
    fi
}

# Function to get system info
get_system_info() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="Linux"
        DISTRO=$(lsb_release -si 2>/dev/null || echo "Unknown")
        CPU_CORES=$(nproc)
        RAM_GB=$(free -g | awk '/^Mem:/{print $2}')
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macOS"
        DISTRO="macOS"
        CPU_CORES=$(sysctl -n hw.ncpu)
        RAM_GB=$(($(sysctl -n hw.memsize) / 1024 / 1024 / 1024))
    else
        OS="Unknown"
        DISTRO="Unknown"
        CPU_CORES=0
        RAM_GB=0
    fi
}

# Step 1: Check system requirements
echo -e "${YELLOW}Step 1: Checking System Requirements${NC}"
echo "======================================"

get_system_info

echo "System Information:"
echo "  OS: $OS ($DISTRO)"
echo "  CPU Cores: $CPU_CORES"
echo "  RAM: ${RAM_GB}GB"
echo ""

# Check hardware requirements
HARDWARE_OK=true

if [ $CPU_CORES -lt $MIN_CPU_CORES ]; then
    echo -e "${RED}✗ Insufficient CPU cores: $CPU_CORES (minimum: $MIN_CPU_CORES)${NC}"
    HARDWARE_OK=false
else
    echo -e "${GREEN}✓ CPU cores: $CPU_CORES${NC}"
fi

if [ $RAM_GB -lt $MIN_RAM_GB ]; then
    echo -e "${RED}✗ Insufficient RAM: ${RAM_GB}GB (minimum: ${MIN_RAM_GB}GB)${NC}"
    HARDWARE_OK=false
else
    echo -e "${GREEN}✓ RAM: ${RAM_GB}GB${NC}"
fi

if [ "$HARDWARE_OK" = false ]; then
    echo ""
    echo -e "${YELLOW}⚠️  Warning: Your system does not meet minimum hardware requirements.${NC}"
    echo "DEAN may run slowly or encounter issues."
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo ""

# Step 2: Check software dependencies
echo -e "${YELLOW}Step 2: Checking Software Dependencies${NC}"
echo "======================================"

DEPS_OK=true

# Check Docker
if check_command docker; then
    DOCKER_VERSION=$(docker --version | cut -d' ' -f3 | cut -d',' -f1)
    if version_ge "$MIN_DOCKER_VERSION" "$DOCKER_VERSION"; then
        echo -e "${GREEN}✓ Docker $DOCKER_VERSION${NC}"
    else
        echo -e "${RED}✗ Docker $DOCKER_VERSION (minimum: $MIN_DOCKER_VERSION)${NC}"
        DEPS_OK=false
    fi
else
    echo -e "${RED}✗ Docker not installed${NC}"
    DEPS_OK=false
fi

# Check Docker Compose
if check_command docker-compose; then
    DC_VERSION=$(docker-compose --version | cut -d' ' -f4 | cut -d',' -f1)
    echo -e "${GREEN}✓ Docker Compose $DC_VERSION${NC}"
else
    echo -e "${RED}✗ Docker Compose not installed${NC}"
    DEPS_OK=false
fi

# Check Python
if check_command python3; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)
    
    if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 10 ]; then
        echo -e "${GREEN}✓ Python $PYTHON_VERSION${NC}"
    else
        echo -e "${RED}✗ Python $PYTHON_VERSION (minimum: $MIN_PYTHON_VERSION)${NC}"
        DEPS_OK=false
    fi
else
    echo -e "${RED}✗ Python 3 not installed${NC}"
    DEPS_OK=false
fi

# Check Git
if check_command git; then
    GIT_VERSION=$(git --version | cut -d' ' -f3)
    echo -e "${GREEN}✓ Git $GIT_VERSION${NC}"
else
    echo -e "${YELLOW}⚠ Git not installed (optional)${NC}"
fi

if [ "$DEPS_OK" = false ]; then
    echo ""
    echo -e "${RED}Missing required dependencies!${NC}"
    echo ""
    echo "Please install missing dependencies:"
    echo "  Docker: https://docs.docker.com/get-docker/"
    echo "  Docker Compose: https://docs.docker.com/compose/install/"
    echo "  Python 3.10+: https://www.python.org/downloads/"
    exit 1
fi

echo ""

# Step 3: Check port availability
echo -e "${YELLOW}Step 3: Checking Port Availability${NC}"
echo "=================================="

PORTS=(8080 8081 8082 8083 5432 6379)
PORT_NAMES=("Airflow" "IndexAgent" "Orchestrator" "Evolution" "PostgreSQL" "Redis")
PORTS_OK=true

for i in "${!PORTS[@]}"; do
    PORT=${PORTS[$i]}
    NAME=${PORT_NAMES[$i]}
    
    if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${RED}✗ Port $PORT is in use ($NAME)${NC}"
        PORTS_OK=false
    else
        echo -e "${GREEN}✓ Port $PORT available ($NAME)${NC}"
    fi
done

if [ "$PORTS_OK" = false ]; then
    echo ""
    echo -e "${RED}Some required ports are in use!${NC}"
    echo "Please stop conflicting services or change DEAN port configuration."
    exit 1
fi

echo ""

# Step 4: Create directory structure
echo -e "${YELLOW}Step 4: Setting Up Directory Structure${NC}"
echo "====================================="

DIRECTORIES=("logs" "data" "certs" "backups" "releases")

for DIR in "${DIRECTORIES[@]}"; do
    if [ ! -d "$DEAN_ROOT/$DIR" ]; then
        mkdir -p "$DEAN_ROOT/$DIR"
        echo -e "${GREEN}✓ Created $DIR/${NC}"
    else
        echo -e "${BLUE}✓ $DIR/ already exists${NC}"
    fi
done

echo ""

# Step 5: Initialize configuration
echo -e "${YELLOW}Step 5: Initializing Configuration${NC}"
echo "================================="

# Create .env file if it doesn't exist
if [ ! -f "$DEAN_ROOT/.env" ]; then
    echo "Creating environment configuration..."
    
    # Generate secure passwords
    DB_PASSWORD=$(openssl rand -base64 32)
    REDIS_PASSWORD=$(openssl rand -base64 24)
    JWT_SECRET=$(openssl rand -base64 64)
    AIRFLOW_PASSWORD=$(openssl rand -base64 24)
    
    cat > "$DEAN_ROOT/.env" << EOF
# DEAN Environment Configuration
# Generated on $(date)

# Environment
DEAN_ENV=production

# Database Configuration
POSTGRES_HOST=postgres-dev
POSTGRES_PORT=5432
POSTGRES_USER=dean_prod
POSTGRES_PASSWORD=$DB_PASSWORD
POSTGRES_DB=dean_production

# Redis Configuration
REDIS_HOST=redis-dev
REDIS_PORT=6379
REDIS_PASSWORD=$REDIS_PASSWORD

# Authentication
JWT_SECRET_KEY=$JWT_SECRET
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Service URLs
INDEXAGENT_API_URL=http://indexagent-stub:8081
AIRFLOW_API_URL=http://airflow-stub:8080
EVOLUTION_API_URL=http://evolution-stub:8083

# Airflow Credentials
AIRFLOW_USERNAME=airflow
AIRFLOW_PASSWORD=$AIRFLOW_PASSWORD

# Security Settings
ENFORCE_HTTPS=false
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8082
SESSION_COOKIE_SECURE=false
SESSION_COOKIE_HTTPONLY=true

# Logging
LOG_LEVEL=INFO
LOG_FILE=/logs/orchestration.log
EOF
    
    echo -e "${GREEN}✓ Created .env configuration${NC}"
    echo -e "${YELLOW}⚠ Generated secure passwords - saved in .env${NC}"
else
    echo -e "${BLUE}✓ .env configuration already exists${NC}"
fi

# Create self-signed certificates for development
if [ ! -f "$DEAN_ROOT/certs/server.crt" ]; then
    echo "Creating self-signed SSL certificates..."
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout "$DEAN_ROOT/certs/server.key" \
        -out "$DEAN_ROOT/certs/server.crt" \
        -subj "/C=US/ST=State/L=City/O=DEAN/CN=localhost" \
        2>/dev/null
    echo -e "${GREEN}✓ Created SSL certificates${NC}"
else
    echo -e "${BLUE}✓ SSL certificates already exist${NC}"
fi

echo ""

# Step 6: Build Docker images
echo -e "${YELLOW}Step 6: Building Docker Images${NC}"
echo "============================="

cd "$DEAN_ROOT"

echo "Building service images..."
if docker-compose -f service_stubs/docker-compose.stubs.yml build; then
    echo -e "${GREEN}✓ Docker images built successfully${NC}"
else
    echo -e "${RED}✗ Failed to build Docker images${NC}"
    exit 1
fi

echo ""

# Step 7: Initialize services
echo -e "${YELLOW}Step 7: Initializing Services${NC}"
echo "============================"

echo "Starting infrastructure services..."
docker-compose -f service_stubs/docker-compose.stubs.yml up -d postgres-dev redis-dev

echo "Waiting for database to be ready..."
sleep 5

# Initialize database
echo "Initializing database..."
docker exec postgres-dev psql -U dean -c "CREATE DATABASE IF NOT EXISTS dean_production;" 2>/dev/null || true

echo -e "${GREEN}✓ Services initialized${NC}"
echo ""

# Step 8: Create Python virtual environment (optional)
echo -e "${YELLOW}Step 8: Python Environment Setup${NC}"
echo "==============================="

if [ ! -d "$DEAN_ROOT/venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv "$DEAN_ROOT/venv"
    source "$DEAN_ROOT/venv/bin/activate"
    pip install --upgrade pip
    pip install -r "$DEAN_ROOT/requirements.txt"
    echo -e "${GREEN}✓ Python environment created${NC}"
else
    echo -e "${BLUE}✓ Python environment already exists${NC}"
fi

echo ""

# Step 9: Final setup
echo -e "${YELLOW}Step 9: Final Setup${NC}"
echo "=================="

# Create systemd service file (Linux only)
if [[ "$OS" == "Linux" ]]; then
    echo "Creating systemd service file..."
    sudo tee /etc/systemd/system/dean.service > /dev/null << EOF
[Unit]
Description=DEAN Orchestration System
After=docker.service
Requires=docker.service

[Service]
Type=simple
ExecStart=$DEAN_ROOT/scripts/start_services.sh
ExecStop=$DEAN_ROOT/scripts/stop_services.sh
Restart=always
User=$USER
WorkingDirectory=$DEAN_ROOT

[Install]
WantedBy=multi-user.target
EOF
    
    echo -e "${GREEN}✓ Systemd service created${NC}"
    echo "  Enable auto-start: sudo systemctl enable dean"
    echo "  Start service: sudo systemctl start dean"
fi

# Create start script
cat > "$DEAN_ROOT/scripts/start_services.sh" << 'EOF'
#!/bin/bash
cd "$(dirname "$0")/.."
docker-compose -f service_stubs/docker-compose.stubs.yml up -d
./scripts/dev_environment.sh
EOF
chmod +x "$DEAN_ROOT/scripts/start_services.sh"

# Create stop script
cat > "$DEAN_ROOT/scripts/stop_services.sh" << 'EOF'
#!/bin/bash
cd "$(dirname "$0")/.."
./scripts/stop_dev_environment.sh
docker-compose -f service_stubs/docker-compose.stubs.yml down
EOF
chmod +x "$DEAN_ROOT/scripts/stop_services.sh"

echo ""

# Installation complete
echo -e "${GREEN}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║            Installation Complete! 🎉                         ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""
echo -e "${BLUE}Next Steps:${NC}"
echo ""
echo "1. Start DEAN services:"
echo -e "   ${YELLOW}./scripts/dev_environment.sh${NC}"
echo ""
echo "2. Access the dashboard:"
echo -e "   ${YELLOW}http://localhost:8082${NC}"
echo ""
echo "3. Login with default credentials:"
echo "   Username: admin"
echo "   Password: admin123"
echo ""
echo -e "${RED}⚠️  IMPORTANT: Change default passwords before production use!${NC}"
echo ""
echo "For help, see:"
echo "  - Quick Start: docs/QUICK_START.md"
echo "  - Full Documentation: docs/README.md"
echo ""
echo -e "${GREEN}Happy evolving! 🧬${NC}"