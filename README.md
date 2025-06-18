# Distributed Evolutionary Agent Network (DEAN)

**Version**: 1.0.0  
**Status**: Production Ready  
**Last Updated**: 2024-01-20

## 🚀 Quick Start Deployment

### Prerequisites
- Windows 10/11 with WSL2 or Linux/macOS
- Docker Desktop 4.20+ or Docker Engine 20.10+
- 32GB RAM (24GB allocated to Docker)
- 100GB available storage
- PowerShell 7+ (Windows) or Bash (Linux/macOS)

### One-Command Setup (Recommended)
```powershell
# Windows PowerShell
./scripts/setup_environment.ps1 -Environment production -GenerateSecrets
./scripts/validate_deployment.ps1
./deploy_windows.ps1

# Linux/macOS
./scripts/setup_environment.sh
./scripts/validate_deployment.sh
./scripts/deploy/deploy_dean_system.sh
```

### Manual Deployment Steps
1. **Clone Repository**
   ```bash
   git clone https://github.com/mprestonsparks/DEAN.git
   cd DEAN
   ```

2. **Setup Environment**
   ```powershell
   # Automated setup with validation
   ./scripts/setup_environment.ps1 -GenerateSecrets
   
   # Or manual setup
   cp .env.template .env
   # Edit .env with secure values
   ```

3. **Validate Configuration**
   ```powershell
   # Comprehensive validation with auto-fix
   ./scripts/validate_deployment.ps1 -AutoFix
   ```

4. **Setup SSL Certificates**
   ```powershell
   # Development (self-signed)
   ./scripts/setup_ssl.ps1 -Environment development
   
   # Production (see instructions)
   ./scripts/setup_ssl.ps1 -ShowInstructions
   ```

5. **Deploy Services**
   ```bash
   # Production deployment
   docker compose -f docker-compose.prod.yml up -d
   
   # Development deployment
   docker compose up -d
   ```

6. **Verify Deployment**
   ```bash
   # Check health endpoints
   curl http://localhost:8082/health
   curl http://localhost/health
   
   # For HTTPS with self-signed certs, use browser
   # Navigate to: https://localhost/health
   ```

## Architecture Overview
DEAN orchestrates AI-driven code evolution through:
- **Orchestration API**: Central coordination service
- **Evolution Engine**: Genetic algorithm implementation
- **Pattern Discovery**: ML-based optimization detection
- **Airflow Integration**: Task scheduling and management

## 📚 Documentation
- [Deployment Checklist](docs/DEPLOYMENT_CHECKLIST.md) - Step-by-step deployment validation
- [Troubleshooting Guide](docs/TROUBLESHOOTING.md) - Solutions for common issues
- [Deployment Guide](docs/deployment/DEPLOYMENT_GUIDE.md) - Comprehensive deployment instructions
- [Configuration Reference](docs/configuration/README.md) - Environment variable reference
- [API Documentation](docs/api/README.md) - REST API endpoints
- [Operations Manual](docs/operations/README.md) - Production operations guide

## ⚡ Deployment Best Practices

### Pre-Deployment Validation
Always run validation before deployment to catch common issues:
```powershell
# Full validation with automatic fixes
./scripts/validate_deployment.ps1 -AutoFix -Verbose
```

This prevents:
- BOM characters in configuration files
- Missing SSL certificates
- Environment variable mismatches
- Port conflicts
- Missing directories

### Known Issues and Solutions

| Issue | Solution |
|-------|----------|
| BOM in config files | Run validation script with -AutoFix |
| Database name mismatch | Ensure POSTGRES_DB="dean_production" everywhere |
| SSL certificate missing | Run setup_ssl.ps1 script |
| PowerShell HTTPS errors | Use browser for self-signed cert testing |
| Port already in use | Check with validation script, stop conflicting services |

### Security Considerations
1. **Always generate new secrets** for production
2. **Replace self-signed certificates** with CA certificates
3. **Review CORS settings** for your domain
4. **Enable firewall rules** to restrict access
5. **Regular security updates** via CI/CD pipeline

## System Components
- **dean-orchestrator**: Core orchestration service
- **dean-evolution**: Evolution engine
- **dean-postgres**: Primary database
- **dean-redis**: Caching and queuing
- **dean-airflow**: Task orchestration
- **dean-dashboard**: Web interface

## 🛠️ Maintenance & Monitoring

### Health Monitoring
```bash
# Quick health check
./scripts/health_check.sh

# Detailed diagnostics
./scripts/troubleshoot.sh

# View logs
docker compose logs -f --tail=100
```

### Backup & Recovery
```bash
# Automated backup
docker exec dean-postgres pg_dump -U dean_prod dean_production > backup.sql

# Restore from backup
docker exec -i dean-postgres psql -U dean_prod dean_production < backup.sql
```

## 🤝 Support & Contributing

### Getting Help
- **Issues**: [GitHub Issues](https://github.com/mprestonsparks/DEAN/issues)
- **Documentation**: [/docs](./docs) directory
- **Troubleshooting**: [Troubleshooting Guide](docs/TROUBLESHOOTING.md)
- **Deployment Help**: [Deployment Checklist](docs/DEPLOYMENT_CHECKLIST.md)

### Contributing
1. Fork the repository
2. Create a feature branch
3. Run validation: `./scripts/validate_deployment.ps1`
4. Submit a pull request

### CI/CD Pipeline
All pull requests automatically run:
- Configuration validation (BOM check, YAML syntax)
- Security scanning (credentials, vulnerabilities)
- SSL configuration verification
- Documentation link checking

## 📝 License
MIT License - see [LICENSE](LICENSE) for details

---

**Built with** ❤️ **by the DEAN Team**