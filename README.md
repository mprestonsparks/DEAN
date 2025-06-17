# Distributed Evolutionary Agent Network (DEAN)

**Version**: 1.0.0  
**Status**: Ready for Deployment  
**Last Updated**: $(date -u +"%Y-%m-%dT%H:%M:%SZ")

## Quick Start Deployment

### Prerequisites
- Windows 10/11 with WSL2
- Docker Desktop 4.20+
- 32GB RAM (24GB for Docker)
- 100GB available storage

### Deployment Steps
1. **Clone Repository**
   ```bash
   git clone https://github.com/mprestonsparks/DEAN.git
   cd DEAN
   ```

2. **Configure Environment**
   ```bash
   cp .env.production.template .env
   # Edit .env with your secure passwords
   ```

3. **Validate Configuration**
   ```bash
   python scripts/validate_config.py
   ```

4. **Deploy Services**
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

5. **Verify Deployment**
   ```bash
   curl https://localhost/health
   ```

## Architecture Overview
DEAN orchestrates AI-driven code evolution through:
- **Orchestration API**: Central coordination service
- **Evolution Engine**: Genetic algorithm implementation
- **Pattern Discovery**: ML-based optimization detection
- **Airflow Integration**: Task scheduling and management

## Documentation
- [Deployment Guide](docs/deployment/DEPLOYMENT_GUIDE.md)
- [Configuration Reference](docs/configuration/README.md)
- [API Documentation](docs/api/README.md)
- [Operations Manual](docs/operations/README.md)

## System Components
- **dean-orchestrator**: Core orchestration service
- **dean-evolution**: Evolution engine
- **dean-postgres**: Primary database
- **dean-redis**: Caching and queuing
- **dean-airflow**: Task orchestration
- **dean-dashboard**: Web interface

## Support
- Issues: [GitHub Issues](https://github.com/mprestonsparks/DEAN/issues)
- Documentation: [/docs](./docs)
- Deployment Support: See [Deployment Guide](docs/deployment/DEPLOYMENT_GUIDE.md)
EOF < /dev/null