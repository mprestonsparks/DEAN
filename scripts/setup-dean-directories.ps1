# DEAN Deployment Directory Setup Script
# This script creates the required directory structure for DEAN deployment on Windows

Write-Host "Creating DEAN deployment directory structure..." -ForegroundColor Green

# Create main directory structure
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
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Host "✓ Created: $dir" -ForegroundColor Green
    } catch {
        Write-Host "✗ Failed to create: $dir - $_" -ForegroundColor Red
    }
}

Write-Host "`nVerifying directory structure:" -ForegroundColor Yellow

# Verify structure
$createdDirs = Get-ChildItem -Path "C:\dean" -Recurse -Directory | Select-Object FullName

if ($createdDirs.Count -eq 0) {
    Write-Host "No directories found under C:\dean" -ForegroundColor Red
} else {
    Write-Host "Directory structure created successfully:" -ForegroundColor Green
    $createdDirs | ForEach-Object {
        Write-Host "  $($_.FullName)" -ForegroundColor Cyan
    }
}

Write-Host "`nDEAN directory setup complete!" -ForegroundColor Green