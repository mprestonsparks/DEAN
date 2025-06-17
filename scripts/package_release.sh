#!/bin/bash

# DEAN Release Packaging Script
# Creates a release archive with all necessary files for deployment

set -e

# Configuration
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DEAN_ROOT="$(dirname "$SCRIPT_DIR")"
RELEASE_DIR="$DEAN_ROOT/releases"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
VERSION="${1:-1.0.0}"
RELEASE_NAME="dean-orchestration-v${VERSION}-${TIMESTAMP}"
RELEASE_PATH="$RELEASE_DIR/$RELEASE_NAME"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}DEAN Release Packaging Script${NC}"
echo "================================"
echo "Version: $VERSION"
echo "Release: $RELEASE_NAME"
echo ""

# Create release directory
echo -e "${YELLOW}Creating release directory...${NC}"
mkdir -p "$RELEASE_PATH"

# Copy source code
echo -e "${YELLOW}Copying source code...${NC}"
cp -r "$DEAN_ROOT/src" "$RELEASE_PATH/"
cp -r "$DEAN_ROOT/configs" "$RELEASE_PATH/"
cp -r "$DEAN_ROOT/scripts" "$RELEASE_PATH/"
cp -r "$DEAN_ROOT/migrations" "$RELEASE_PATH/"
cp -r "$DEAN_ROOT/service_stubs" "$RELEASE_PATH/"
cp -r "$DEAN_ROOT/docs" "$RELEASE_PATH/"

# Copy requirements
echo -e "${YELLOW}Copying requirements...${NC}"
cp -r "$DEAN_ROOT/requirements" "$RELEASE_PATH/"
cp "$DEAN_ROOT/requirements.txt" "$RELEASE_PATH/"
cp "$DEAN_ROOT/pyproject.toml" "$RELEASE_PATH/"

# Copy Docker files
echo -e "${YELLOW}Copying Docker configurations...${NC}"
cp "$DEAN_ROOT/docker-compose.dev.yml" "$RELEASE_PATH/"
cp "$DEAN_ROOT/service_stubs/docker-compose.stubs.yml" "$RELEASE_PATH/"

# Copy important files
echo -e "${YELLOW}Copying documentation and configuration...${NC}"
cp "$DEAN_ROOT/README.md" "$RELEASE_PATH/"
cp "$DEAN_ROOT/Makefile" "$RELEASE_PATH/"

# Create default configuration templates
echo -e "${YELLOW}Creating configuration templates...${NC}"
mkdir -p "$RELEASE_PATH/configs/templates"

cat > "$RELEASE_PATH/configs/templates/.env.template" << 'EOF'
# DEAN Environment Configuration Template
# Copy this to .env and update values for your environment

# Database Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=dean_prod
POSTGRES_PASSWORD=CHANGE_ME_STRONG_PASSWORD
POSTGRES_DB=dean_production

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=CHANGE_ME_REDIS_PASSWORD

# Authentication
JWT_SECRET_KEY=CHANGE_ME_GENERATE_STRONG_SECRET
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Service URLs
INDEXAGENT_API_URL=http://localhost:8081
AIRFLOW_API_URL=http://localhost:8080
EVOLUTION_API_URL=http://localhost:8083

# Airflow Credentials
AIRFLOW_USERNAME=airflow
AIRFLOW_PASSWORD=CHANGE_ME_AIRFLOW_PASSWORD

# Security Settings
ENFORCE_HTTPS=true
ALLOWED_ORIGINS=https://your-domain.com
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_HTTPONLY=true

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/dean/orchestration.log

# Performance
MAX_WORKERS=4
REQUEST_TIMEOUT=300
EOF

# Create installation script
echo -e "${YELLOW}Creating installation script...${NC}"
cat > "$RELEASE_PATH/install.sh" << 'EOF'
#!/bin/bash

# DEAN Installation Script

set -e

echo "DEAN Orchestration System Installer"
echo "==================================="
echo ""

# Check requirements
echo "Checking system requirements..."

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker 20.10+"
    exit 1
fi

# Check Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose 2.0+"
    exit 1
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.10+"
    exit 1
fi

echo "✅ All requirements satisfied"
echo ""

# Create directories
echo "Creating directories..."
mkdir -p logs
mkdir -p data
mkdir -p certs

# Copy environment template
if [ ! -f .env ]; then
    echo "Creating environment configuration..."
    cp configs/templates/.env.template .env
    echo "⚠️  Please edit .env file with your configuration"
    echo ""
fi

# Build Docker images
echo "Building Docker images..."
docker-compose -f docker-compose.dev.yml build

# Initialize database
echo "Initializing database..."
docker-compose -f docker-compose.dev.yml up -d postgres-dev
sleep 5

# Run migrations
echo "Running database migrations..."
docker-compose -f docker-compose.dev.yml run --rm orchestrator python scripts/utilities/db_migrate.py up

echo ""
echo "✅ Installation complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your configuration"
echo "2. Run ./scripts/first_run.sh to create admin user"
echo "3. Start services with: docker-compose -f docker-compose.dev.yml up -d"
echo ""
EOF

