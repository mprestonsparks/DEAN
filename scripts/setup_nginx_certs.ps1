# DEAN Nginx Certificate Setup Script for Windows
# Converts existing PFX or generates new self-signed certificates

param(
    [Parameter(Mandatory=$false)]
    [string]$PfxPath = ".\certs\localhost.pfx",
    
    [Parameter(Mandatory=$false)]
    [string]$PfxPassword = "",
    
    [Parameter(Mandatory=$false)]
    [string]$OutputDir = ".\certs",
    
    [Parameter(Mandatory=$false)]
    [switch]$GenerateNew = $false
)

Write-Host "=== DEAN Nginx Certificate Setup ===" -ForegroundColor Cyan
Write-Host ""

# Ensure output directory exists
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
    Write-Host "Created certificate directory: $OutputDir" -ForegroundColor Green
}

# Function to convert PFX to PEM format
function Convert-PfxToPem {
    param(
        [string]$PfxFile,
        [string]$Password,
        [string]$OutDir
    )
    
    Write-Host "Converting PFX certificate to nginx format..." -ForegroundColor Yellow
    
    try {
        # Load the PFX certificate
        $pfxCert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2
        
        if ($Password) {
            $securePassword = ConvertTo-SecureString -String $Password -AsPlainText -Force
            $pfxCert.Import($PfxFile, $securePassword, [System.Security.Cryptography.X509Certificates.X509KeyStorageFlags]::Exportable)
        } else {
            # Try without password first
            try {
                $pfxCert.Import($PfxFile, "", [System.Security.Cryptography.X509Certificates.X509KeyStorageFlags]::Exportable)
            } catch {
                # Prompt for password if needed
                $securePassword = Read-Host "Enter PFX password" -AsSecureString
                $pfxCert.Import($PfxFile, $securePassword, [System.Security.Cryptography.X509Certificates.X509KeyStorageFlags]::Exportable)
            }
        }
        
        # Export certificate (public key)
        $certPem = "-----BEGIN CERTIFICATE-----`n"
        $certPem += [System.Convert]::ToBase64String($pfxCert.RawData, [System.Base64FormattingOptions]::InsertLineBreaks)
        $certPem += "`n-----END CERTIFICATE-----`n"
        
        # Save certificate files
        $certPem | Out-File -FilePath "$OutDir\localhost.crt" -Encoding ASCII
        $certPem | Out-File -FilePath "$OutDir\nginx.crt" -Encoding ASCII
        
        # Export private key (if available)
        $rsaKey = $pfxCert.PrivateKey
        if ($rsaKey) {
            $privateKeyBytes = $rsaKey.ExportCspBlob($true)
            
            # Convert to PEM format (simplified - for production use OpenSSL)
            Write-Host "Note: For production use, OpenSSL is recommended for private key export" -ForegroundColor Yellow
            
            # Create a basic private key file (nginx may need OpenSSL conversion)
            $keyContent = "-----BEGIN RSA PRIVATE KEY-----`n"
            $keyContent += [System.Convert]::ToBase64String($privateKeyBytes, [System.Base64FormattingOptions]::InsertLineBreaks)
            $keyContent += "`n-----END RSA PRIVATE KEY-----`n"
            
            $keyContent | Out-File -FilePath "$OutDir\localhost.key.tmp" -Encoding ASCII
            $keyContent | Out-File -FilePath "$OutDir\nginx.key.tmp" -Encoding ASCII
            
            Write-Host "✓ Certificate exported (may need OpenSSL conversion for private key)" -ForegroundColor Yellow
            Write-Host "  If nginx fails to read the key, use OpenSSL to convert it:" -ForegroundColor Gray
            Write-Host "  openssl rsa -in localhost.key.tmp -out localhost.key" -ForegroundColor Gray
        } else {
            Write-Host "⚠ Private key not found in PFX" -ForegroundColor Red
        }
        
        return $true
        
    } catch {
        Write-Host "✗ Failed to convert PFX: $_" -ForegroundColor Red
        return $false
    }
}

