# Runtime Environment Diagnostic Script
param(
    [switch]$AutoFix = $false
)

Write-Host "DEAN Runtime Database Configuration Diagnostic" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan

# Function to check Docker container environment
function Test-DockerEnvironment {
    Write-Host "`nChecking Docker container configurations..." -ForegroundColor Yellow
    
    # Check if containers are running
    $runningContainers = docker ps --format "table {{.Names}}\t{{.Status}}" | Select-String "dean-"
    if ($runningContainers) {
        Write-Host "Running DEAN containers:" -ForegroundColor Green
        $runningContainers | ForEach-Object { Write-Host "  $_" }
        
        # Check environment variables in running containers
        Write-Host "`nChecking orchestrator environment:" -ForegroundColor Yellow
        docker exec dean-orchestrator printenv | Select-String "POSTGRES|DATABASE" | ForEach-Object {
            Write-Host "  $_"
        }
    } else {
        Write-Host "No DEAN containers are currently running" -ForegroundColor Red
    }
}

# Function to check local environment files
function Test-LocalEnvironment {
    Write-Host "`nChecking local environment files..." -ForegroundColor Yellow
    
    $envFiles = @(".env", ".env.production", ".env.local")
    foreach ($envFile in $envFiles) {
        if (Test-Path $envFile) {
            Write-Host "`nFound $envFile with following database settings:" -ForegroundColor Green
            Get-Content $envFile | Select-String "POSTGRES|DATABASE" | ForEach-Object {
                $line = $_.Line.Trim()
                if ($line -match "dean_prod(?!uction)") {
                    Write-Host "  ❌ $line" -ForegroundColor Red
                    Write-Host "     ^ This should be 'dean_production'" -ForegroundColor Yellow
                } else {
                    Write-Host "  ✓ $line" -ForegroundColor Green
                }
            }
        }
    }
}

# Function to create corrected environment file
function New-CorrectedEnvironment {
    Write-Host "`nCreating corrected environment configuration..." -ForegroundColor Yellow
    
    $correctedEnv = @"
# DEAN Production Environment Configuration
# Database Configuration
POSTGRES_HOST=dean-postgres
POSTGRES_PORT=5432
POSTGRES_USER=dean_prod
POSTGRES_PASSWORD=CHANGE_ME_SECURE_PASSWORD
POSTGRES_DB=dean_production

# Correct database URL format
DATABASE_URL=postgresql://dean_prod:CHANGE_ME_SECURE_PASSWORD@dean-postgres:5432/dean_production

# Application Configuration
NODE_ENV=production
API_PORT=8082
"@

    $correctedEnv | Out-File -FilePath ".env.corrected" -Encoding UTF8
    Write-Host "Created .env.corrected with proper database configuration" -ForegroundColor Green
}

# Main diagnostic and fix logic
Write-Host "`nStarting diagnostic..." -ForegroundColor Cyan

# Run diagnostics
Test-DockerEnvironment
Test-LocalEnvironment

# Check for specific issue
$hasIssue = $false
if (Test-Path ".env") {
    $envContent = Get-Content ".env" -Raw
    if ($envContent -match "POSTGRES_DB\s*=\s*dean_prod\s*$") {
        $hasIssue = $true
        Write-Host "`n⚠️  ISSUE FOUND: .env file has incorrect database name 'dean_prod'" -ForegroundColor Red
    }
}

if ($hasIssue) {
    if ($AutoFix) {
        Write-Host "`nApplying automatic fix..." -ForegroundColor Yellow
        
        # Backup current .env
        Copy-Item ".env" ".env.backup.$(Get-Date -Format 'yyyyMMdd_HHmmss')"
        Write-Host "Created backup of current .env file" -ForegroundColor Green
        
        # Fix the database name
        $fixedContent = $envContent -replace '(POSTGRES_DB\s*=\s*)dean_prod(\s*$)', '${1}dean_production${2}'
        $fixedContent = $fixedContent -replace '(DATABASE_URL=.*/)dean_prod(/|$)', '${1}dean_production${2}'
        
        $fixedContent | Out-File -FilePath ".env" -Encoding UTF8 -NoNewline
        Write-Host "✓ Fixed database name in .env file" -ForegroundColor Green
        
        Write-Host "`nYou need to restart Docker containers for changes to take effect:" -ForegroundColor Yellow
        Write-Host "  docker-compose -f docker-compose.prod.yml down" -ForegroundColor White
        Write-Host "  docker-compose -f docker-compose.prod.yml up -d" -ForegroundColor White
    } else {
        Write-Host "`nTo fix this issue, run this script with -AutoFix flag:" -ForegroundColor Yellow
        Write-Host "  .\scripts\fix_runtime_database_config.ps1 -AutoFix" -ForegroundColor White
        
        Write-Host "`nOr manually fix by:" -ForegroundColor Yellow
        Write-Host "  1. Edit .env file" -ForegroundColor White
        Write-Host "  2. Change POSTGRES_DB=dean_prod to POSTGRES_DB=dean_production" -ForegroundColor White
        Write-Host "  3. Update DATABASE_URL to use /dean_production instead of /dean_prod" -ForegroundColor White
    }
} else {
    Write-Host "`n✓ No database naming issues found in environment files" -ForegroundColor Green
    Write-Host "`nIf you're still experiencing connection issues, ensure:" -ForegroundColor Yellow
    Write-Host "  1. Docker containers are using the latest environment variables" -ForegroundColor White
    Write-Host "  2. PostgreSQL initialization scripts have been run" -ForegroundColor White
    Write-Host "  3. No cached configurations are overriding settings" -ForegroundColor White
}

# Create reference configuration
New-CorrectedEnvironment
Write-Host "`n✓ Reference configuration created in .env.corrected" -ForegroundColor Green