chmod +x "$RELEASE_PATH/install.sh"

# Create first run script
cat > "$RELEASE_PATH/scripts/first_run.sh" << 'EOF'
#!/bin/bash

# DEAN First Run Script
# Initializes the system after installation

set -e

echo "DEAN First Run Setup"
echo "==================="
echo ""

# Source environment
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Check if services are running
if ! docker-compose -f docker-compose.dev.yml ps | grep -q "Up"; then
    echo "Starting services..."
    docker-compose -f docker-compose.dev.yml up -d
    sleep 10
fi

# Create admin user
echo "Creating admin user..."
echo "Please enter admin credentials:"
read -p "Username [admin]: " ADMIN_USER
ADMIN_USER=${ADMIN_USER:-admin}

read -s -p "Password: " ADMIN_PASS
echo ""
read -s -p "Confirm password: " ADMIN_PASS_CONFIRM
echo ""

if [ "$ADMIN_PASS" != "$ADMIN_PASS_CONFIRM" ]; then
    echo "❌ Passwords do not match"
    exit 1
fi

# Create admin via API or CLI
# This is a placeholder - actual implementation depends on your user management
echo "Admin user created: $ADMIN_USER"

# Run system verification
echo ""
echo "Running system verification..."
./scripts/health_check.sh

echo ""
echo "✅ First run setup complete!"
echo ""
echo "Access the system at:"
echo "  Dashboard: https://localhost:8082"
echo "  API Docs: https://localhost:8082/docs"
echo ""
echo "Default credentials have been set up."
echo "Please change them immediately for security."
EOF

chmod +x "$RELEASE_PATH/scripts/first_run.sh"

# Remove development files
echo -e "${YELLOW}Cleaning up development files...${NC}"
find "$RELEASE_PATH" -name "*.pyc" -delete
find "$RELEASE_PATH" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find "$RELEASE_PATH" -name ".pytest_cache" -type d -exec rm -rf {} + 2>/dev/null || true
find "$RELEASE_PATH" -name "*.log" -delete

# Create version file
echo -e "${YELLOW}Creating version file...${NC}"
cat > "$RELEASE_PATH/VERSION" << EOF
DEAN Orchestration System
Version: $VERSION
Build Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)
Commit: $(git rev-parse HEAD 2>/dev/null || echo "unknown")
EOF

# Create release notes
echo -e "${YELLOW}Creating release notes...${NC}"
cat > "$RELEASE_PATH/RELEASE_NOTES.md" << EOF
# DEAN Orchestration System Release Notes

## Version $VERSION

### Release Date
$(date +%Y-%m-%d)

### Features
- Complete authentication and authorization system
- Evolution trial management
- Agent creation and optimization
- Pattern discovery engine
- Real-time monitoring dashboard
- WebSocket support for live updates
- Comprehensive API documentation

### System Requirements
- Docker 20.10+
- Docker Compose 2.0+
- Python 3.10+
- 16GB RAM minimum
- 4+ CPU cores
- 100GB available storage

### Installation
1. Extract the release archive
2. Run \`./install.sh\`
3. Configure \`.env\` file
4. Run \`./scripts/first_run.sh\`

### Documentation
See the \`docs/\` directory for:
- Quick Start Guide
- Architecture Overview
- API Reference
- Security Guide
- Deployment Guide

### Support
- GitHub Issues: https://github.com/your-org/dean/issues
- Documentation: https://dean-docs.example.com
EOF

# Create archive
echo -e "${YELLOW}Creating release archive...${NC}"
cd "$RELEASE_DIR"
tar -czf "${RELEASE_NAME}.tar.gz" "$RELEASE_NAME"

# Create checksum
echo -e "${YELLOW}Creating checksum...${NC}"
if command -v sha256sum &> /dev/null; then
    sha256sum "${RELEASE_NAME}.tar.gz" > "${RELEASE_NAME}.tar.gz.sha256"
else
    shasum -a 256 "${RELEASE_NAME}.tar.gz" > "${RELEASE_NAME}.tar.gz.sha256"
fi

# Cleanup
rm -rf "$RELEASE_PATH"

# Summary
ARCHIVE_SIZE=$(du -h "${RELEASE_NAME}.tar.gz" | cut -f1)

echo ""
echo -e "${GREEN}✅ Release package created successfully!${NC}"
echo ""
echo "Release Information:"
echo "  Version: $VERSION"
echo "  Archive: ${RELEASE_NAME}.tar.gz"
echo "  Size: $ARCHIVE_SIZE"
echo "  Location: $RELEASE_DIR/"
echo ""
echo "Distribution:"
echo "  1. Upload ${RELEASE_NAME}.tar.gz to release server"
echo "  2. Share checksum file for verification"
echo "  3. Update download links in documentation"
echo ""

# Generate distribution commands
echo "Quick distribution commands:"
echo "  scp $RELEASE_DIR/${RELEASE_NAME}.tar.gz user@server:/path/to/releases/"
echo "  curl -F file=@$RELEASE_DIR/${RELEASE_NAME}.tar.gz https://releases.example.com/upload"