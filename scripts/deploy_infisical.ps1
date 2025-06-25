# Infisical Deployment Script for Windows
param(
    [string]$DeploymentPath = "C:\DEAN"
)

Write-Host "🔐 Deploying Infisical Security Platform" -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Cyan

# Check prerequisites
if (-not (Test-Path $DeploymentPath)) {
    Write-Error "DEAN deployment directory not found: $DeploymentPath"
    exit 1
}

Set-Location $DeploymentPath

# Check for .env.infisical
if (-not (Test-Path ".env.infisical")) {
    Write-Error ".env.infisical not found. Please create it with generated credentials."
    exit 1
}

# Create required directories
Write-Host "`nCreating directories..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path "docker/infisical/data" | Out-Null
New-Item -ItemType Directory -Force -Path "docker/infisical/certs" | Out-Null

# Set secure permissions on .env.infisical
Write-Host "Setting secure permissions..." -ForegroundColor Yellow
$acl = Get-Acl ".env.infisical"
$acl.SetAccessRuleProtection($true, $false)
$adminRule = New-Object System.Security.AccessControl.FileSystemAccessRule(
    "BUILTIN\Administrators", "FullControl", "Allow")
$systemRule = New-Object System.Security.AccessControl.FileSystemAccessRule(
    "NT AUTHORITY\SYSTEM", "FullControl", "Allow")
$acl.SetAccessRule($adminRule)
$acl.SetAccessRule($systemRule)
Set-Acl -Path ".env.infisical" -AclObject $acl

# Deploy Infisical
Write-Host "`nDeploying Infisical..." -ForegroundColor Yellow
docker-compose -f docker-compose.infisical.yml --env-file .env.infisical up -d

# Wait for Infisical to be ready
Write-Host "`nWaiting for Infisical to initialize..." -ForegroundColor Yellow
$maxAttempts = 30
$attempt = 0

while ($attempt -lt $maxAttempts) {
    Start-Sleep -Seconds 10
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8090/api/status" -UseBasicParsing -TimeoutSec 5
        if ($response.StatusCode -eq 200) {
            Write-Host "✅ Infisical is ready!" -ForegroundColor Green
            break
        }
    } catch {
        $attempt++
        Write-Host "Waiting for Infisical... ($attempt/$maxAttempts)"
    }
}

if ($attempt -eq $maxAttempts) {
    Write-Error "Infisical failed to start within expected time"
    docker-compose -f docker-compose.infisical.yml logs infisical
    exit 1
}

Write-Host "`n✅ Infisical deployed successfully!" -ForegroundColor Green
Write-Host "`n📋 Access Information:" -ForegroundColor Cyan
Write-Host "  URL: http://localhost:8090" -ForegroundColor White
Write-Host "  Admin Email: Check .env.infisical" -ForegroundColor White
Write-Host "  Admin Password: Check .env.infisical" -ForegroundColor White
Write-Host "`n⚠️  Next Steps:" -ForegroundColor Yellow
Write-Host "1. Login to Infisical web UI" -ForegroundColor White
Write-Host "2. Create DEAN organization" -ForegroundColor White
Write-Host "3. Run setup_infisical_secrets.py to configure all secrets" -ForegroundColor White
