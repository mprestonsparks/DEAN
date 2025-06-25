# DEAN Credential Deployment Script for Windows
# This script updates the production deployment with secure credentials

param(
    [Parameter(Mandatory=$false)]
    [string]$DeploymentPath = "C:\DEAN",
    
    [Parameter(Mandatory=$false)]
    [string]$BackupPath = "C:\DEAN\backups\credentials"
)

# Create backup directory
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupDir = Join-Path $BackupPath $timestamp

Write-Host "DEAN Credential Deployment Script" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan

# Check if deployment directory exists
if (-not (Test-Path $DeploymentPath)) {
    Write-Host "ERROR: Deployment directory not found: $DeploymentPath" -ForegroundColor Red
    exit 1
}

# Create backup of existing credentials
Write-Host "`nBacking up existing credentials..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path $backupDir | Out-Null

# Backup existing .env files
$envFiles = @(".env", ".env.local", ".env.production")
foreach ($file in $envFiles) {
    $sourcePath = Join-Path $DeploymentPath $file
    if (Test-Path $sourcePath) {
        Copy-Item $sourcePath -Destination $backupDir
        Write-Host "  ✓ Backed up $file" -ForegroundColor Green
    }
}

# Backup docker-compose files with credentials
$composeFiles = Get-ChildItem -Path $DeploymentPath -Filter "docker-compose*.yml"
foreach ($file in $composeFiles) {
    Copy-Item $file.FullName -Destination $backupDir
    Write-Host "  ✓ Backed up $($file.Name)" -ForegroundColor Green
}

Write-Host "`nBackup completed to: $backupDir" -ForegroundColor Green

# Stop running services
Write-Host "`nStopping DEAN services..." -ForegroundColor Yellow
Set-Location $DeploymentPath
docker-compose down

# Create secure .env.production file
Write-Host "`nCreating secure environment configuration..." -ForegroundColor Yellow

# Read the generated credentials (this would be copied from the local machine)
$envContent = @'
# DEAN Production Environment Configuration
# Generated: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
# WARNING: This file contains sensitive credentials. Protect it carefully!

# Database Configuration
POSTGRES_USER=dean_admin
POSTGRES_PASSWORD=SECURE_PASSWORD_PLACEHOLDER_1
POSTGRES_DB=agent_evolution
DATABASE_URL=postgresql://dean_admin:SECURE_PASSWORD_PLACEHOLDER_1@postgres:5432/agent_evolution
DEAN_DATABASE_URL=postgresql://dean_admin:SECURE_PASSWORD_PLACEHOLDER_1@postgres:5432/agent_evolution
AGENT_EVOLUTION_DATABASE_URL=postgresql://dean_admin:SECURE_PASSWORD_PLACEHOLDER_1@postgres:5432/agent_evolution

# Redis Configuration
REDIS_PASSWORD=SECURE_PASSWORD_PLACEHOLDER_2
REDIS_URL=redis://:SECURE_PASSWORD_PLACEHOLDER_2@redis:6379/0

# DEAN Service Configuration
DEAN_SERVICE_API_KEY=SECURE_API_KEY_PLACEHOLDER_1
DEAN_JWT_SECRET_KEY=SECURE_JWT_KEY_PLACEHOLDER
DEAN_ADMIN_PASSWORD=SECURE_PASSWORD_PLACEHOLDER_3
DEAN_ENV=production

# Airflow Configuration
AIRFLOW_ADMIN_PASSWORD=SECURE_PASSWORD_PLACEHOLDER_4
AIRFLOW__CORE__FERNET_KEY=SECURE_FERNET_KEY_PLACEHOLDER
AIRFLOW__WEBSERVER__SECRET_KEY=SECURE_SECRET_KEY_PLACEHOLDER

