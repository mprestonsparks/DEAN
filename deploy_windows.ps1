# DEAN Windows Deployment Script
# Requires PowerShell 7+ and Docker Desktop

param(
    [Parameter(Mandatory=$false)]
    [string]$Environment = "production",
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipValidation = $false,
    
    [Parameter(Mandatory=$false)]
    [switch]$Verbose = $false
)

Write-Host "DEAN Deployment Script for Windows" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host "Version: 1.0.0" -ForegroundColor Gray
Write-Host ""

# Check prerequisites
function Test-Prerequisites {
    Write-Host "Checking prerequisites..." -ForegroundColor Yellow
    
    $errors = @()
    
    # Check Docker
    try {
        $dockerVersion = docker version --format '{{.Server.Version}}' 2>$null
        if ($dockerVersion) {
            Write-Host "✓ Docker Desktop detected (version $dockerVersion)" -ForegroundColor Green
        } else {
            $errors += "Docker Desktop not running"
        }
    } catch {
        $errors += "Docker Desktop not installed or not in PATH"
    }
    
    # Check Docker Compose
    try {
        $composeVersion = docker-compose version --short 2>$null
        if ($composeVersion) {
            Write-Host "✓ Docker Compose detected (version $composeVersion)" -ForegroundColor Green
        } else {
            $errors += "Docker Compose not available"
        }
    } catch {
        $errors += "Docker Compose not found"
    }
    
    # Check WSL2
    try {
        $wslStatus = wsl --status 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ WSL2 detected" -ForegroundColor Green
        } else {
            $errors += "WSL2 not properly configured"
        }
    } catch {
        $errors += "WSL2 not installed"
    }
    
    # Check Python (optional but recommended)
    try {
        $pythonVersion = python --version 2>$null
        if ($pythonVersion) {
            Write-Host "✓ Python detected ($pythonVersion)" -ForegroundColor Green
        } else {
            Write-Host "⚠ Python not found (optional)" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "⚠ Python not found (optional)" -ForegroundColor Yellow
    }
    
    # Check if .env exists
    if (Test-Path ".env") {
        Write-Host "✓ Environment configuration found" -ForegroundColor Green
    } else {
        if (Test-Path ".env.production.template") {
            Write-Host "⚠ .env not found, but template exists" -ForegroundColor Yellow
            Write-Host "  Run: Copy-Item .env.production.template .env" -ForegroundColor Gray
        } else {
            $errors += ".env.production.template not found"
        }
    }
    
    if ($errors.Count -gt 0) {
        Write-Host "`nErrors found:" -ForegroundColor Red
        $errors | ForEach-Object { Write-Host "  ✗ $_" -ForegroundColor Red }
        exit 1
    }
    
    Write-Host "`nAll prerequisites satisfied\!" -ForegroundColor Green
}

# Validate configuration
function Test-Configuration {
    if (-not $SkipValidation) {
        Write-Host "`nValidating configuration..." -ForegroundColor Yellow
        
        if (Test-Path "scripts/validate_config.py") {
            python scripts/validate_config.py
            if ($LASTEXITCODE -ne 0) {
                Write-Host "✗ Configuration validation failed" -ForegroundColor Red
                Write-Host "  Please check your .env file" -ForegroundColor Gray
                exit 1
            }
        } else {
            Write-Host "⚠ Validation script not found, skipping" -ForegroundColor Yellow
        }
    }
}

# Create required directories
function Initialize-Directories {
    Write-Host "`nCreating required directories..." -ForegroundColor Yellow
    
    $dirs = @("data", "logs", "backups", "certs")
    foreach ($dir in $dirs) {
        if (-not (Test-Path $dir)) {
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
            Write-Host "✓ Created $dir/" -ForegroundColor Green
        } else {
            Write-Host "✓ $dir/ already exists" -ForegroundColor Gray
        }
    }
}

