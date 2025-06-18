#!/usr/bin/env pwsh
# scripts/validate_deployment.ps1
# Comprehensive pre-deployment validation script for DEAN System
# Addresses all deployment issues discovered during initial deployment

param(
    [switch]$AutoFix = $false,
    [switch]$Verbose = $false
)

$ErrorActionPreference = "Stop"
$script:hasErrors = $false
$script:hasWarnings = $false

# Color output functions
function Write-Success { 
    param($Message)
    Write-Host "✓ $Message" -ForegroundColor Green 
}

function Write-Error { 
    param($Message)
    Write-Host "✗ $Message" -ForegroundColor Red
    $script:hasErrors = $true
}

function Write-Warning { 
    param($Message)
    Write-Host "⚠ $Message" -ForegroundColor Yellow
    $script:hasWarnings = $true
}

function Write-Info { 
    param($Message)
    Write-Host "ℹ $Message" -ForegroundColor Cyan 
}

function Write-Header {
    param($Title)
    Write-Host "`n=== $Title ===" -ForegroundColor Magenta
}

# Check for BOM in configuration files
function Test-BOMInFiles {
    Write-Header "Checking for BOM characters in configuration files"
    
    $configFiles = @(
        "nginx/nginx.prod.conf",
        "nginx/nginx.dev.conf",
        "docker-compose.yml",
        "docker-compose.prod.yml",
        ".env",
        "configs/**/*.yaml",
        "configs/**/*.yml"
    )
    
    $bomFound = $false
    
    foreach ($pattern in $configFiles) {
        $files = Get-ChildItem -Path . -Filter $pattern -Recurse -ErrorAction SilentlyContinue
        
        foreach ($file in $files) {
            if (Test-Path $file.FullName) {
                $bytes = [System.IO.File]::ReadAllBytes($file.FullName)
                
                # Check for UTF-8 BOM (EF BB BF)
                if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
                    Write-Error "BOM found in: $($file.FullName)"
                    $bomFound = $true
                    
                    if ($AutoFix) {
                        Write-Info "Removing BOM from $($file.Name)..."
                        $content = [System.IO.File]::ReadAllText($file.FullName)
                        [System.IO.File]::WriteAllText($file.FullName, $content, [System.Text.UTF8Encoding]::new($false))
                        Write-Success "BOM removed from $($file.Name)"
                    }
                }
            }
        }
    }
    
    if (-not $bomFound) {
        Write-Success "No BOM characters found in configuration files"
    } elseif (-not $AutoFix) {
        Write-Warning "Run with -AutoFix to remove BOM characters automatically"
    }
}

# Validate environment variables
function Test-EnvironmentVariables {
    Write-Header "Validating environment variables"
    
    $requiredVars = @{
        "JWT_SECRET_KEY" = @{
            MinLength = 32
            Description = "JWT signing key (min 32 chars)"
        }
        "POSTGRES_USER" = @{
            Description = "PostgreSQL username"
        }
        "POSTGRES_PASSWORD" = @{
            MinLength = 8
            Description = "PostgreSQL password (min 8 chars)"
        }
        "POSTGRES_DB" = @{
            Description = "PostgreSQL database name"
            ExpectedValue = "dean_production"
        }
        "REDIS_PASSWORD" = @{
            MinLength = 8
            Description = "Redis password (min 8 chars)"
        }
        "DEAN_SERVICE_API_KEY" = @{
            MinLength = 16
            Description = "Service API key (min 16 chars)"
        }
    }
    
    # Load .env file if exists
    $envFile = ".env"
    $envVars = @{}
    
    if (Test-Path $envFile) {
        Get-Content $envFile | ForEach-Object {
            if ($_ -match "^([^#][^=]+)=(.*)$") {
                $envVars[$matches[1].Trim()] = $matches[2].Trim()
            }
        }
    } else {
        Write-Error ".env file not found"
        if ($AutoFix) {
            Write-Info "Creating .env from template..."
            if (Test-Path ".env.template") {
                Copy-Item ".env.template" ".env"
                Write-Success ".env created from template"
            } else {
                Write-Error ".env.template not found"
            }
        }
        return
    }
    
    foreach ($var in $requiredVars.GetEnumerator()) {
        $varName = $var.Key
        $varConfig = $var.Value
        $value = $envVars[$varName]
        
        if (-not $value) {
            Write-Error "$varName is not set - $($varConfig.Description)"
        } else {
            # Check minimum length
            if ($varConfig.MinLength -and $value.Length -lt $varConfig.MinLength) {
                Write-Error "$varName is too short (${value.Length} chars, min $($varConfig.MinLength))"
            }
            
            # Check expected value
            if ($varConfig.ExpectedValue -and $value -ne $varConfig.ExpectedValue) {
                Write-Warning "$varName is '$value' but expected '$($varConfig.ExpectedValue)'"
            }
            
            # Check for placeholder values
            if ($value -match "CHANGE_ME|REPLACE_ME|TODO|XXX") {
                Write-Error "$varName contains placeholder value"
            }
        }
    }
    
    # Check database naming consistency
    $dbName = $envVars["POSTGRES_DB"]
    if ($dbName -and $dbName -ne "dean_production") {
        Write-Warning "Database name is '$dbName' - ensure docker-compose.yml uses the same name"
    }
}

