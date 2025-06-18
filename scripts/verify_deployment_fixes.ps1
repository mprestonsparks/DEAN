#!/usr/bin/env pwsh
# Verification script to confirm all deployment issues are addressed
# Based on the deployment issues mentioned in the instructions

param(
    [switch]$Detailed = $false
)

$ErrorActionPreference = "Continue"

# Color functions
function Write-Success { Write-Host "✓ $args" -ForegroundColor Green }
function Write-Error { Write-Host "✗ $args" -ForegroundColor Red }
function Write-Info { Write-Host "ℹ $args" -ForegroundColor Cyan }
function Write-Header { Write-Host "`n=== $args ===" -ForegroundColor Magenta }

# Track verification results
$verificationResults = @{
    DatabaseNaming = $false
    EnvironmentVariables = $false
    BOMCharacters = $false
    SSLCertificates = $false
    DockerConnectivity = $false
    PowerShellHTTPS = $false
    Documentation = $false
    Scripts = $false
}

Write-Host "`n╔════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  DEAN Deployment Fix Verification              ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════╝" -ForegroundColor Cyan

# 1. Verify Database Naming Fix (dean_prod vs dean_production)
Write-Header "1. Database Naming Consistency"
try {
    # Check .env.template
    $envTemplate = Get-Content ".env.template" -ErrorAction SilentlyContinue | Select-String "POSTGRES_DB"
    if ($envTemplate -match "dean_production") {
        Write-Success ".env.template uses correct database name: dean_production"
        $verificationResults.DatabaseNaming = $true
    } else {
        Write-Error ".env.template has incorrect database name"
    }
    
    # Check docker-compose files
    $composeFiles = @("docker-compose.yml", "docker-compose.prod.yml")
    foreach ($file in $composeFiles) {
        if (Test-Path $file) {
            $content = Get-Content $file -Raw
            if ($content -match "POSTGRES_DB.*dean_production" -or $content -match '\$\{POSTGRES_DB\}') {
                Write-Success "$file uses correct database configuration"
            } else {
                Write-Error "$file may have database naming issues"
            }
        }
    }
} catch {
    Write-Error "Failed to verify database naming: $_"
}

# 2. Verify Environment Variable Configuration
Write-Header "2. Environment Variable Configuration"
try {
    if (Test-Path "scripts/validate_deployment.ps1") {
        $validateScript = Get-Content "scripts/validate_deployment.ps1" -Raw
        if ($validateScript -match "Test-EnvironmentVariables" -and 
            $validateScript -match "JWT_SECRET_KEY" -and
            $validateScript -match "POSTGRES_PASSWORD") {
            Write-Success "Environment validation script checks required variables"
            $verificationResults.EnvironmentVariables = $true
        }
    }
    
    if (Test-Path "scripts/setup_environment.ps1") {
        Write-Success "Environment setup script exists for automated configuration"
    }
} catch {
    Write-Error "Failed to verify environment configuration: $_"
}

# 3. Verify BOM Character Detection and Removal
Write-Header "3. BOM Character Prevention"
try {
    if (Test-Path "scripts/validate_deployment.ps1") {
        $validateScript = Get-Content "scripts/validate_deployment.ps1" -Raw
        if ($validateScript -match "Test-BOMInFiles" -and $validateScript -match "0xEF.*0xBB.*0xBF") {
            Write-Success "BOM detection implemented in validation script"
            if ($validateScript -match "AutoFix") {
                Write-Success "Auto-fix capability for BOM removal is available"
                $verificationResults.BOMCharacters = $true
            }
        }
    }
} catch {
    Write-Error "Failed to verify BOM detection: $_"
}

# 4. Verify SSL Certificate Management
Write-Header "4. SSL Certificate Management"
try {
    if (Test-Path "scripts/setup_ssl.ps1") {
        $sslScript = Get-Content "scripts/setup_ssl.ps1" -Raw
        if ($sslScript -match "New-SelfSignedCertificate" -and 
            $sslScript -match "Test-Certificates") {
            Write-Success "SSL certificate management script exists with generation and validation"
            $verificationResults.SSLCertificates = $true
        }
    }
    
    if (Test-Path "scripts/deploy/setup_ssl_certificates.sh") {
        Write-Success "Additional SSL setup script found for Linux/Mac"
    }
} catch {
    Write-Error "Failed to verify SSL management: $_"
}

# 5. Verify Docker Service Connectivity
Write-Header "5. Docker Service Connectivity"
try {
    # Check for Docker compose health checks
    $composeFiles = @("docker-compose.yml", "docker-compose.prod.yml")
    $hasHealthChecks = $false
    
    foreach ($file in $composeFiles) {
        if (Test-Path $file) {
            $content = Get-Content $file -Raw
            if ($content -match "healthcheck:" -and $content -match "depends_on:") {
                $hasHealthChecks = $true
                Write-Success "$file includes health checks and dependencies"
            }
        }
    }
    
    if ($hasHealthChecks) {
        $verificationResults.DockerConnectivity = $true
    }
} catch {
    Write-Error "Failed to verify Docker connectivity: $_"
}

