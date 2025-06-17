# DEAN Windows Deployment Guide with Docker Desktop

## Overview
This guide provides instructions for deploying DEAN on Windows systems using Docker Desktop, specifically optimized for systems with Intel i7 processors and RTX 3080 GPUs.

## Prerequisites

### Hardware Requirements
- **CPU**: Intel i7 or equivalent (8+ cores recommended)
- **RAM**: 32GB (24GB allocated to Docker)
- **GPU**: NVIDIA RTX 3080 (optional, for future ML features)
- **Storage**: 100GB+ available SSD space

### Software Requirements
- **Windows**: Windows 10/11 Pro or Enterprise
- **WSL2**: Windows Subsystem for Linux 2
- **Docker Desktop**: 4.20+ with WSL2 backend
- **Git**: Git for Windows with Git Bash
- **Python**: 3.10+ (for local scripts)

## Pre-Deployment Setup

### 1. Install WSL2
```powershell
# Run as Administrator
wsl --install
wsl --set-default-version 2
```

### 2. Install Docker Desktop
- Download from https://www.docker.com/products/docker-desktop
- Enable WSL2 backend during installation
- Allocate resources in Docker Desktop Settings:
  - CPUs: 6
  - Memory: 24GB
  - Swap: 4GB

### 3. Configure Windows Defender
Add exclusions for Docker directories:
```powershell
Add-MpPreference -ExclusionPath "C:\ProgramData\Docker"
Add-MpPreference -ExclusionPath "C:\Program Files\Docker"
Add-MpPreference -ExclusionPath "C:\dean"
```

## Deployment Steps

### 1. Clone Repository
```bash
# Using Git Bash
cd /c/
git clone https://github.com/mprestonsparks/DEAN.git dean
cd dean
```

### 2. Configure Environment
```powershell
# Copy template and edit with secure values
Copy-Item .env.production.template .env
notepad .env

# Generate secure passwords
-join ((65..90) + (97..122) + (48..57) | Get-Random -Count 32 | % {[char]$_})
```

### 3. Run Deployment Script
```powershell
# Execute deployment
.\deploy_windows.ps1
```

### 4. Verify Deployment
```powershell
# Check service health
docker-compose -f docker-compose.prod.yml ps

# Test endpoints
Invoke-WebRequest -Uri https://localhost/health -SkipCertificateCheck
```

## SSL Configuration
For local development, self-signed certificates are generated automatically by deploy_windows.ps1.
For production, obtain certificates from Let's Encrypt or your CA.

## Post-Deployment
1. Access dashboard at https://localhost
2. Login with configured admin credentials
3. Configure service integrations
4. Set up monitoring alerts

## Troubleshooting

### Docker Desktop Not Starting
```powershell
# Verify WSL2
wsl --status
wsl --update

# Restart Docker service
Restart-Service com.docker.service
```

### Permission Issues
```powershell
# Add user to docker-users group
net localgroup docker-users "$env:USERNAME" /add
# Log out and back in
```

### Network Issues
```powershell
# Reset Docker network
docker network prune -f
docker network create dean_default
```

## GPU Support (Future)
To enable GPU support when ML features are implemented:
1. Install NVIDIA drivers
2. Install NVIDIA Container Toolkit
3. Update docker-compose.prod.yml with GPU reservation

## Maintenance
- Logs: `docker-compose -f docker-compose.prod.yml logs -f`
- Backup: Use provided backup scripts in scripts/
- Updates: Pull latest changes and re-run deploy_windows.ps1