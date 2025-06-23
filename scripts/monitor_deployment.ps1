# DEAN Deployment Monitoring Script
# Purpose: Monitor deployment health for specified duration
# Usage: .\monitor_deployment.ps1 [-Duration 15] [-Environment production]

param(
    [int]$Duration = 15,  # Duration in minutes
    [ValidateSet("staging", "production")]
    [string]$Environment = "production",
    [switch]$ShowLogs = $false
)

$ErrorActionPreference = "Stop"

Write-Host "=== DEAN Deployment Monitoring ===" -ForegroundColor Cyan
Write-Host "Environment: $Environment" -ForegroundColor Yellow
Write-Host "Duration: $Duration minutes" -ForegroundColor Yellow
Write-Host "Started: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Gray
Write-Host ""

# Initialize monitoring data
$monitoringData = @{
    StartTime = Get-Date
    EndTime = (Get-Date).AddMinutes($Duration)
    Checks = @()
    Errors = 0
    Warnings = 0
    HealthyChecks = 0
    TotalChecks = 0
}

# Health check function
function Test-ServiceHealth {
    $result = @{
        Timestamp = Get-Date
        Healthy = $false
        ResponseTime = 0
        Services = @{}
        Errors = @()
    }
    
    # Check orchestrator health
    try {
        $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
        $health = Invoke-RestMethod -Uri "http://localhost:8082/health" -TimeoutSec 5
        $stopwatch.Stop()
        
        $result.ResponseTime = $stopwatch.ElapsedMilliseconds
        $result.Healthy = ($health.status -eq "healthy")
        
        # Check service status
        try {
            $services = Invoke-RestMethod -Uri "http://localhost:8082/api/v1/services/status" -TimeoutSec 5
            foreach ($service in $services.services) {
                $result.Services[$service.name] = $service.status
            }
        } catch {
            $result.Errors += "Failed to get service status"
        }
        
    } catch {
        $result.Healthy = $false
        $result.Errors += "Health check failed: $_"
    }
    
    return $result
}

# Container status function
function Get-ContainerStatus {
    $containers = @{}
    
    try {
        $runningContainers = docker ps --format "{{.Names}}|{{.Status}}|{{.CreatedAt}}" 2>$null
        
        foreach ($line in $runningContainers) {
            if ($line) {
                $parts = $line -split '\|'
                if ($parts.Count -ge 2) {
                    $containers[$parts[0]] = @{
                        Status = $parts[1]
                        Created = $parts[2]
                    }
                }
            }
        }
    } catch {
        Write-Host "⚠ Failed to get container status" -ForegroundColor Yellow
    }
    
    return $containers
}

# Resource usage function
function Get-ResourceUsage {
    $usage = @{
        CPU = @{}
        Memory = @{}
    }
    
    try {
        $stats = docker stats --no-stream --format "json" 2>$null | ConvertFrom-Json
        
        foreach ($stat in $stats) {
            $usage.CPU[$stat.Name] = $stat.CPUPerc
            $usage.Memory[$stat.Name] = $stat.MemUsage
        }
    } catch {
        # Stats collection failed
    }
    
    return $usage
}

# Main monitoring loop
$checkInterval = 30  # seconds
$checksPerMinute = 60 / $checkInterval
$totalIterations = $Duration * $checksPerMinute

Write-Host "Monitoring every $checkInterval seconds for $Duration minutes..." -ForegroundColor Gray
Write-Host "Press Ctrl+C to stop monitoring early" -ForegroundColor Gray
Write-Host ""

# Create log file
$logFile = "monitoring_$Environment_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"

