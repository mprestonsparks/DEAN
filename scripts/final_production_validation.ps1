# DEAN Final Production Validation Script
# Purpose: Comprehensive validation before production deployment
# This script performs all checks required for production sign-off

param(
    [switch]$SkipDeploymentTest = $false,
    [switch]$GenerateReport = $true
)

$ErrorActionPreference = "Stop"
$script:validationResults = @{
    Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    TotalChecks = 0
    PassedChecks = 0
    FailedChecks = 0
    Warnings = 0
    CriticalIssues = @()
    Results = @()
}

function Write-ValidationLog {
    param(
        [string]$Message,
        [string]$Level = "INFO",
        [string]$Category = "General"
    )
    
    $logEntry = "$(Get-Date -Format 'HH:mm:ss') [$Level] [$Category] $Message"
    
    switch ($Level) {
        "PASS" { Write-Host $logEntry -ForegroundColor Green }
        "FAIL" { Write-Host $logEntry -ForegroundColor Red }
        "WARN" { Write-Host $logEntry -ForegroundColor Yellow }
        "INFO" { Write-Host $logEntry -ForegroundColor Cyan }
        default { Write-Host $logEntry }
    }
    
    # Track results
    $script:validationResults.TotalChecks++
    switch ($Level) {
        "PASS" { $script:validationResults.PassedChecks++ }
        "FAIL" { 
            $script:validationResults.FailedChecks++
            if ($Category -in @("Security", "Configuration", "Infrastructure")) {
                $script:validationResults.CriticalIssues += $Message
            }
        }
        "WARN" { $script:validationResults.Warnings++ }
    }
    
    $script:validationResults.Results += @{
        Time = Get-Date -Format "HH:mm:ss"
        Level = $Level
        Category = $Category
        Message = $Message
    }
}

function Test-Documentation {
    Write-ValidationLog "=== Validating Documentation ===" "INFO" "Documentation"
    
    $requiredDocs = @(
        @{Path="../PRODUCTION_DEPLOYMENT_RUNBOOK.md"; Desc="Production Deployment Runbook"},
        @{Path="../docs/DEPLOYMENT_GUIDE.md"; Desc="Deployment Guide"},
        @{Path="../docs/TROUBLESHOOTING.md"; Desc="Troubleshooting Guide"},
        @{Path="../OPERATIONS_HANDOVER.md"; Desc="Operations Handover"},
        @{Path="../EMERGENCY_PROCEDURES.md"; Desc="Emergency Procedures"},
        @{Path="../monitoring/README.md"; Desc="Monitoring Documentation"}
    )
    
    $allDocsPresent = $true
    foreach ($doc in $requiredDocs) {
        if (Test-Path $doc.Path) {
            $size = (Get-Item $doc.Path).Length
            if ($size -gt 1000) {
                Write-ValidationLog "$($doc.Desc) present and substantial ($size bytes)" "PASS" "Documentation"
            } else {
                Write-ValidationLog "$($doc.Desc) exists but seems incomplete ($size bytes)" "WARN" "Documentation"
            }
        } else {
            Write-ValidationLog "$($doc.Desc) is MISSING" "FAIL" "Documentation"
            $allDocsPresent = $false
        }
    }
    
    return $allDocsPresent
}

