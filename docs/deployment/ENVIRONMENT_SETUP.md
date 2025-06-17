# DEAN Environment Configuration Guide

## Overview
This guide explains how to configure the DEAN environment with secure credentials for production deployment.

## Quick Start

### Windows (PowerShell)
```powershell
# Option 1: Use the all-in-one setup script
.\setup_environment.ps1 -AdminEmail "your-email@example.com"

# Option 2: Run scripts individually
.\generate_secrets.ps1
.\configure_env.ps1 -AdminEmail "your-email@example.com"
```

### macOS/Linux (Bash)
```bash
# Make the script executable
chmod +x setup_environment.sh

# Run the setup script
./setup_environment.sh your-email@example.com
```

## Manual Configuration

If you prefer to configure manually or the scripts don't work:

### 1. Generate Secure Passwords

#### Windows PowerShell:
```powershell
# Generate 32-character password
-join ((65..90) + (97..122) + (48..57) | Get-Random -Count 32 | % {[char]$_})

# Generate 64-character secret
-join ((65..90) + (97..122) + (48..57) | Get-Random -Count 64 | % {[char]$_})
```

#### macOS/Linux:
```bash
# Generate 32-character password
openssl rand -base64 32 | tr -d "=+/" | cut -c1-32

# Generate 64-character secret
openssl rand -base64 64 | tr -d "=+/" | cut -c1-64
```

### 2. Copy Template
```bash
cp .env.production.template .env
```

### 3. Edit .env File
Replace the following placeholders:
- `CHANGE_ME_SECURE_PASSWORD` → Your generated 32-character passwords
- `CHANGE_ME_64_CHAR_SECRET` → Your generated 64-character JWT secret
- `https://your-domain.com` → `https://localhost` (for local deployment)
- `admin@your-domain.com` → Your admin email address

### 4. Update Connection Strings
Ensure the database and Redis URLs contain your actual passwords:
```
DATABASE_URL=postgresql://dean_prod:[YOUR_DB_PASSWORD]@postgres-prod:5432/dean_production
REDIS_URL=redis://:[YOUR_REDIS_PASSWORD]@redis-prod:6379
```

## Environment Variables Reference

### Required Variables
| Variable | Description | Default | Security |
|----------|-------------|---------|----------|
| `POSTGRES_PASSWORD` | PostgreSQL database password | None | 32+ chars |
| `REDIS_PASSWORD` | Redis cache password | None | 32+ chars |
| `JWT_SECRET_KEY` | JWT token signing key | None | 64+ chars |
| `DATABASE_URL` | Full PostgreSQL connection string | None | Contains password |
| `REDIS_URL` | Full Redis connection string | None | Contains password |

### Configuration Variables
| Variable | Description | Default |
|----------|-------------|---------|
| `POSTGRES_USER` | Database username | dean_prod |
| `POSTGRES_DB` | Database name | dean_production |
| `CORS_ALLOWED_ORIGINS` | Allowed CORS origins | https://localhost |
| `DEAN_ADMIN_EMAIL` | Administrator email | admin@localhost |

### Resource Variables
| Variable | Description | Default |
|----------|-------------|---------|
| `MAX_WORKERS` | Maximum worker processes | 16 |
| `MAX_MEMORY_PER_WORKER` | Memory limit per worker | 2G |
| `UVICORN_WORKERS` | API server workers | 8 |
| `DB_POOL_SIZE` | Database connection pool | 20 |

### Feature Flags
| Variable | Description | Default |
|----------|-------------|---------|
| `ENABLE_GPU_ACCELERATION` | Enable GPU support | false |
| `ENABLE_PATTERN_DISCOVERY` | Enable pattern discovery | true |
| `ENABLE_AUTO_EVOLUTION` | Enable auto evolution | true |

## Security Best Practices

1. **Never commit .env files** - The .gitignore is configured to exclude them
2. **Use strong passwords** - Minimum 32 characters for passwords, 64 for JWT
3. **Rotate credentials regularly** - Change passwords every 90 days
4. **Limit access** - Only deployment administrators should have .env access
5. **Use secrets management** - Consider HashiCorp Vault or similar for production

## Verification

After configuration, verify your setup:

### Check for security issues:
```bash
# Ensure no CHANGE_ME values remain
grep -i "CHANGE_ME" .env

# Verify password lengths
grep "PASSWORD=" .env | awk -F= '{print length($2)}'
```

### Test configuration:
```bash
# Validate with Python script
python scripts/validate_config.py

# Or manually check Docker can read it
docker-compose -f docker-compose.prod.yml config
```

## Troubleshooting

### Common Issues

**Issue**: Scripts fail with "command not found"
- **Solution**: Ensure you're using PowerShell 7+ on Windows or bash on Unix

**Issue**: Permission denied errors
- **Solution**: Run PowerShell as Administrator on Windows

**Issue**: Special characters in passwords cause issues
- **Solution**: Use only alphanumeric characters (A-Z, a-z, 0-9)

**Issue**: .env file not found by Docker
- **Solution**: Ensure you're in the DEAN root directory when running commands

## Next Steps

Once your environment is configured:

1. Run deployment:
   - Windows: `.\deploy_windows.ps1`
   - Linux/macOS: `docker-compose -f docker-compose.prod.yml up -d`

2. Verify services:
   ```bash
   docker-compose -f docker-compose.prod.yml ps
   curl http://localhost:8082/health
   ```

3. Access the system:
   - API: http://localhost:8082
   - Dashboard: https://localhost

## Support

For issues with environment configuration:
1. Check this guide first
2. Review logs: `docker-compose logs`
3. Submit issues: https://github.com/mprestonsparks/DEAN/issues