try {
    for ($i = 1; $i -le $totalIterations; $i++) {
        $iterationStart = Get-Date
        
        # Clear previous output for clean display
        if ($i -gt 1 -and -not $ShowLogs) {
            Clear-Host
            Write-Host "=== DEAN Deployment Monitoring ===" -ForegroundColor Cyan
            Write-Host "Environment: $Environment | Check $i of $totalIterations" -ForegroundColor Yellow
            Write-Host ""
        }
        
        # Perform health check
        $healthResult = Test-ServiceHealth
        $monitoringData.TotalChecks++
        
        if ($healthResult.Healthy) {
            $monitoringData.HealthyChecks++
            Write-Host "✓ Health Check PASSED" -ForegroundColor Green -NoNewline
            Write-Host " (Response: $($healthResult.ResponseTime)ms)" -ForegroundColor Gray
        } else {
            $monitoringData.Errors++
            Write-Host "✗ Health Check FAILED" -ForegroundColor Red
            foreach ($error in $healthResult.Errors) {
                Write-Host "  - $error" -ForegroundColor Red
            }
        }
        
        # Get container status
        Write-Host "`nContainer Status:" -ForegroundColor Cyan
        $containers = Get-ContainerStatus
        
        $expectedContainers = @("dean-orchestrator", "dean-postgres", "dean-redis", "dean-nginx")
        foreach ($container in $expectedContainers) {
            if ($containers.ContainsKey($container)) {
                $status = $containers[$container].Status
                if ($status -match "Up") {
                    Write-Host "  ✓ $container`: $status" -ForegroundColor Green
                } else {
                    Write-Host "  ⚠ $container`: $status" -ForegroundColor Yellow
                    $monitoringData.Warnings++
                }
            } else {
                Write-Host "  ✗ $container`: Not running" -ForegroundColor Red
                $monitoringData.Errors++
            }
        }
        
        # Get resource usage
        $resources = Get-ResourceUsage
        if ($resources.CPU.Count -gt 0) {
            Write-Host "`nResource Usage:" -ForegroundColor Cyan
            foreach ($container in $resources.CPU.Keys) {
                $cpu = $resources.CPU[$container]
                $mem = $resources.Memory[$container]
                
                $cpuValue = [double]($cpu -replace '%', '')
                $cpuColor = if ($cpuValue -gt 80) { "Red" } elseif ($cpuValue -gt 60) { "Yellow" } else { "Gray" }
                
                Write-Host "  $container`:" -NoNewline
                Write-Host " CPU $cpu" -ForegroundColor $cpuColor -NoNewline
                Write-Host " | MEM $mem" -ForegroundColor Gray
            }
        }
        
        # Log to file
        $logEntry = @{
            Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
            Iteration = $i
            HealthCheck = $healthResult
            Containers = $containers
            Resources = $resources
        }
        $logEntry | ConvertTo-Json -Depth 10 | Add-Content -Path $logFile
        
        # Show recent logs if requested
        if ($ShowLogs) {
            Write-Host "`nRecent Logs:" -ForegroundColor Cyan
            docker logs dean-orchestrator --tail 5 --since 30s 2>&1 | ForEach-Object {
                if ($_ -match "ERROR") {
                    Write-Host "  $_" -ForegroundColor Red
                } elseif ($_ -match "WARNING") {
                    Write-Host "  $_" -ForegroundColor Yellow
                } else {
                    Write-Host "  $_" -ForegroundColor Gray
                }
            }
        }
        
        # Calculate remaining time
        $elapsed = (Get-Date) - $monitoringData.StartTime
        $remaining = $monitoringData.EndTime - (Get-Date)
        
        Write-Host "`nMonitoring Status:" -ForegroundColor Cyan
        Write-Host "  Elapsed: $([int]$elapsed.TotalMinutes) min $([int]$elapsed.Seconds % 60) sec" -ForegroundColor Gray
        Write-Host "  Remaining: $([int]$remaining.TotalMinutes) min $([int]$remaining.Seconds % 60) sec" -ForegroundColor Gray
        Write-Host "  Health: $($monitoringData.HealthyChecks)/$($monitoringData.TotalChecks) checks passed" -ForegroundColor Gray
        
        if ($monitoringData.Errors -gt 0) {
            Write-Host "  Errors: $($monitoringData.Errors)" -ForegroundColor Red
        }
        if ($monitoringData.Warnings -gt 0) {
            Write-Host "  Warnings: $($monitoringData.Warnings)" -ForegroundColor Yellow
        }
        
        # Alert on critical issues
        if ($monitoringData.Errors -gt 5) {
            Write-Host "`n⚠️  ALERT: Multiple errors detected!" -ForegroundColor Red -BackgroundColor DarkRed
            Write-Host "Consider investigating the deployment" -ForegroundColor Yellow
        }
        
        # Wait for next iteration
        $iterationDuration = (Get-Date) - $iterationStart
        $sleepTime = [Math]::Max(0, $checkInterval - $iterationDuration.TotalSeconds)
        
        if ($i -lt $totalIterations) {
            Start-Sleep -Seconds $sleepTime
        }
    }
} catch {
    Write-Host "`nMonitoring interrupted: $_" -ForegroundColor Yellow
} finally {
    # Final summary
    Write-Host "`n=== Monitoring Summary ===" -ForegroundColor Cyan
    Write-Host "Duration: $([int]((Get-Date) - $monitoringData.StartTime).TotalMinutes) minutes" -ForegroundColor Gray
    Write-Host "Total Checks: $($monitoringData.TotalChecks)" -ForegroundColor Gray
    Write-Host "Successful: $($monitoringData.HealthyChecks)" -ForegroundColor Green
    Write-Host "Failed: $($monitoringData.TotalChecks - $monitoringData.HealthyChecks)" -ForegroundColor Red
    Write-Host "Errors: $($monitoringData.Errors)" -ForegroundColor Red
    Write-Host "Warnings: $($monitoringData.Warnings)" -ForegroundColor Yellow
    
    $successRate = if ($monitoringData.TotalChecks -gt 0) {
        [Math]::Round(($monitoringData.HealthyChecks / $monitoringData.TotalChecks) * 100, 2)
    } else { 0 }
    
    Write-Host "`nHealth Success Rate: $successRate%" -ForegroundColor $(if ($successRate -ge 95) { "Green" } elseif ($successRate -ge 80) { "Yellow" } else { "Red" })
    
    Write-Host "`nDetailed logs saved to: $logFile" -ForegroundColor Cyan
    
    # Recommendations
    if ($successRate -lt 95) {
        Write-Host "`nRecommendations:" -ForegroundColor Yellow
        Write-Host "- Check container logs: docker-compose -f docker-compose.prod.yml logs" -ForegroundColor Gray
        Write-Host "- Verify resource allocation is sufficient" -ForegroundColor Gray
        Write-Host "- Review error patterns in monitoring log" -ForegroundColor Gray
    } else {
        Write-Host "`n✅ Deployment appears stable and healthy!" -ForegroundColor Green
    }
}