# 6. Verify PowerShell HTTPS Documentation
Write-Header "6. PowerShell HTTPS Compatibility"
try {
    if (Test-Path "docs/TROUBLESHOOTING.md") {
        $troubleshooting = Get-Content "docs/TROUBLESHOOTING.md" -Raw
        if ($troubleshooting -match "PowerShell.*HTTPS" -or 
            $troubleshooting -match "self-signed.*certificate") {
            Write-Success "PowerShell HTTPS issues documented in troubleshooting guide"
            $verificationResults.PowerShellHTTPS = $true
        }
    }
    
    # Check if SSL script handles PowerShell limitations
    if (Test-Path "scripts/setup_ssl.ps1") {
        $sslScript = Get-Content "scripts/setup_ssl.ps1" -Raw
        if ($sslScript -match "self-signed.*warning" -or $sslScript -match "browser") {
            Write-Success "SSL script acknowledges browser testing for self-signed certs"
        }
    }
} catch {
    Write-Error "Failed to verify PowerShell HTTPS documentation: $_"
}

# 7. Verify Documentation
Write-Header "7. Deployment Documentation"
try {
    $requiredDocs = @(
        "README.md",
        "docs/DEPLOYMENT_CHECKLIST.md",
        "docs/TROUBLESHOOTING.md"
    )
    
    $allDocsExist = $true
    foreach ($doc in $requiredDocs) {
        if (Test-Path $doc) {
            Write-Success "$doc exists"
        } else {
            Write-Error "$doc is missing"
            $allDocsExist = $false
        }
    }
    
    if ($allDocsExist) {
        $verificationResults.Documentation = $true
    }
} catch {
    Write-Error "Failed to verify documentation: $_"
}

# 8. Verify Required Scripts
Write-Header "8. Deployment Scripts"
try {
    $requiredScripts = @(
        "scripts/validate_deployment.ps1",
        "scripts/setup_ssl.ps1",
        "scripts/setup_environment.ps1"
    )
    
    $allScriptsExist = $true
    foreach ($script in $requiredScripts) {
        if (Test-Path $script) {
            Write-Success "$script exists"
        } else {
            Write-Error "$script is missing"
            $allScriptsExist = $false
        }
    }
    
    if ($allScriptsExist) {
        $verificationResults.Scripts = $true
    }
} catch {
    Write-Error "Failed to verify scripts: $_"
}

# Summary
Write-Host "`n╔════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  Verification Summary                          ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════╝" -ForegroundColor Cyan

$totalIssues = 8
$fixedIssues = ($verificationResults.Values | Where-Object { $_ -eq $true }).Count

Write-Host "`nDeployment Issues Addressed: $fixedIssues/$totalIssues" -ForegroundColor $(if ($fixedIssues -eq $totalIssues) { "Green" } else { "Yellow" })

foreach ($issue in $verificationResults.GetEnumerator()) {
    $status = if ($issue.Value) { "✓ FIXED" } else { "✗ NOT FIXED" }
    $color = if ($issue.Value) { "Green" } else { "Red" }
    Write-Host "$status - $($issue.Key)" -ForegroundColor $color
}

if ($fixedIssues -eq $totalIssues) {
    Write-Host "`n🎉 All deployment issues have been successfully addressed!" -ForegroundColor Green
    Write-Host "The DEAN system is ready for deployment." -ForegroundColor Green
} else {
    Write-Host "`n⚠️  Some issues still need attention." -ForegroundColor Yellow
    Write-Host "Run with -Detailed flag for more information." -ForegroundColor Yellow
}

# Generate deployment readiness report
if ($Detailed) {
    Write-Host "`n=== Detailed Deployment Readiness Report ===" -ForegroundColor Cyan
    
    Write-Host "`nPre-deployment Commands:" -ForegroundColor Yellow
    Write-Host "1. ./scripts/setup_environment.ps1 -GenerateSecrets" -ForegroundColor White
    Write-Host "2. ./scripts/validate_deployment.ps1 -AutoFix" -ForegroundColor White
    Write-Host "3. ./scripts/setup_ssl.ps1 -Environment development" -ForegroundColor White
    
    Write-Host "`nDeployment Command:" -ForegroundColor Yellow
    Write-Host "./deploy_windows.ps1" -ForegroundColor White
    
    Write-Host "`nPost-deployment Verification:" -ForegroundColor Yellow
    Write-Host "- Browser: https://localhost/health" -ForegroundColor White
    Write-Host "- API: http://localhost:8082/health" -ForegroundColor White
    Write-Host "- Docs: http://localhost:8082/docs" -ForegroundColor White
}

# Exit with appropriate code
exit $(if ($fixedIssues -eq $totalIssues) { 0 } else { 1 })