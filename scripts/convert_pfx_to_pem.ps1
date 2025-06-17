# Simple PFX to PEM Converter for DEAN Nginx
# Requires OpenSSL to be installed

param(
    [Parameter(Mandatory=$false)]
    [string]$PfxPath = ".\certs\localhost.pfx",
    
    [Parameter(Mandatory=$false)]
    [string]$OutputDir = ".\certs"
)

Write-Host "=== PFX to PEM Converter for Nginx ===" -ForegroundColor Cyan

# Check if OpenSSL is available
$openssl = Get-Command openssl -ErrorAction SilentlyContinue
if (-not $openssl) {
    Write-Host "ERROR: OpenSSL is required but not found in PATH" -ForegroundColor Red
    Write-Host "Please install OpenSSL first:" -ForegroundColor Yellow
    Write-Host "  - Git for Windows includes OpenSSL" -ForegroundColor Gray
    Write-Host "  - Or download from: https://www.openssl.org/" -ForegroundColor Gray
    exit 1
}

# Check if PFX exists
if (-not (Test-Path $PfxPath)) {
    Write-Host "ERROR: PFX file not found at: $PfxPath" -ForegroundColor Red
    exit 1
}

# Ensure output directory exists
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

Write-Host "Converting $PfxPath to nginx format..." -ForegroundColor Yellow

# Extract private key
Write-Host "Extracting private key..." -ForegroundColor Gray
$keyFile = Join-Path $OutputDir "localhost.key"
& openssl pkcs12 -in $PfxPath -nocerts -nodes -out $keyFile 2>$null

if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to extract private key. The PFX may be password protected." -ForegroundColor Red
    Write-Host "Trying with password prompt..." -ForegroundColor Yellow
    & openssl pkcs12 -in $PfxPath -nocerts -nodes -out $keyFile
}

# Extract certificate
Write-Host "Extracting certificate..." -ForegroundColor Gray
$crtFile = Join-Path $OutputDir "localhost.crt"
& openssl pkcs12 -in $PfxPath -clcerts -nokeys -out $crtFile 2>$null

if ($LASTEXITCODE -ne 0) {
    & openssl pkcs12 -in $PfxPath -clcerts -nokeys -out $crtFile
}

# Create nginx copies
Copy-Item $keyFile (Join-Path $OutputDir "nginx.key") -Force
Copy-Item $crtFile (Join-Path $OutputDir "nginx.crt") -Force

# Verify files
Write-Host "`nVerifying generated files..." -ForegroundColor Yellow
$success = $true

foreach ($file in @("localhost.key", "localhost.crt", "nginx.key", "nginx.crt")) {
    $path = Join-Path $OutputDir $file
    if (Test-Path $path) {
        Write-Host "  ✓ $file" -ForegroundColor Green
    } else {
        Write-Host "  ✗ $file missing" -ForegroundColor Red
        $success = $false
    }
}

if ($success) {
    Write-Host "`n✓ Conversion complete!" -ForegroundColor Green
    Write-Host "Nginx certificates are ready in: $OutputDir" -ForegroundColor White
} else {
    Write-Host "`n✗ Conversion failed" -ForegroundColor Red
}