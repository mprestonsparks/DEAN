# DEAN Deployment Rollback Script
# Purpose: Quickly rollback to previous deployment version
# Usage: .\rollback_deployment.ps1 [-Environment staging|production] [-BackupId <timestamp>]

param(
    [ValidateSet("staging", "production")]
    [string]$Environment = "production",
    [string]$BackupId = "",
    [switch]$Force = $false
)

$ErrorActionPreference = "Stop"

Write-Host "=== DEAN Deployment Rollback ===" -ForegroundColor Red
Write-Host "Environment: $Environment" -ForegroundColor Yellow
Write-Host ""

# Confirmation
if (-not $Force) {
    Write-Host "⚠️  WARNING: This will rollback the $Environment deployment!" -ForegroundColor Yellow
    Write-Host "Current deployment will be stopped and previous version restored." -ForegroundColor Yellow
    $confirm = Read-Host "Are you sure you want to continue? (yes/no)"
    if ($confirm -ne "yes") {
        Write-Host "Rollback cancelled." -ForegroundColor Gray
        exit 0
    }
}

# Set paths based on environment
$deploymentPath = if ($Environment -eq "production") {
    "C:\dean\production\DEAN"
} else {
    "C:\dean\staging\DEAN"
}

$backupPath = "C:\dean\shared\backups\$Environment"

# Check if deployment exists
if (-not (Test-Path $deploymentPath)) {
    Write-Host "✗ Deployment not found at: $deploymentPath" -ForegroundColor Red
    exit 1
}

Set-Location $deploymentPath

# Step 1: Stop current deployment
Write-Host "Step 1: Stopping current deployment..." -ForegroundColor Yellow

try {
    docker-compose -f docker-compose.prod.yml down
    Write-Host "✓ Current deployment stopped" -ForegroundColor Green
} catch {
    Write-Host "⚠ Failed to stop deployment cleanly: $_" -ForegroundColor Yellow
    Write-Host "Attempting force stop..." -ForegroundColor Yellow
    docker stop $(docker ps -q --filter "label=com.docker.compose.project=dean-$Environment") 2>$null
}

# Step 2: Find backup to restore
Write-Host "`nStep 2: Finding backup to restore..." -ForegroundColor Yellow

if ($BackupId) {
    $backupFile = "$backupPath\dean_backup_$BackupId.tar.gz"
    if (-not (Test-Path $backupFile)) {
        Write-Host "✗ Specified backup not found: $backupFile" -ForegroundColor Red
        exit 1
    }
} else {
    # Find most recent backup
    $backups = Get-ChildItem -Path $backupPath -Filter "dean_backup_*.tar.gz" -ErrorAction SilentlyContinue | 
               Sort-Object LastWriteTime -Descending
    
    if ($backups.Count -eq 0) {
        Write-Host "✗ No backups found in: $backupPath" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "Available backups:" -ForegroundColor Cyan
    $backups | Select-Object -First 5 | ForEach-Object {
        Write-Host "  - $($_.Name) ($(Get-Date $_.LastWriteTime -Format 'yyyy-MM-dd HH:mm:ss'))" -ForegroundColor Gray
    }
    
    $backupFile = $backups[0].FullName
    Write-Host "`nUsing most recent backup: $($backups[0].Name)" -ForegroundColor Yellow
}

# Step 3: Create rollback point
Write-Host "`nStep 3: Creating rollback point of current state..." -ForegroundColor Yellow

$rollbackTimestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$rollbackDir = "$backupPath\rollback_$rollbackTimestamp"

try {
    New-Item -ItemType Directory -Path $rollbackDir -Force | Out-Null
    
    # Save current configuration
    if (Test-Path ".env") {
        Copy-Item ".env" "$rollbackDir\.env.backup"
    }
    
    # Save docker compose state
    docker-compose -f docker-compose.prod.yml config > "$rollbackDir\docker-compose.snapshot.yml"
    
    # Save container logs
    docker-compose -f docker-compose.prod.yml logs > "$rollbackDir\container_logs.txt" 2>&1
    
    Write-Host "✓ Rollback point created at: $rollbackDir" -ForegroundColor Green
} catch {
    Write-Host "⚠ Failed to create complete rollback point: $_" -ForegroundColor Yellow
}

# Step 4: Restore from backup
Write-Host "`nStep 4: Restoring from backup..." -ForegroundColor Yellow

try {
    # Extract backup
    Write-Host "Extracting backup archive..." -ForegroundColor Gray
    tar -xzf $backupFile -C $deploymentPath --strip-components=1
    
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to extract backup"
    }
    
    Write-Host "✓ Backup extracted successfully" -ForegroundColor Green
} catch {
    Write-Host "✗ Failed to restore backup: $_" -ForegroundColor Red
    Write-Host "Attempting to restore rollback point..." -ForegroundColor Yellow
    
    if (Test-Path "$rollbackDir\.env.backup") {
        Copy-Item "$rollbackDir\.env.backup" ".env" -Force
    }
    
    exit 1
}