# Function to generate new self-signed certificate
function New-SelfSignedCertificateForNginx {
    param(
        [string]$OutDir
    )
    
    Write-Host "Generating new self-signed certificate..." -ForegroundColor Yellow
    
    try {
        # Check if OpenSSL is available
        $opensslPath = Get-Command openssl -ErrorAction SilentlyContinue
        
        if ($opensslPath) {
            Write-Host "Using OpenSSL to generate certificate..." -ForegroundColor Green
            
            # Generate private key
            & openssl genrsa -out "$OutDir\localhost.key" 2048 2>$null
            
            # Generate certificate
            & openssl req -new -x509 -key "$OutDir\localhost.key" -out "$OutDir\localhost.crt" -days 365 `
                -subj "/C=US/ST=State/L=City/O=DEAN/CN=localhost" 2>$null
            
            # Create copies for nginx
            Copy-Item "$OutDir\localhost.crt" "$OutDir\nginx.crt" -Force
            Copy-Item "$OutDir\localhost.key" "$OutDir\nginx.key" -Force
            
            Write-Host "✓ Certificates generated with OpenSSL" -ForegroundColor Green
            
        } else {
            Write-Host "OpenSSL not found. Using PowerShell to generate certificate..." -ForegroundColor Yellow
            
            # Use PowerShell to create self-signed certificate
            $cert = New-SelfSignedCertificate `
                -DnsName "localhost", "127.0.0.1", "::1" `
                -CertStoreLocation "Cert:\CurrentUser\My" `
                -NotAfter (Get-Date).AddYears(1) `
                -FriendlyName "DEAN Localhost Certificate" `
                -KeyExportPolicy Exportable `
                -KeySpec Signature `
                -KeyUsage DigitalSignature, KeyEncipherment `
                -KeyAlgorithm RSA `
                -KeyLength 2048 `
                -HashAlgorithm SHA256
            
            # Export certificate
            $certPath = "Cert:\CurrentUser\My\$($cert.Thumbprint)"
            $certPem = "-----BEGIN CERTIFICATE-----`n"
            $certPem += [System.Convert]::ToBase64String($cert.RawData, [System.Base64FormattingOptions]::InsertLineBreaks)
            $certPem += "`n-----END CERTIFICATE-----`n"
            
            $certPem | Out-File -FilePath "$OutDir\localhost.crt" -Encoding ASCII
            $certPem | Out-File -FilePath "$OutDir\nginx.crt" -Encoding ASCII
            
            # Export to PFX first (for key extraction)
            $pfxPassword = ConvertTo-SecureString -String "temp123" -AsPlainText -Force
            Export-PfxCertificate -Cert $certPath -FilePath "$OutDir\temp.pfx" -Password $pfxPassword | Out-Null
            
            Write-Host "✓ Certificate created" -ForegroundColor Green
            Write-Host "⚠ Private key export requires additional steps" -ForegroundColor Yellow
            Write-Host "  Consider installing OpenSSL for complete key generation" -ForegroundColor Gray
            
            # Clean up
            Remove-Item $certPath -Force
            Remove-Item "$OutDir\temp.pfx" -Force -ErrorAction SilentlyContinue
        }
        
        return $true
        
    } catch {
        Write-Host "✗ Failed to generate certificate: $_" -ForegroundColor Red
        return $false
    }
}

# Main execution
if ($GenerateNew -or -not (Test-Path $PfxPath)) {
    if (-not $GenerateNew -and -not (Test-Path $PfxPath)) {
        Write-Host "PFX file not found at: $PfxPath" -ForegroundColor Yellow
        Write-Host "Generating new self-signed certificate instead..." -ForegroundColor Yellow
    }
    
    $success = New-SelfSignedCertificateForNginx -OutDir $OutputDir
} else {
    Write-Host "Found PFX at: $PfxPath" -ForegroundColor Green
    $success = Convert-PfxToPem -PfxFile $PfxPath -Password $PfxPassword -OutDir $OutputDir
}

# Final summary
if ($success) {
    Write-Host "`n=== Certificate Setup Complete ===" -ForegroundColor Green
    Write-Host "Certificates location: $OutputDir" -ForegroundColor White
    
    $files = @("localhost.crt", "localhost.key", "nginx.crt", "nginx.key")
    Write-Host "`nGenerated files:" -ForegroundColor Cyan
    foreach ($file in $files) {
        $path = Join-Path $OutputDir $file
        if (Test-Path $path) {
            Write-Host "  ✓ $file" -ForegroundColor Green
        } elseif (Test-Path "$path.tmp") {
            Write-Host "  ⚠ $file.tmp (needs OpenSSL conversion)" -ForegroundColor Yellow
        } else {
            Write-Host "  ✗ $file (missing)" -ForegroundColor Red
        }
    }
    
    Write-Host "`nNext steps:" -ForegroundColor Yellow
    Write-Host "1. If you see .tmp files, install OpenSSL and run:" -ForegroundColor White
    Write-Host "   openssl rsa -in localhost.key.tmp -out localhost.key" -ForegroundColor Gray
    Write-Host "2. Ensure certificates are in the certs/ directory" -ForegroundColor White
    Write-Host "3. Run docker-compose to start nginx" -ForegroundColor White
    
} else {
    Write-Host "`n✗ Certificate setup failed" -ForegroundColor Red
    Write-Host "Please check the error messages above" -ForegroundColor Yellow
}

# Recommend OpenSSL installation if not found
if (-not (Get-Command openssl -ErrorAction SilentlyContinue)) {
    Write-Host "`nRecommendation: Install OpenSSL for better certificate handling" -ForegroundColor Yellow
    Write-Host "Options:" -ForegroundColor White
    Write-Host "  - Git for Windows includes OpenSSL" -ForegroundColor Gray
    Write-Host "  - Download from: https://www.openssl.org/source/" -ForegroundColor Gray
    Write-Host "  - Or use: choco install openssl (if Chocolatey is installed)" -ForegroundColor Gray
}