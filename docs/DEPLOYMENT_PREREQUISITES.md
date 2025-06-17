# DEAN Deployment Prerequisites
**Last Updated**: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
**Target Platform**: Windows with Docker Desktop

## Required Software Versions
Based on development and testing, the following versions are confirmed compatible:
- Docker Desktop: 4.20+ with WSL2 backend
- Docker Compose: 2.x (included with Docker Desktop)
- PostgreSQL: 13+ (containerized)
- Redis: 7-alpine (containerized)
- Python: 3.10+ (for local scripts)

## Hardware Requirements
Minimum specifications based on development testing:
- CPU: 8 cores (6 allocated to Docker)
- RAM: 32GB (24GB allocated to Docker)
- Storage: 100GB available space
- GPU: Optional (RTX 3080 supported for future ML features)

## Network Requirements
The following ports must be available:
- 443: HTTPS (nginx proxy)
- 8082: Orchestration API
- 8083: Evolution API
- 3000: Grafana dashboards
- 8080: Airflow web UI

## Pre-Deployment Checklist
- [ ] Docker Desktop installed and running
- [ ] WSL2 enabled and updated
- [ ] Git installed with Git Bash
- [ ] Python 3.10+ installed
- [ ] C:\dean directory created
- [ ] Windows Defender exclusions configured
- [ ] Virtualization enabled in BIOS
EOF < /dev/null