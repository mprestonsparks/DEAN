# DEAN Deployment Pipeline Initialization Script
# Purpose: Set up the complete deployment directory structure and staging environment
# Target: Windows Deployment PC (10.7.0.2)

param(
    [switch]$SkipGitClone = $false,
    [switch]$Force = $false
)

$ErrorActionPreference = "Stop"

Write-Host "=== DEAN Deployment Pipeline Initialization ===" -ForegroundColor Cyan
Write-Host "Target: Windows Deployment PC (10.7.0.2)" -ForegroundColor Gray
Write-Host ""

# Step 1: Initialize deployment directory structure
Write-Host "Step 1: Creating deployment directory structure..." -ForegroundColor Yellow

$directories = @(
    "C:\dean",
    "C:\dean\staging",
    "C:\dean\production",
    "C:\dean\shared",
    "C:\dean\shared\backups",
    "C:\dean\shared\logs",
    "C:\dean\shared\certificates"
)

foreach ($dir in $directories) {
    try {
        if (Test-Path $dir) {
            Write-Host "✓ Directory exists: $dir" -ForegroundColor Gray
        } else {
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
            Write-Host "✓ Created directory: $dir" -ForegroundColor Green
        }
    } catch {
        Write-Host "✗ Failed to create directory: $dir" -ForegroundColor Red
        Write-Host "  Error: $_" -ForegroundColor Red
        exit 1
    }
}

# Verify directory structure
Write-Host "`nVerifying directory structure:" -ForegroundColor Cyan
Get-ChildItem -Path "C:\dean" -Recurse -Directory | ForEach-Object {
    Write-Host "  📁 $($_.FullName)" -ForegroundColor DarkGray
}

# Step 2: Set up staging environment
Write-Host "`nStep 2: Setting up staging environment..." -ForegroundColor Yellow

# Check if repository already exists
$stagingRepoPath = "C:\dean\staging\DEAN"
if (Test-Path $stagingRepoPath) {
    if ($SkipGitClone) {
        Write-Host "✓ Repository already exists at $stagingRepoPath (skipping clone)" -ForegroundColor Gray
    } else {
        Write-Host "⚠ Repository already exists at $stagingRepoPath" -ForegroundColor Yellow
        if ($Force) {
            Write-Host "  Removing existing repository (Force flag set)..." -ForegroundColor Yellow
            Remove-Item -Path $stagingRepoPath -Recurse -Force
            $cloneRepo = $true
        } else {
            Write-Host "  Use -Force flag to remove and re-clone, or -SkipGitClone to skip" -ForegroundColor Gray
            $cloneRepo = $false
        }
    }
} else {
    $cloneRepo = $true
}

# Clone repository if needed
if ($cloneRepo -and -not $SkipGitClone) {
    Write-Host "Cloning DEAN repository to staging..." -ForegroundColor Yellow
    Set-Location "C:\dean\staging"
    
    try {
        # Check if git is available
        $gitVersion = git --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ Git is available: $gitVersion" -ForegroundColor Green
            
            # Clone the repository
            git clone https://github.com/mprestonsparks/DEAN.git
            
            if ($LASTEXITCODE -eq 0) {
                Write-Host "✓ Successfully cloned DEAN repository" -ForegroundColor Green
            } else {
                throw "Git clone failed with exit code $LASTEXITCODE"
            }
        } else {
            throw "Git is not installed or not in PATH"
        }
    } catch {
        Write-Host "✗ Failed to clone repository: $_" -ForegroundColor Red
        exit 1
    }
}

# Step 3: Verify deployment scripts
Write-Host "`nStep 3: Verifying deployment scripts..." -ForegroundColor Yellow

$requiredScripts = @(
    @{Path="$stagingRepoPath\scripts\deployment_dry_run.ps1"; Desc="Deployment dry-run script"},
    @{Path="$stagingRepoPath\deploy_windows.ps1"; Desc="Windows deployment script"},
    @{Path="$stagingRepoPath\scripts\verify_deployment.ps1"; Desc="Deployment verification script"},
    @{Path="$stagingRepoPath\scripts\rollback_deployment.ps1"; Desc="Rollback script"}
)

