# DEAN Deployment Guide

**Version**: 1.0.0  
**Last Updated**: 2025-06-16T22:31:07Z

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Initial Setup](#initial-setup)
3. [Configuration](#configuration)
4. [Deployment](#deployment)
5. [Verification](#verification)
6. [Troubleshooting](#troubleshooting)

## Prerequisites

Before deploying DEAN, ensure you have:

- Windows 10/11 with WSL2 enabled
- Docker Desktop 4.20+ installed and running
- Git and Git Bash installed
- Python 3.10+ installed
- At least 32GB RAM (24GB allocated to Docker)
- 100GB available disk space

## Initial Setup

### 1. Clone Repository
```bash
git clone https://github.com/mprestonsparks/DEAN.git
cd DEAN
```

### 2. Create Deployment Directory
```bash
# Create deployment directory
mkdir -p C:/dean
cp -r * C:/dean/
cd C:/dean
```

### 3. Configure Environment
```bash
# Copy environment template
cp .env.production.template .env

# Edit .env file with your secure values
# IMPORTANT: Replace all CHANGE_ME values with secure passwords
```

## Configuration

### Environment Variables
Edit the `.env` file and configure:

- **Database Credentials**:
  - `POSTGRES_PASSWORD`: Strong password (32+ characters)
  - `POSTGRES_USER`: Database username (default: dean_prod)
  
- **Redis Security**:
  - `REDIS_PASSWORD`: Strong password for Redis

- **JWT Security**:
  - `JWT_SECRET_KEY`: 64+ character secret key

- **Domain Configuration**:
  - `CORS_ALLOWED_ORIGINS`: Your production domain
  - `DEAN_ADMIN_EMAIL`: Administrator email

### SSL Certificates
Place SSL certificates in the `certs/` directory:
```bash
mkdir -p certs
# Copy your certificates
cp /path/to/cert.pem certs/
cp /path/to/key.pem certs/
```

## Deployment

### Using PowerShell Script (Recommended)
```powershell
# Run from PowerShell as Administrator
./deploy_windows.ps1
```

### Manual Deployment
```bash
# Validate configuration
python scripts/validate_config.py

# Build images
docker-compose -f docker-compose.prod.yml build

# Start infrastructure services
docker-compose -f docker-compose.prod.yml up -d postgres-prod redis-prod

# Wait for services to be ready
sleep 15

# Run database migrations
docker-compose -f docker-compose.prod.yml run --rm orchestrator python -m alembic upgrade head

# Start all services
docker-compose -f docker-compose.prod.yml up -d
```

## Verification

### 1. Check Service Health
```bash
# Check all containers are running
docker ps

# Check orchestrator health
curl http://localhost:8082/health

# Check nginx proxy
curl https://localhost/health
```

### 2. View Logs
```bash
# View all logs
docker-compose -f docker-compose.prod.yml logs

# View specific service logs
docker-compose -f docker-compose.prod.yml logs orchestrator
```

### 3. Access Web Interfaces
- Main API: https://localhost
- Orchestration API: http://localhost:8082
- Grafana: http://localhost:3000
- Airflow: http://localhost:8080

## Troubleshooting

### Port Conflicts
If you encounter port conflicts:
```bash
# Check which process is using a port
netstat -ano | findstr :8082

# Modify ports in docker-compose.prod.yml
```

### Docker Issues
```bash
# Reset Docker Desktop
# Settings > Troubleshoot > Reset to factory defaults

# Clean up containers and volumes
docker-compose -f docker-compose.prod.yml down -v
docker system prune -a
```

### Database Connection Issues
```bash
# Check PostgreSQL logs
docker logs dean-postgres

# Test database connection
docker exec -it dean-postgres psql -U dean_prod -d dean_production
```

### Permission Issues
Ensure Docker Desktop has access to your drive:
- Docker Desktop > Settings > Resources > File Sharing
- Add C:/dean to shared paths

## Maintenance

### Backup Database
```bash
docker exec dean-postgres pg_dump -U dean_prod dean_production > backup_$(date +%Y%m%d).sql
```

### Update Services
```bash
# Pull latest changes
git pull

# Rebuild and restart
docker-compose -f docker-compose.prod.yml up -d --build
```

### Monitor Resources
```bash
# Check container resources
docker stats

# Check disk usage
docker system df
```

## Support

For issues or questions:
- GitHub Issues: https://github.com/mprestonsparks/DEAN/issues
- Documentation: /docs
- Security concerns: See SECURITY.md