# Check SSL certificates
function Test-SSLCertificates {
    Write-Header "Checking SSL certificates"
    
    $certPaths = @(
        "nginx/certs/server.crt",
        "nginx/certs/server.key",
        "nginx/certs/localhost.crt",
        "nginx/certs/localhost.key",
        "nginx/certs/nginx.crt",
        "nginx/certs/nginx.key"
    )
    
    $certsDir = "nginx/certs"
    $anyCertFound = $false
    
    # Check if directory exists
    if (-not (Test-Path $certsDir)) {
        Write-Error "Certificate directory $certsDir does not exist"
        if ($AutoFix) {
            Write-Info "Creating certificate directory..."
            New-Item -ItemType Directory -Path $certsDir -Force | Out-Null
            Write-Success "Certificate directory created"
        }
    }
    
    # Check for any certificate files
    foreach ($certPath in $certPaths) {
        if (Test-Path $certPath) {
            $anyCertFound = $true
            Write-Success "Found certificate: $certPath"
        }
    }
    
    if (-not $anyCertFound) {
        Write-Error "No SSL certificates found"
        if ($AutoFix) {
            Write-Info "Generating self-signed certificates..."
            & ./scripts/setup_ssl_certificates.sh
            if ($LASTEXITCODE -eq 0) {
                Write-Success "SSL certificates generated"
            } else {
                Write-Error "Failed to generate SSL certificates"
            }
        } else {
            Write-Warning "Run ./scripts/setup_ssl_certificates.sh to generate certificates"
        }
    }
}

# Check required directories
function Test-RequiredDirectories {
    Write-Header "Checking required directories"
    
    $requiredDirs = @(
        "nginx/certs",
        "postgres",
        "logs",
        "data"
    )
    
    foreach ($dir in $requiredDirs) {
        if (Test-Path $dir) {
            Write-Success "Directory exists: $dir"
        } else {
            Write-Error "Directory missing: $dir"
            if ($AutoFix) {
                Write-Info "Creating directory $dir..."
                New-Item -ItemType Directory -Path $dir -Force | Out-Null
                Write-Success "Directory created: $dir"
            }
        }
    }
}

# Check Docker environment
function Test-DockerEnvironment {
    Write-Header "Checking Docker environment"
    
    # Check if Docker is running
    try {
        $dockerInfo = docker info 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Docker is running"
        } else {
            Write-Error "Docker is not running"
            return
        }
    } catch {
        Write-Error "Docker command not found"
        return
    }
    
    # Check Docker Compose
    try {
        $composeVersion = docker compose version 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Docker Compose v2 is available"
        } else {
            # Try legacy docker-compose
            $legacyVersion = docker-compose --version 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Warning "Using legacy docker-compose (consider upgrading to Docker Compose v2)"
            } else {
                Write-Error "Docker Compose not found"
            }
        }
    } catch {
        Write-Error "Docker Compose not found"
    }
}

# Check port availability
function Test-PortAvailability {
    Write-Header "Checking port availability"
    
    $requiredPorts = @{
        80 = "HTTP (nginx)"
        443 = "HTTPS (nginx)"
        8082 = "Orchestrator API"
        5432 = "PostgreSQL"
        6379 = "Redis"
    }
    
    foreach ($port in $requiredPorts.GetEnumerator()) {
        $tcpClient = New-Object System.Net.Sockets.TcpClient
        try {
            $tcpClient.Connect("localhost", $port.Key)
            $tcpClient.Close()
            Write-Warning "Port $($port.Key) is already in use ($($port.Value))"
        } catch {
            Write-Success "Port $($port.Key) is available ($($port.Value))"
        }
    }
}

# Validate docker-compose files
function Test-DockerComposeFiles {
    Write-Header "Validating docker-compose files"
    
    $composeFiles = @(
        "docker-compose.yml",
        "docker-compose.prod.yml"
    )
    
    foreach ($file in $composeFiles) {
        if (Test-Path $file) {
            # Check for valid YAML
            try {
                docker compose -f $file config > $null 2>&1
                if ($LASTEXITCODE -eq 0) {
                    Write-Success "$file is valid"
                } else {
                    Write-Error "$file has syntax errors"
                }
            } catch {
                Write-Warning "Could not validate $file"
            }
            
            # Check for database name consistency
            $content = Get-Content $file -Raw
            if ($content -match "POSTGRES_DB=(\w+)") {
                $dbName = $matches[1]
                if ($dbName -ne "dean_production") {
                    Write-Warning "$file uses database name '$dbName' instead of 'dean_production'"
                }
            }
        } else {
            Write-Error "$file not found"
        }
    }
}

# Main validation function
function Start-ValidationChecks {
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "DEAN System Pre-Deployment Validation" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "AutoFix: $(if ($AutoFix) { 'Enabled' } else { 'Disabled' })" -ForegroundColor White
    Write-Host "Time: $(Get-Date)" -ForegroundColor White
    
    # Run all checks
    Test-DockerEnvironment
    Test-BOMInFiles
    Test-EnvironmentVariables
    Test-RequiredDirectories
    Test-SSLCertificates
    Test-PortAvailability
    Test-DockerComposeFiles
    
    # Summary
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "Validation Summary" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    
    if ($script:hasErrors) {
        Write-Host "RESULT: FAILED - Errors found" -ForegroundColor Red
        if (-not $AutoFix) {
            Write-Host "`nRun with -AutoFix flag to attempt automatic fixes" -ForegroundColor Yellow
        }
        exit 1
    } elseif ($script:hasWarnings) {
        Write-Host "RESULT: PASSED WITH WARNINGS" -ForegroundColor Yellow
        Write-Host "The system can be deployed but review warnings above" -ForegroundColor Yellow
        exit 0
    } else {
        Write-Host "RESULT: PASSED - Ready for deployment!" -ForegroundColor Green
        exit 0
    }
}

# Run validation
Start-ValidationChecks