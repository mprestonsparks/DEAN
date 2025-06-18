#!/usr/bin/env pwsh
# scripts/setup_ssl.ps1
# Enhanced SSL Certificate Management for DEAN System
# Handles certificate generation, validation, and troubleshooting

param(
    [Parameter()]
    [ValidateSet("development", "production")]
    [string]$Environment = "development",
    
    [Parameter()]
    [string]$CertPath = "./nginx/certs",
    
    [Parameter()]
    [string]$Domain = "localhost",
    
    [Parameter()]
    [int]$ValidityDays = 365,
    
    [Parameter()]
    [switch]$Force = $false,
    
    [Parameter()]
    [switch]$Validate = $false,
    
    [Parameter()]
    [switch]$ShowInstructions = $false
)

$ErrorActionPreference = "Stop"

# Color output functions
function Write-Success { Write-Host "✓ $args" -ForegroundColor Green }
function Write-Error { Write-Host "✗ $args" -ForegroundColor Red }
function Write-Warning { Write-Host "⚠ $args" -ForegroundColor Yellow }
function Write-Info { Write-Host "ℹ $args" -ForegroundColor Cyan }

# Check for OpenSSL
function Test-OpenSSL {
    try {
        $version = openssl version 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Success "OpenSSL found: $version"
            return $true
        }
    } catch {}
    
    Write-Error "OpenSSL not found"
    Write-Info "Install OpenSSL:"
    Write-Info "  - Windows: choco install openssl"
    Write-Info "  - macOS: brew install openssl"
    Write-Info "  - Linux: apt-get install openssl"
    return $false
}

# Generate self-signed certificate
function New-SelfSignedCertificate {
    param(
        [string]$CertPath,
        [string]$Domain,
        [int]$ValidityDays
    )
    
    Write-Info "Generating self-signed certificate for $Domain..."
    
    # Create certificate directory
    if (-not (Test-Path $CertPath)) {
        New-Item -ItemType Directory -Path $CertPath -Force | Out-Null
        Write-Success "Created certificate directory: $CertPath"
    }
    
    # Generate private key and certificate
    $keyFile = Join-Path $CertPath "server.key"
    $certFile = Join-Path $CertPath "server.crt"
    $configFile = Join-Path $CertPath "openssl.cnf"
    
    # Create OpenSSL config for SAN
    $opensslConfig = @"
[req]
distinguished_name = req_distinguished_name
x509_extensions = v3_req
prompt = no

[req_distinguished_name]
C = US
ST = State
L = City
O = DEAN System
CN = $Domain

[v3_req]
keyUsage = keyEncipherment, dataEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = $Domain
DNS.2 = *.$Domain
DNS.3 = localhost
DNS.4 = *.localhost
IP.1 = 127.0.0.1
IP.2 = ::1
"@
    
    $opensslConfig | Out-File -FilePath $configFile -Encoding ASCII
    
    # Generate certificate
    $opensslCmd = @"
openssl req -x509 -nodes -days $ValidityDays -newkey rsa:2048 
    -keyout "$keyFile" 
    -out "$certFile" 
    -config "$configFile"
"@ -replace "`n", " "
    
    try {
        Invoke-Expression $opensslCmd 2>&1 | Out-Null
        
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Generated certificate and key"
            
            # Create copies with alternative names
            $alternativeNames = @(
                @{cert="localhost.crt"; key="localhost.key"},
                @{cert="nginx.crt"; key="nginx.key"}
            )
            
            foreach ($alt in $alternativeNames) {
                Copy-Item $certFile (Join-Path $CertPath $alt.cert) -Force
                Copy-Item $keyFile (Join-Path $CertPath $alt.key) -Force
            }
            
            # Set permissions (Windows-compatible)
            if ($IsWindows) {
                $acl = Get-Acl $keyFile
                $acl.SetAccessRuleProtection($true, $false)
                $permission = $env:USERNAME, "FullControl", "Allow"
                $accessRule = New-Object System.Security.AccessControl.FileSystemAccessRule $permission
                $acl.SetAccessRule($accessRule)
                Set-Acl $keyFile $acl
            } else {
                chmod 600 "$CertPath/*.key" 2>$null
                chmod 644 "$CertPath/*.crt" 2>$null
            }
            
            Write-Success "SSL certificates generated successfully"
            
            # Clean up config file
            Remove-Item $configFile -Force -ErrorAction SilentlyContinue
            
            return $true
        } else {
            Write-Error "Failed to generate certificate"
            return $false
        }
    } catch {
        Write-Error "Error generating certificate: $_"
        return $false
    }
}

# Validate existing certificates
function Test-Certificates {
    param([string]$CertPath)
    
    Write-Info "Validating SSL certificates..."
    
    $requiredFiles = @(
        @{name="server.crt"; type="Certificate"},
        @{name="server.key"; type="Private Key"}
    )
    
    $allValid = $true
    
    foreach ($file in $requiredFiles) {
        $filePath = Join-Path $CertPath $file.name
        
        if (Test-Path $filePath) {
            Write-Success "Found $($file.type): $($file.name)"
            
            # Validate certificate
            if ($file.name -like "*.crt") {
                try {
                    $certInfo = openssl x509 -in $filePath -noout -dates 2>&1
                    if ($LASTEXITCODE -eq 0) {
                        # Check expiration
                        $endDate = $certInfo | Select-String "notAfter=" | ForEach-Object {
                            $_.Line -replace "notAfter=", ""
                        }
                        
                        if ($endDate) {
                            $expiry = [DateTime]::Parse($endDate)
                            $daysLeft = ($expiry - (Get-Date)).Days
                            
                            if ($daysLeft -lt 0) {
                                Write-Error "Certificate expired $(-$daysLeft) days ago"
                                $allValid = $false
                            } elseif ($daysLeft -lt 30) {
                                Write-Warning "Certificate expires in $daysLeft days"
                            } else {
                                Write-Success "Certificate valid for $daysLeft more days"
                            }
                        }
                    }
                } catch {
                    Write-Warning "Could not validate certificate expiration"
                }
            }
        } else {
            Write-Error "Missing $($file.type): $($file.name)"
            $allValid = $false
        }
    }
    
    return $allValid
}

# Show production certificate instructions
function Show-ProductionInstructions {
    Write-Host "`n=== Production Certificate Setup ===" -ForegroundColor Cyan
    Write-Host @"
For production deployment, you need valid SSL certificates from a Certificate Authority (CA).

Option 1: Let's Encrypt (Recommended for production)
---------------------------------------------------
1. Install certbot:
   - Ubuntu/Debian: sudo apt-get install certbot
   - CentOS/RHEL: sudo yum install certbot
   - macOS: brew install certbot

2. Generate certificates:
   sudo certbot certonly --standalone -d your-domain.com

3. Copy certificates to DEAN:
   cp /etc/letsencrypt/live/your-domain.com/fullchain.pem ./nginx/certs/server.crt
   cp /etc/letsencrypt/live/your-domain.com/privkey.pem ./nginx/certs/server.key

4. Set up auto-renewal:
   sudo crontab -e
   Add: 0 0 * * 0 certbot renew --quiet

Option 2: Commercial CA Certificate
-----------------------------------
1. Generate CSR:
   openssl req -new -newkey rsa:2048 -nodes -keyout server.key -out server.csr

2. Submit CSR to your CA and download certificates

3. Install certificates:
   cp your-certificate.crt ./nginx/certs/server.crt
   cp your-private-key.key ./nginx/certs/server.key

Option 3: Internal CA (For internal deployments)
-----------------------------------------------
Use your organization's internal CA to generate certificates.

Certificate Requirements:
- RSA 2048-bit or higher
- Valid for your domain name
- Includes Subject Alternative Names (SAN) if needed
- Not expired

After installing certificates, validate with:
  ./scripts/setup_ssl.ps1 -Validate
"@
}