$allScriptsPresent = $true
foreach ($script in $requiredScripts) {
    if (Test-Path $script.Path) {
        Write-Host "✓ Found: $($script.Desc)" -ForegroundColor Green
    } else {
        Write-Host "✗ Missing: $($script.Desc)" -ForegroundColor Red
        Write-Host "  Expected at: $($script.Path)" -ForegroundColor Gray
        $allScriptsPresent = $false
    }
}

# Check monitoring stack
$monitoringPath = "$stagingRepoPath\monitoring"
if (Test-Path "$monitoringPath\docker-compose.monitoring.yml") {
    Write-Host "✓ Found: Monitoring stack configuration" -ForegroundColor Green
} else {
    Write-Host "✗ Missing: Monitoring stack configuration" -ForegroundColor Red
    $allScriptsPresent = $false
}

# Step 4: Check Docker status
Write-Host "`nStep 4: Checking Docker status..." -ForegroundColor Yellow

try {
    $dockerVersion = docker version --format '{{.Server.Version}}' 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Docker is running (version $dockerVersion)" -ForegroundColor Green
        
        # Check Docker Compose
        $composeVersion = docker-compose version --short 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ Docker Compose is available (version $composeVersion)" -ForegroundColor Green
        } else {
            Write-Host "⚠ Docker Compose not found - may need to install separately" -ForegroundColor Yellow
        }
    } else {
        throw "Docker is not running"
    }
} catch {
    Write-Host "✗ Docker is not running or not installed" -ForegroundColor Red
    Write-Host "  Please ensure Docker Desktop is installed and running" -ForegroundColor Gray
}

# Step 5: Create environment file template
Write-Host "`nStep 5: Setting up environment configuration..." -ForegroundColor Yellow

$envTemplatePath = "$stagingRepoPath\.env.production.template"
$stagingEnvPath = "$stagingRepoPath\.env.staging"

if (Test-Path $envTemplatePath) {
    if (-not (Test-Path $stagingEnvPath)) {
        Copy-Item $envTemplatePath $stagingEnvPath
        Write-Host "✓ Created staging environment file from template" -ForegroundColor Green
        Write-Host "  ⚠ Remember to update credentials in: $stagingEnvPath" -ForegroundColor Yellow
    } else {
        Write-Host "✓ Staging environment file already exists" -ForegroundColor Gray
    }
} else {
    Write-Host "✗ Environment template not found at: $envTemplatePath" -ForegroundColor Red
}

# Summary
Write-Host "`n=== Initialization Summary ===" -ForegroundColor Cyan

if ($allScriptsPresent) {
    Write-Host "✅ All deployment scripts are present" -ForegroundColor Green
} else {
    Write-Host "❌ Some deployment scripts are missing" -ForegroundColor Red
}

Write-Host "`nNext Steps:" -ForegroundColor Yellow
Write-Host "1. Update credentials in: $stagingEnvPath" -ForegroundColor White
Write-Host "2. Run deployment dry-run: .\scripts\deployment_dry_run.ps1" -ForegroundColor White
Write-Host "3. Deploy to staging: .\deploy_windows.ps1 -Environment staging" -ForegroundColor White
Write-Host "4. Verify deployment: .\scripts\verify_deployment.ps1" -ForegroundColor White

Write-Host "`nDeployment Workflow:" -ForegroundColor Cyan
Write-Host "- Develop changes on MacBook" -ForegroundColor Gray
Write-Host "- Push to GitHub main branch" -ForegroundColor Gray
Write-Host "- Pull to C:\dean\staging\DEAN" -ForegroundColor Gray
Write-Host "- Run dry-run validation" -ForegroundColor Gray
Write-Host "- Deploy to staging" -ForegroundColor Gray
Write-Host "- Verify staging deployment" -ForegroundColor Gray
Write-Host "- Repeat for production" -ForegroundColor Gray
Write-Host "- Monitor for 15 minutes" -ForegroundColor Gray

Write-Host "`n✅ Deployment pipeline initialization complete!" -ForegroundColor Green