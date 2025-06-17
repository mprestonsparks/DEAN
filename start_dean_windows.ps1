# DEAN Quick Start Script for Windows
Write-Host "Starting DEAN services..." -ForegroundColor Cyan

# Check if nginx config exists
if (-not (Test-Path "nginx\nginx.prod.conf")) {
    Write-Host "Nginx configuration not found. Running without nginx." -ForegroundColor Yellow
    docker-compose -f docker-compose.prod.yml up -d postgres-prod redis-prod orchestrator
} else {
    Write-Host "Starting all services including nginx..." -ForegroundColor Green
    docker-compose -f docker-compose.prod.yml up -d
}

Start-Sleep -Seconds 5

# Check service status
Write-Host "`nService Status:" -ForegroundColor Cyan
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Test health endpoint
Write-Host "`nTesting health endpoint..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri http://localhost:8082/health -UseBasicParsing
    Write-Host "✓ Orchestrator is healthy!" -ForegroundColor Green
} catch {
    Write-Host "⚠ Health check failed - services may still be starting" -ForegroundColor Red
}

Write-Host "`nDEAN is accessible at:" -ForegroundColor Cyan
Write-Host "  - Direct: http://localhost:8082" -ForegroundColor White
if (docker ps | Select-String "dean-nginx") {
    Write-Host "  - Via Nginx: http://localhost" -ForegroundColor White
}