# Service API Keys
INDEXAGENT_API_KEY=SECURE_API_KEY_PLACEHOLDER_2
EVOLUTION_API_KEY=SECURE_API_KEY_PLACEHOLDER_3
MONITORING_API_KEY=SECURE_API_KEY_PLACEHOLDER_4

# External Services
CLAUDE_API_KEY=YOUR_CLAUDE_API_KEY_HERE
GITHUB_TOKEN=YOUR_GITHUB_TOKEN_HERE

# Service URLs (internal Docker network)
DEAN_SERVER_HOST=dean-orchestration
DEAN_SERVER_PORT=8082
DEAN_WEB_PORT=8083
INDEXAGENT_URL=http://indexagent:8081
AIRFLOW_URL=http://airflow-webserver:8080
EVOLUTION_API_URL=http://evolution-api:8090
PROMETHEUS_URL=http://prometheus:9090
GRAFANA_URL=http://grafana:3000

# Resource Limits
AGENT_MAX_CONCURRENT=8
AGENT_TOKEN_LIMIT=4096
AGENT_EVOLUTION_MAX_POPULATION=100000
DEAN_MIN_DIVERSITY=0.3
DEAN_MUTATION_RATE=0.1
DEAN_MIN_VALUE_PER_TOKEN=0.001

# Deployment Configuration
DOCKER_DEFAULT_PLATFORM=linux/amd64
COMPOSE_PROJECT_NAME=dean-production
'@

# Save the new .env.production file
$envPath = Join-Path $DeploymentPath ".env.production"
$envContent | Out-File -FilePath $envPath -Encoding UTF8
Write-Host "  ✓ Created .env.production" -ForegroundColor Green

# Set secure permissions on .env file
$acl = Get-Acl $envPath
$acl.SetAccessRuleProtection($true, $false)
$adminRule = New-Object System.Security.AccessControl.FileSystemAccessRule("Administrators","FullControl","Allow")
$systemRule = New-Object System.Security.AccessControl.FileSystemAccessRule("SYSTEM","FullControl","Allow")
$userRule = New-Object System.Security.AccessControl.FileSystemAccessRule($env:USERNAME,"ReadAndExecute","Allow")
$acl.SetAccessRule($adminRule)
$acl.SetAccessRule($systemRule)
$acl.SetAccessRule($userRule)
Set-Acl -Path $envPath -AclObject $acl
Write-Host "  ✓ Set secure permissions on .env.production" -ForegroundColor Green

# Create production docker-compose override
Write-Host "`nCreating production Docker Compose configuration..." -ForegroundColor Yellow

$composeOverride = @'
# docker-compose.prod.yml
# Production configuration with security hardening
version: '3.8'

services:
  postgres:
    restart: always
    volumes:
      - postgres-data:/var/lib/postgresql/data
    environment:
      POSTGRES_PASSWORD_FILE: /run/secrets/postgres_password
    secrets:
      - postgres_password
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U dean_admin"]
      interval: 30s
      timeout: 10s
      retries: 5
      
  redis:
    restart: always
    volumes:
      - redis-data:/data
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 5
      
  dean-orchestration:
    restart: always
    environment:
      DEAN_ENV: production
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
        
  indexagent:
    restart: always
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
              
  evolution-api:
    restart: always
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
          
  airflow-webserver:
    restart: always
    depends_on:
      postgres:
        condition: service_healthy
        
  airflow-scheduler:
    restart: always
    depends_on:
      postgres:
        condition: service_healthy
        
  prometheus:
    restart: always
    volumes:
      - prometheus-data:/prometheus
      
  grafana:
    restart: always
    volumes:
      - grafana-data:/var/lib/grafana
    environment:
      GF_SECURITY_ADMIN_PASSWORD: ${DEAN_ADMIN_PASSWORD}
      GF_INSTALL_PLUGINS: grafana-clock-panel,grafana-simple-json-datasource

volumes:
  postgres-data:
    driver: local
  redis-data:
    driver: local
  prometheus-data:
    driver: local
  grafana-data:
    driver: local
    