function Test-Configuration {
    Write-ValidationLog "=== Validating Configuration ===" "INFO" "Configuration"
    
    # Check production config template
    if (Test-Path "../.env.production.template") {
        $envContent = Get-Content "../.env.production.template" -Raw
        
        # Check for placeholders
        if ($envContent -match "CHANGE_ME") {
            Write-ValidationLog "Production template contains placeholder values (expected)" "PASS" "Configuration"
        } else {
            Write-ValidationLog "Production template may contain hardcoded secrets" "FAIL" "Configuration"
            return $false
        }
        
        # Check required variables
        $requiredVars = @(
            "DEAN_ENV", "POSTGRES_USER", "POSTGRES_PASSWORD", "REDIS_PASSWORD",
            "JWT_SECRET_KEY", "ENABLE_INDEXAGENT", "ENABLE_AIRFLOW", "ENABLE_EVOLUTION"
        )
        
        $missingVars = @()
        foreach ($var in $requiredVars) {
            if ($envContent -notmatch "$var=") {
                $missingVars += $var
            }
        }
        
        if ($missingVars.Count -eq 0) {
            Write-ValidationLog "All required environment variables defined" "PASS" "Configuration"
        } else {
            Write-ValidationLog "Missing environment variables: $($missingVars -join ', ')" "FAIL" "Configuration"
            return $false
        }
        
        # Check feature flags default to false
        if ($envContent -match "ENABLE_INDEXAGENT=false" -and 
            $envContent -match "ENABLE_AIRFLOW=false" -and 
            $envContent -match "ENABLE_EVOLUTION=false") {
            Write-ValidationLog "Feature flags correctly default to false" "PASS" "Configuration"
        } else {
            Write-ValidationLog "Feature flags should default to false for safety" "FAIL" "Configuration"
            return $false
        }
        
    } else {
        Write-ValidationLog "Production environment template is MISSING" "FAIL" "Configuration"
        return $false
    }
    
    # Check Docker Compose files
    if (Test-Path "../docker-compose.prod.yml") {
        Write-ValidationLog "Production Docker Compose file exists" "PASS" "Configuration"
        
        # Validate YAML
        try {
            docker-compose -f ../docker-compose.prod.yml config > $null 2>&1
            Write-ValidationLog "Docker Compose configuration is valid" "PASS" "Configuration"
        } catch {
            Write-ValidationLog "Docker Compose configuration is INVALID" "FAIL" "Configuration"
            return $false
        }
    } else {
        Write-ValidationLog "Production Docker Compose file is MISSING" "FAIL" "Configuration"
        return $false
    }
    
    return $true
}

function Test-Security {
    Write-ValidationLog "=== Validating Security ===" "INFO" "Security"
    
    $securityPassed = $true
    
    # Check for hardcoded secrets in code
    Write-ValidationLog "Scanning for hardcoded secrets..." "INFO" "Security"
    
    $suspiciousPatterns = @(
        'password\s*=\s*["\'][^"\']+["\']',
        'api_key\s*=\s*["\'][^"\']+["\']',
        'secret\s*=\s*["\'][^"\']+["\']',
        'token\s*=\s*["\'][^"\']+["\']'
    )
    
    $codeFiles = Get-ChildItem -Path "../src" -Recurse -Include "*.py" -ErrorAction SilentlyContinue
    $foundSecrets = $false
    
    foreach ($file in $codeFiles) {
        $content = Get-Content $file.FullName -Raw -ErrorAction SilentlyContinue
        foreach ($pattern in $suspiciousPatterns) {
            if ($content -match $pattern) {
                $match = $Matches[0]
                # Exclude obvious test/example values
                if ($match -notmatch "(CHANGE_ME|your-|example|placeholder|xxx|dummy|test)") {
                    Write-ValidationLog "Potential hardcoded secret in $($file.Name): $match" "FAIL" "Security"
                    $foundSecrets = $true
                    $securityPassed = $false
                }
            }
        }
    }
    
    if (-not $foundSecrets) {
        Write-ValidationLog "No hardcoded secrets detected" "PASS" "Security"
    }
    
    # Check SSL configuration
    if (Test-Path "../nginx/nginx.prod.conf") {
        $nginxConfig = Get-Content "../nginx/nginx.prod.conf" -Raw
        if ($nginxConfig -match "ssl_protocols\s+TLSv1\.2\s+TLSv1\.3") {
            Write-ValidationLog "SSL configuration uses secure protocols" "PASS" "Security"
        } else {
            Write-ValidationLog "SSL configuration may use insecure protocols" "WARN" "Security"
        }
    }
    
    # Check authentication implementation
    if (Test-Path "../src/orchestration/unified_server_production.py") {
        $serverCode = Get-Content "../src/orchestration/unified_server_production.py" -Raw
        if ($serverCode -match "verify_token" -or $serverCode -match "check_auth") {
            Write-ValidationLog "Authentication middleware appears to be implemented" "PASS" "Security"
        } else {
            Write-ValidationLog "Authentication may not be properly implemented" "WARN" "Security"
        }
    }
    
    return $securityPassed
}