# Main execution
function Start-SSLSetup {
    Write-Host "`n=== DEAN SSL Certificate Management ===" -ForegroundColor Cyan
    Write-Host "Environment: $Environment" -ForegroundColor White
    Write-Host "Domain: $Domain" -ForegroundColor White
    Write-Host "Certificate Path: $CertPath" -ForegroundColor White
    Write-Host ""
    
    # Check OpenSSL
    if (-not (Test-OpenSSL)) {
        exit 1
    }
    
    # Show instructions if requested
    if ($ShowInstructions) {
        Show-ProductionInstructions
        return
    }
    
    # Validate only
    if ($Validate) {
        if (Test-Certificates -CertPath $CertPath) {
            Write-Success "`nAll certificates are valid"
            exit 0
        } else {
            Write-Error "`nCertificate validation failed"
            exit 1
        }
    }
    
    # Check existing certificates
    $certExists = Test-Path (Join-Path $CertPath "server.crt")
    
    if ($certExists -and -not $Force) {
        Write-Info "Certificates already exist. Validating..."
        if (Test-Certificates -CertPath $CertPath) {
            Write-Success "Existing certificates are valid"
            Write-Info "Use -Force to regenerate certificates"
            return
        } else {
            Write-Warning "Existing certificates have issues. Regenerating..."
        }
    }
    
    # Generate certificates based on environment
    if ($Environment -eq "development") {
        if (New-SelfSignedCertificate -CertPath $CertPath -Domain $Domain -ValidityDays $ValidityDays) {
            Write-Success "`nDevelopment certificates ready!"
            Write-Warning "These are self-signed certificates. Browsers will show security warnings."
            Write-Info "For production, use certificates from a trusted CA."
        } else {
            Write-Error "Failed to generate certificates"
            exit 1
        }
    } else {
        Write-Warning "Production environment selected"
        Write-Info "Checking for production certificates..."
        
        if (-not (Test-Certificates -CertPath $CertPath)) {
            Write-Error "Production certificates not found!"
            Show-ProductionInstructions
            exit 1
        }
    }
    
    Write-Success "`nSSL setup complete!"
}

# Run main function
Start-SSLSetup