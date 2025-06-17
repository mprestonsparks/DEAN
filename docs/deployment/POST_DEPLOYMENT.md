# DEAN Post-Deployment Guide

## Service Access Points

After successful deployment, DEAN services are available at:

### Direct Access (Always Available)
- **Orchestrator API**: http://localhost:8082
- **Health Check**: http://localhost:8082/health
- **API Documentation**: http://localhost:8082/docs (if enabled)

### Via Nginx (If Configured)
- **HTTP**: http://localhost
- **HTTPS**: https://localhost (requires SSL certificates)

## Quick Commands

### Check Service Status
```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

### View Logs
```bash
# All services
docker-compose -f docker-compose.prod.yml logs -f

# Specific service
docker logs dean-orchestrator -f
```

### Restart Services
```bash
docker-compose -f docker-compose.prod.yml restart
```

### Stop Services
```bash
docker-compose -f docker-compose.prod.yml down
```

## Troubleshooting

### Nginx Issues
If nginx fails to start:

1. Check if nginx config exists: `ls nginx/`
2. Run without nginx: `docker-compose -f docker-compose.prod.yml up -d postgres-prod redis-prod orchestrator`
3. Access orchestrator directly at http://localhost:8082

### SSL Certificate Issues

#### Option 1: Convert Existing PFX Certificate (Windows)
If you have an existing localhost.pfx certificate:
```powershell
# Convert PFX to nginx-compatible format
.\scripts\convert_pfx_to_pem.ps1 -PfxPath .\certs\localhost.pfx

# Or use the comprehensive setup script
.\scripts\setup_nginx_certs.ps1 -PfxPath .\certs\localhost.pfx
```

#### Option 2: Generate New Self-Signed Certificates
```bash
# Linux/macOS
./scripts/generate_ssl_certs.sh

# Windows (PowerShell)
.\scripts\setup_nginx_certs.ps1 -GenerateNew
```

### Permission Issues on Windows
Run PowerShell as Administrator or use the provided start script:
```powershell
.\start_dean_windows.ps1
```