# Generate self-signed certificates for local development
function Initialize-Certificates {
    Write-Host "`nChecking SSL certificates..." -ForegroundColor Yellow
    
    if (-not (Test-Path "certs/localhost.crt")) {
        Write-Host "Generating self-signed certificate for localhost..." -ForegroundColor Yellow
        
        # Use openssl if available, otherwise skip
        try {
            $opensslPath = (Get-Command openssl -ErrorAction SilentlyContinue).Path
            if ($opensslPath) {
                & openssl req -x509 -nodes -days 365 -newkey rsa:2048 `
                    -keyout certs/localhost.key `
                    -out certs/localhost.crt `
                    -subj "/C=US/ST=State/L=City/O=DEAN/CN=localhost" 2>$null
                Write-Host "✓ Self-signed certificate generated" -ForegroundColor Green
            } else {
                Write-Host "⚠ OpenSSL not found, skipping certificate generation" -ForegroundColor Yellow
                Write-Host "  HTTPS will not be available" -ForegroundColor Gray
            }
        } catch {
            Write-Host "⚠ Could not generate certificates" -ForegroundColor Yellow
        }
    } else {
        Write-Host "✓ SSL certificates already exist" -ForegroundColor Green
    }
}

# Deploy services
function Deploy-Services {
    Write-Host "`nDeploying DEAN services..." -ForegroundColor Yellow
    
    # Use appropriate compose file
    $composeFile = if (Test-Path "docker-compose.prod.yml") {
        "docker-compose.prod.yml"
    } else {
        Write-Host "✗ docker-compose.prod.yml not found\!" -ForegroundColor Red
        exit 1
    }
    
    # Windows-specific compose override if exists
    $overrideFile = if (Test-Path "docker-compose.windows.yml") {
        "-f docker-compose.windows.yml"
    } else {
        ""
    }
    
    try {
        # Pull latest images
        Write-Host "Pulling Docker images..." -ForegroundColor Gray
        docker-compose -f $composeFile $overrideFile pull
        
        # Build custom images
        Write-Host "Building services..." -ForegroundColor Gray
        docker-compose -f $composeFile $overrideFile build
        
        # Start infrastructure services first
        Write-Host "Starting infrastructure services..." -ForegroundColor Gray
        docker-compose -f $composeFile $overrideFile up -d postgres-prod redis-prod
        
        # Wait for database to be ready
        Write-Host "Waiting for database initialization..." -ForegroundColor Gray
        Start-Sleep -Seconds 15
        
        # Run database migrations if available
        if (Test-Path "scripts/migrate.py") {
            Write-Host "Running database migrations..." -ForegroundColor Gray
            docker-compose -f $composeFile $overrideFile run --rm orchestrator python scripts/migrate.py
        }
        
        # Start all services
        Write-Host "Starting all services..." -ForegroundColor Gray
        docker-compose -f $composeFile $overrideFile up -d
        
        Write-Host "✓ Services deployed successfully\!" -ForegroundColor Green
        
    } catch {
        Write-Host "✗ Deployment failed: $_" -ForegroundColor Red
        exit 1
    }
}

# Verify deployment
function Test-Deployment {
    Write-Host "`nVerifying deployment..." -ForegroundColor Yellow
    
    # Wait for services to start
    Start-Sleep -Seconds 10
    
    # Check service status
    Write-Host "Service Status:" -ForegroundColor Gray
    docker-compose -f docker-compose.prod.yml ps
    
    # Test health endpoints
    Write-Host "`nTesting health endpoints..." -ForegroundColor Yellow
    
    $endpoints = @(
        @{Name="Orchestrator"; Url="http://localhost:8082/health"},
        @{Name="Web Interface"; Url="https://localhost/health"}
    )
    
    foreach ($endpoint in $endpoints) {
        try {
            $response = Invoke-WebRequest -Uri $endpoint.Url -UseBasicParsing -SkipCertificateCheck -TimeoutSec 5 2>$null
            if ($response.StatusCode -eq 200) {
                Write-Host "✓ $($endpoint.Name) is healthy" -ForegroundColor Green
            } else {
                Write-Host "⚠ $($endpoint.Name) returned status $($response.StatusCode)" -ForegroundColor Yellow
            }
        } catch {
            Write-Host "✗ $($endpoint.Name) is not responding" -ForegroundColor Red
        }
    }
}

# Main execution
function Main {
    $startTime = Get-Date
    
    Test-Prerequisites
    Test-Configuration
    Initialize-Directories
    Initialize-Certificates
    Deploy-Services
    Test-Deployment
    
    $duration = (Get-Date) - $startTime
    Write-Host "`nDeployment completed in $($duration.TotalSeconds) seconds\!" -ForegroundColor Green
    Write-Host "`nAccess DEAN at:" -ForegroundColor Cyan
    Write-Host "  - HTTP:  http://localhost:8082" -ForegroundColor White
    Write-Host "  - HTTPS: https://localhost (self-signed cert)" -ForegroundColor White
    Write-Host "`nDefault credentials:" -ForegroundColor Yellow
    Write-Host "  Review .env file for configured credentials" -ForegroundColor Gray
    Write-Host "`nFor logs:" -ForegroundColor Gray
    Write-Host "  docker-compose -f docker-compose.prod.yml logs -f" -ForegroundColor Gray
}

# Run main function
Main