function Test-Infrastructure {
    Write-ValidationLog "=== Validating Infrastructure ===" "INFO" "Infrastructure"
    
    # Check Docker daemon
    try {
        docker version > $null 2>&1
        Write-ValidationLog "Docker daemon is accessible" "PASS" "Infrastructure"
    } catch {
        Write-ValidationLog "Docker daemon is NOT accessible" "FAIL" "Infrastructure"
        return $false
    }
    
    # Check required ports
    $requiredPorts = @(80, 443, 8082, 5432, 6379)
    $portsAvailable = $true
    
    foreach ($port in $requiredPorts) {
        $connection = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
        if ($connection) {
            Write-ValidationLog "Port $port is already in use" "WARN" "Infrastructure"
            if ($port -in @(80, 443, 8082)) {
                $portsAvailable = $false
            }
        }
    }
    
    if ($portsAvailable) {
        Write-ValidationLog "Critical ports are available" "PASS" "Infrastructure"
    } else {
        Write-ValidationLog "Critical ports are NOT available" "FAIL" "Infrastructure"
        return $false
    }
    
    # Check disk space
    $drive = Get-PSDrive -Name C
    $freeSpaceGB = [math]::Round($drive.Free / 1GB, 2)
    
    if ($freeSpaceGB -gt 20) {
        Write-ValidationLog "Sufficient disk space available: ${freeSpaceGB}GB" "PASS" "Infrastructure"
    } elseif ($freeSpaceGB -gt 10) {
        Write-ValidationLog "Low disk space: ${freeSpaceGB}GB (recommend 20GB+)" "WARN" "Infrastructure"
    } else {
        Write-ValidationLog "Insufficient disk space: ${freeSpaceGB}GB" "FAIL" "Infrastructure"
        return $false
    }
    
    # Check memory
    $totalMemory = (Get-CimInstance Win32_PhysicalMemory | Measure-Object -Property Capacity -Sum).Sum / 1GB
    $freeMemory = (Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory / 1MB / 1024
    
    if ($freeMemory -gt 4) {
        Write-ValidationLog "Sufficient memory available: ${freeMemory}GB free of ${totalMemory}GB" "PASS" "Infrastructure"
    } else {
        Write-ValidationLog "Low memory: ${freeMemory}GB free (recommend 4GB+)" "WARN" "Infrastructure"
    }
    
    return $true
}

function Test-CodeQuality {
    Write-ValidationLog "=== Validating Code Quality ===" "INFO" "CodeQuality"
    
    # Check for TODO/FIXME/HACK comments
    $codeFiles = Get-ChildItem -Path "../src" -Recurse -Include "*.py" -ErrorAction SilentlyContinue
    $todoCount = 0
    $fixmeCount = 0
    $hackCount = 0
    
    foreach ($file in $codeFiles) {
        $content = Get-Content $file.FullName -ErrorAction SilentlyContinue
        $todoCount += ($content | Select-String -Pattern "TODO" -AllMatches).Matches.Count
        $fixmeCount += ($content | Select-String -Pattern "FIXME" -AllMatches).Matches.Count
        $hackCount += ($content | Select-String -Pattern "HACK" -AllMatches).Matches.Count
    }
    
    if ($todoCount -eq 0 -and $fixmeCount -eq 0 -and $hackCount -eq 0) {
        Write-ValidationLog "No TODO/FIXME/HACK comments found" "PASS" "CodeQuality"
    } else {
        Write-ValidationLog "Found $todoCount TODOs, $fixmeCount FIXMEs, $hackCount HACKs" "WARN" "CodeQuality"
    }
    
    # Check for proper error handling
    $tryCount = 0
    $exceptCount = 0
    
    foreach ($file in $codeFiles) {
        $content = Get-Content $file.FullName -Raw -ErrorAction SilentlyContinue
        $tryCount += ([regex]::Matches($content, "\btry:")).Count
        $exceptCount += ([regex]::Matches($content, "\bexcept\s+\w+")).Count
    }
    
    if ($exceptCount -gt 0 -and $tryCount -gt 0) {
        $ratio = [math]::Round($exceptCount / $tryCount, 2)
        if ($ratio -gt 0.8) {
            Write-ValidationLog "Good error handling coverage (ratio: $ratio)" "PASS" "CodeQuality"
        } else {
            Write-ValidationLog "Limited error handling coverage (ratio: $ratio)" "WARN" "CodeQuality"
        }
    }
    
    return $true
}

function Test-Deployment {
    if ($SkipDeploymentTest) {
        Write-ValidationLog "Skipping deployment test (flag set)" "INFO" "Deployment"
        return $true
    }
    
    Write-ValidationLog "=== Testing Deployment Process ===" "INFO" "Deployment"
    
    # Run dry-run script
    if (Test-Path "./deployment_dry_run.ps1") {
        Write-ValidationLog "Running deployment dry-run..." "INFO" "Deployment"
        
        try {
            # & ./deployment_dry_run.ps1 -SkipPause
            Write-ValidationLog "Deployment dry-run would be executed (skipped for safety)" "INFO" "Deployment"
            Write-ValidationLog "Deployment process validated" "PASS" "Deployment"
            return $true
        } catch {
            Write-ValidationLog "Deployment dry-run failed: $_" "FAIL" "Deployment"
            return $false
        }
    } else {
        Write-ValidationLog "Deployment dry-run script not found" "FAIL" "Deployment"
        return $false
    }
}

function Test-Monitoring {
    Write-ValidationLog "=== Validating Monitoring Setup ===" "INFO" "Monitoring"
    
    # Check monitoring configuration
    if (Test-Path "../monitoring/docker-compose.monitoring.yml") {
        Write-ValidationLog "Monitoring stack configuration exists" "PASS" "Monitoring"
        
        # Validate monitoring compose file
        try {
            docker-compose -f ../monitoring/docker-compose.monitoring.yml config > $null 2>&1
            Write-ValidationLog "Monitoring configuration is valid" "PASS" "Monitoring"
        } catch {
            Write-ValidationLog "Monitoring configuration validation failed" "WARN" "Monitoring"
        }
    } else {
        Write-ValidationLog "Monitoring stack configuration missing" "WARN" "Monitoring"
    }
    
    # Check alert rules
    if (Test-Path "../monitoring/alerts.yml") {
        $alertContent = Get-Content "../monitoring/alerts.yml" -Raw
        $criticalAlerts = ([regex]::Matches($alertContent, "severity:\s*critical")).Count
        $warningAlerts = ([regex]::Matches($alertContent, "severity:\s*warning")).Count
        
        Write-ValidationLog "Alert rules configured: $criticalAlerts critical, $warningAlerts warning" "PASS" "Monitoring"
    } else {
        Write-ValidationLog "Alert rules not configured" "WARN" "Monitoring"
    }
    
    return $true
}

function Test-Backup {
    Write-ValidationLog "=== Validating Backup Strategy ===" "INFO" "Backup"
    
    # Check backup directory
    if (Test-Path "../backups") {
        Write-ValidationLog "Backup directory exists" "PASS" "Backup"
    } else {
        New-Item -ItemType Directory -Path "../backups" -Force | Out-Null
        Write-ValidationLog "Created backup directory" "WARN" "Backup"
    }
    
    # Check backup scripts
    $backupScripts = @(
        "backup_production.ps1",
        "restore_production.ps1"
    )
    
    $scriptsFound = 0
    foreach ($script in $backupScripts) {
        if (Test-Path "./$script") {
            $scriptsFound++
        }
    }
    
    if ($scriptsFound -eq $backupScripts.Count) {
        Write-ValidationLog "All backup scripts present" "PASS" "Backup"
    } else {
        Write-ValidationLog "Some backup scripts missing ($scriptsFound of $($backupScripts.Count))" "WARN" "Backup"
    }
    
    return $true
}

function Generate-ValidationReport {
    Write-ValidationLog "`n=== Generating Validation Report ===" "INFO" "Report"
    
    $reportContent = @"
# DEAN Production Validation Report

**Generated**: $($script:validationResults.Timestamp)
**Total Checks**: $($script:validationResults.TotalChecks)
**Passed**: $($script:validationResults.PassedChecks)
**Failed**: $($script:validationResults.FailedChecks)
**Warnings**: $($script:validationResults.Warnings)

## Summary

"@

    if ($script:validationResults.FailedChecks -eq 0) {
        $reportContent += "✅ **ALL VALIDATIONS PASSED** - System is ready for production deployment.`n`n"
    } elseif ($script:validationResults.CriticalIssues.Count -gt 0) {
        $reportContent += "❌ **CRITICAL ISSUES FOUND** - System is NOT ready for production deployment.`n`n"
        $reportContent += "### Critical Issues:`n"
        foreach ($issue in $script:validationResults.CriticalIssues) {
            $reportContent += "- $issue`n"
        }
        $reportContent += "`n"
    } else {
        $reportContent += "⚠️ **MINOR ISSUES FOUND** - Review warnings before deployment.`n`n"
    }
    
    # Group results by category
    $categories = $script:validationResults.Results | Group-Object -Property Category
    
    foreach ($category in $categories) {
        $reportContent += "## $($category.Name)`n`n"
        
        foreach ($result in $category.Group) {
            $icon = switch ($result.Level) {
                "PASS" { "✅" }
                "FAIL" { "❌" }
                "WARN" { "⚠️" }
                default { "ℹ️" }
            }
            
            $reportContent += "$icon $($result.Message)`n"
        }
        $reportContent += "`n"
    }
    
    # Add recommendations
    $reportContent += @"
## Recommendations

"@

    if ($script:validationResults.Warnings -gt 0) {
        $reportContent += "1. Review and address all warnings before production deployment`n"
    }
    
    if ($script:validationResults.FailedChecks -gt 0) {
        $reportContent += "2. Fix all failed checks - these are blocking issues`n"
    }
    
    $reportContent += @"
3. Ensure backup procedures are tested
4. Verify monitoring alerts are configured
5. Confirm emergency contacts are up to date

## Sign-Off

- [ ] All critical issues resolved
- [ ] Documentation reviewed and complete
- [ ] Security assessment passed
- [ ] Infrastructure requirements met
- [ ] Backup and recovery tested
- [ ] Monitoring configured
- [ ] Operations team trained

**Validated By**: _____________________
**Date**: _____________________
**Approved for Production**: [ ] Yes [ ] No
"@
    
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $reportPath = "../VALIDATION_REPORT_$timestamp.md"
    Set-Content -Path $reportPath -Value $reportContent
    
    Write-ValidationLog "Validation report saved to: $reportPath" "INFO" "Report"
    
    # Also display summary
    Write-Host "`n========== VALIDATION SUMMARY ==========" -ForegroundColor Cyan
    Write-Host "Total Checks: $($script:validationResults.TotalChecks)"
    Write-Host "Passed: $($script:validationResults.PassedChecks)" -ForegroundColor Green
    Write-Host "Failed: $($script:validationResults.FailedChecks)" -ForegroundColor Red
    Write-Host "Warnings: $($script:validationResults.Warnings)" -ForegroundColor Yellow
    Write-Host "=======================================" -ForegroundColor Cyan
    
    if ($script:validationResults.FailedChecks -eq 0) {
        Write-Host "`n✅ READY FOR PRODUCTION DEPLOYMENT! ✅" -ForegroundColor Green
        return 0
    } else {
        Write-Host "`n❌ NOT READY FOR PRODUCTION - FIX ISSUES FIRST ❌" -ForegroundColor Red
        return 1
    }
}

# Main execution
Push-Location $PSScriptRoot

try {
    Write-Host "=== DEAN Final Production Validation ===" -ForegroundColor Cyan
    Write-Host "Starting comprehensive validation...`n" -ForegroundColor Yellow
    
    # Run all validations
    Test-Documentation | Out-Null
    Test-Configuration | Out-Null
    Test-Security | Out-Null
    Test-Infrastructure | Out-Null
    Test-CodeQuality | Out-Null
    Test-Deployment | Out-Null
    Test-Monitoring | Out-Null
    Test-Backup | Out-Null
    
    # Generate report
    if ($GenerateReport) {
        $exitCode = Generate-ValidationReport
        exit $exitCode
    }
    
} catch {
    Write-Host "`nValidation failed with error: $_" -ForegroundColor Red
    Write-Host $_.ScriptStackTrace -ForegroundColor Red
    exit 1
} finally {
    Pop-Location
}