# DEAN Monitoring Stack Deployment Script
# Purpose: Deploy Prometheus, Grafana, and related monitoring tools
# Usage: ./deploy_monitoring.ps1 [-Action deploy|stop|status]

param(
    [ValidateSet("deploy", "stop", "status", "logs")]
    [string]$Action = "deploy"
)

$ErrorActionPreference = "Stop"

function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    Write-Host $Message -ForegroundColor $Color
}

function Test-Prerequisites {
    Write-ColorOutput "`n=== Checking Prerequisites ===" "Cyan"
    
    # Check Docker
    try {
        docker version | Out-Null
        Write-ColorOutput "✓ Docker is installed and running" "Green"
    } catch {
        Write-ColorOutput "✗ Docker is not running or not installed" "Red"
        return $false
    }
    
    # Check if DEAN network exists
    $networks = docker network ls --format "{{.Name}}"
    if ($networks -contains "dean_dean-net") {
        Write-ColorOutput "✓ DEAN network exists" "Green"
    } else {
        Write-ColorOutput "⚠ DEAN network not found, creating..." "Yellow"
        docker network create dean_dean-net
    }
    
    # Check environment file
    if (Test-Path "../.env") {
        Write-ColorOutput "✓ Environment file found" "Green"
    } else {
        Write-ColorOutput "⚠ Environment file not found at ../.env" "Yellow"
        Write-ColorOutput "  Please ensure database credentials are set" "Yellow"
    }
    
    return $true
}

function Deploy-MonitoringStack {
    Write-ColorOutput "`n=== Deploying Monitoring Stack ===" "Cyan"
    
    # Copy environment file if exists
    if (Test-Path "../.env") {
        Copy-Item "../.env" ".env" -Force
        Write-ColorOutput "✓ Environment file copied" "Green"
    }
    
    # Deploy the stack
    Write-ColorOutput "Starting monitoring services..." "Yellow"
    docker-compose -f docker-compose.monitoring.yml up -d
    
    if ($LASTEXITCODE -eq 0) {
        Write-ColorOutput "✓ Monitoring stack deployed successfully" "Green"
        
        # Wait for services to be ready
        Write-ColorOutput "`nWaiting for services to be ready..." "Yellow"
        Start-Sleep -Seconds 10
        
        # Show access URLs
        Write-ColorOutput "`n=== Access URLs ===" "Cyan"
        Write-ColorOutput "Prometheus: http://localhost:9090" "White"
        Write-ColorOutput "Grafana: http://localhost:3000 (admin/admin)" "White"
        Write-ColorOutput "Alertmanager: http://localhost:9093" "White"
        
        # Show container status
        Show-MonitoringStatus
    } else {
        Write-ColorOutput "✗ Failed to deploy monitoring stack" "Red"
        return $false
    }
    
    return $true
}

function Stop-MonitoringStack {
    Write-ColorOutput "`n=== Stopping Monitoring Stack ===" "Cyan"
    
    docker-compose -f docker-compose.monitoring.yml down
    
    if ($LASTEXITCODE -eq 0) {
        Write-ColorOutput "✓ Monitoring stack stopped" "Green"
    } else {
        Write-ColorOutput "✗ Failed to stop monitoring stack" "Red"
        return $false
    }
    
    return $true
}

function Show-MonitoringStatus {
    Write-ColorOutput "`n=== Monitoring Stack Status ===" "Cyan"
    
    $containers = @(
        "dean-prometheus",
        "dean-grafana",
        "dean-alertmanager",
        "dean-node-exporter",
        "dean-cadvisor",
        "dean-postgres-exporter",
        "dean-redis-exporter",
        "dean-loki",
        "dean-promtail"
    )
    
    foreach ($container in $containers) {
        $status = docker ps --filter "name=$container" --format "table {{.Status}}" | Select-Object -Skip 1
        if ($status) {
            Write-ColorOutput "✓ $container`: $status" "Green"
        } else {
            Write-ColorOutput "✗ $container`: Not running" "Red"
        }
    }
}

function Show-MonitoringLogs {
    Write-ColorOutput "`n=== Recent Monitoring Logs ===" "Cyan"
    
    $containers = @("dean-prometheus", "dean-grafana", "dean-alertmanager")
    
    foreach ($container in $containers) {
        Write-ColorOutput "`n--- $container logs ---" "Yellow"
        docker logs $container --tail 10 2>&1 | ForEach-Object {
            if ($_ -match "error|fail|warn") {
                Write-ColorOutput $_ "Red"
            } else {
                Write-Host $_
            }
        }
    }
}

function Test-MonitoringEndpoints {
    Write-ColorOutput "`n=== Testing Monitoring Endpoints ===" "Cyan"
    
    $endpoints = @(
        @{Name="Prometheus"; Url="http://localhost:9090/-/healthy"},
        @{Name="Grafana"; Url="http://localhost:3000/api/health"},
        @{Name="Alertmanager"; Url="http://localhost:9093/-/healthy"},
        @{Name="Loki"; Url="http://localhost:3100/ready"}
    )
    
    foreach ($endpoint in $endpoints) {
        try {
            $response = Invoke-WebRequest -Uri $endpoint.Url -TimeoutSec 5 -ErrorAction Stop
            if ($response.StatusCode -eq 200) {
                Write-ColorOutput "✓ $($endpoint.Name) is healthy" "Green"
            }
        } catch {
            Write-ColorOutput "✗ $($endpoint.Name) is not responding" "Red"
        }
    }
}

# Main execution
Push-Location $PSScriptRoot

try {
    switch ($Action) {
        "deploy" {
            if (Test-Prerequisites) {
                if (Deploy-MonitoringStack) {
                    Test-MonitoringEndpoints
                    Write-ColorOutput "`n✓ Monitoring deployment completed successfully!" "Green"
                }
            }
        }
        
        "stop" {
            Stop-MonitoringStack
        }
        
        "status" {
            Show-MonitoringStatus
            Test-MonitoringEndpoints
        }
        
        "logs" {
            Show-MonitoringLogs
        }
    }
} catch {
    Write-ColorOutput "`nError: $_" "Red"
    Write-ColorOutput $_.ScriptStackTrace "Red"
    exit 1
} finally {
    Pop-Location
}