# Step 5: Restore database if backup exists
Write-Host "`nStep 5: Checking for database backup..." -ForegroundColor Yellow

$dbBackupPattern = $BackupId -replace "dean_backup_", "db_backup_"
$dbBackupFile = Get-ChildItem -Path $backupPath -Filter "*$dbBackupPattern*.sql" -ErrorAction SilentlyContinue | 
                Select-Object -First 1

if ($dbBackupFile) {
    Write-Host "Found database backup: $($dbBackupFile.Name)" -ForegroundColor Cyan
    Write-Host "Restoring database..." -ForegroundColor Yellow
    
    try {
        # Start only database container
        docker-compose -f docker-compose.prod.yml up -d postgres-prod
        Start-Sleep -Seconds 10
        
        # Restore database
        Get-Content $dbBackupFile.FullName | docker exec -i dean-postgres psql -U dean_prod dean_production
        
        Write-Host "✓ Database restored" -ForegroundColor Green
    } catch {
        Write-Host "⚠ Database restore failed: $_" -ForegroundColor Yellow
        Write-Host "  You may need to restore manually" -ForegroundColor Gray
    }
} else {
    Write-Host "⚠ No database backup found for this version" -ForegroundColor Yellow
}

# Step 6: Start rolled-back version
Write-Host "`nStep 6: Starting rolled-back version..." -ForegroundColor Yellow

try {
    docker-compose -f docker-compose.prod.yml up -d
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Rolled-back version started" -ForegroundColor Green
    } else {
        throw "Failed to start services"
    }
} catch {
    Write-Host "✗ Failed to start rolled-back version: $_" -ForegroundColor Red
    exit 1
}

# Step 7: Verify rollback
Write-Host "`nStep 7: Verifying rollback..." -ForegroundColor Yellow

Start-Sleep -Seconds 15

# Check health
try {
    $health = Invoke-RestMethod -Uri "http://localhost:8082/health" -TimeoutSec 10
    if ($health.status -eq "healthy") {
        Write-Host "✓ Health check passed" -ForegroundColor Green
    } else {
        Write-Host "⚠ Health check returned non-healthy status" -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠ Health check failed: $_" -ForegroundColor Yellow
}

# Show running containers
Write-Host "`nRunning containers:" -ForegroundColor Cyan
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Summary
Write-Host "`n=== Rollback Summary ===" -ForegroundColor Cyan
Write-Host "✅ Rollback completed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Rolled back to: $(Split-Path -Leaf $backupFile)" -ForegroundColor White
Write-Host "Rollback point saved at: $rollbackDir" -ForegroundColor White
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Monitor services for stability" -ForegroundColor Gray
Write-Host "2. Check application logs for errors" -ForegroundColor Gray
Write-Host "3. Verify critical functionality" -ForegroundColor Gray
Write-Host "4. Investigate original deployment issue" -ForegroundColor Gray
Write-Host ""
Write-Host "To view logs:" -ForegroundColor Cyan
Write-Host "docker-compose -f docker-compose.prod.yml logs -f" -ForegroundColor Gray