secrets:
  postgres_password:
    file: ./secrets/postgres_password.txt
'@

$prodComposePath = Join-Path $DeploymentPath "docker-compose.prod.yml"
$composeOverride | Out-File -FilePath $prodComposePath -Encoding UTF8
Write-Host "  ✓ Created docker-compose.prod.yml" -ForegroundColor Green

# Create secrets directory and files
$secretsDir = Join-Path $DeploymentPath "secrets"
New-Item -ItemType Directory -Force -Path $secretsDir | Out-Null

# Create placeholder secrets files
"SECURE_PASSWORD_PLACEHOLDER_1" | Out-File -FilePath (Join-Path $secretsDir "postgres_password.txt") -Encoding UTF8 -NoNewline

# Set secure permissions on secrets directory
$acl = Get-Acl $secretsDir
$acl.SetAccessRuleProtection($true, $false)
$adminRule = New-Object System.Security.AccessControl.FileSystemAccessRule("Administrators","FullControl","Allow")
$systemRule = New-Object System.Security.AccessControl.FileSystemAccessRule("SYSTEM","FullControl","Allow")
$acl.SetAccessRule($adminRule)
$acl.SetAccessRule($systemRule)
Set-Acl -Path $secretsDir -AclObject $acl
Write-Host "  ✓ Created secrets directory with secure permissions" -ForegroundColor Green

# Update Grafana configuration
Write-Host "`nUpdating Grafana configuration..." -ForegroundColor Yellow
$grafanaConfigPath = Join-Path $DeploymentPath "monitoring\grafana\grafana.ini"
if (Test-Path $grafanaConfigPath) {
    $grafanaConfig = Get-Content $grafanaConfigPath
    $grafanaConfig = $grafanaConfig -replace 'admin_password = admin', 'admin_password = ${DEAN_ADMIN_PASSWORD}'
    $grafanaConfig | Out-File -FilePath $grafanaConfigPath -Encoding UTF8
    Write-Host "  ✓ Updated Grafana admin password configuration" -ForegroundColor Green
}

# Create credential update instructions
$instructionsPath = Join-Path $DeploymentPath "CREDENTIAL_UPDATE_INSTRUCTIONS.txt"
@"
DEAN CREDENTIAL UPDATE INSTRUCTIONS
===================================

The secure credential placeholders have been created. You must now:

1. Replace all PLACEHOLDER values in .env.production with the actual secure values
   generated by generate_credentials.py

2. Update the secrets/postgres_password.txt file with the actual PostgreSQL password

3. Add your actual CLAUDE_API_KEY and GITHUB_TOKEN to .env.production

4. After updating all credentials, start the services with:
   docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

5. Verify all services are running:
   docker-compose ps

6. Check service health:
   curl http://localhost:8082/health  # DEAN orchestration
   curl http://localhost:8081/health  # IndexAgent
   curl http://localhost:8090/health  # Evolution API

Security Notes:
- Keep the backup directory secure: $backupDir
- Never commit .env.production or secrets/ to version control
- Regularly rotate credentials
- Monitor access logs for suspicious activity

"@ | Out-File -FilePath $instructionsPath -Encoding UTF8

Write-Host "`n✅ Credential deployment preparation completed!" -ForegroundColor Green
Write-Host "`n📋 NEXT STEPS:" -ForegroundColor Cyan
Write-Host "1. Copy actual credentials from generate_credentials.py output" -ForegroundColor White
Write-Host "2. Replace all PLACEHOLDER values in $envPath" -ForegroundColor White
Write-Host "3. Update secrets files in $secretsDir" -ForegroundColor White
Write-Host "4. Add your CLAUDE_API_KEY and GITHUB_TOKEN" -ForegroundColor White
Write-Host "5. Run: docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d" -ForegroundColor White
Write-Host "`nDetailed instructions saved to: $instructionsPath" -ForegroundColor Yellow