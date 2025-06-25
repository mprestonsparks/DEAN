#!/usr/bin/env python3
"""Generate secure credentials for Infisical deployment."""

import secrets
import string
import json
import base64
from datetime import datetime
from cryptography.fernet import Fernet

def generate_password(length=32, special_chars=True):
    """Generate a secure password."""
    alphabet = string.ascii_letters + string.digits
    if special_chars:
        # Use URL-safe special characters
        alphabet += "-_"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def generate_encryption_key():
    """Generate a base64-encoded encryption key."""
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8')

def generate_infisical_credentials():
    """Generate all required credentials for Infisical deployment."""
    credentials = {
        "generated_at": datetime.utcnow().isoformat(),
        "infisical": {
            "postgres_password": generate_password(32, special_chars=False),
            "redis_password": generate_password(32, special_chars=False),
            "encryption_key": generate_encryption_key(),
            "auth_secret": generate_password(64, special_chars=False),
            "jwt_secret": generate_password(64, special_chars=False),
            "admin_email": "admin@dean-system.local",
            "admin_password": generate_password(24),
            "agent_token": f"st.{generate_password(48, special_chars=False)}",
            "dean_project_id": f"proj_{generate_password(16, special_chars=False)}"
        }
    }
    
    return credentials

def generate_env_file(credentials):
    """Generate .env.infisical file content."""
    env_content = f"""# Infisical Security Platform Configuration
# Generated: {credentials['generated_at']}
# WARNING: This file contains sensitive credentials. Protect it carefully!

# Database Configuration
INFISICAL_POSTGRES_PASSWORD={credentials['infisical']['postgres_password']}

# Redis Configuration
INFISICAL_REDIS_PASSWORD={credentials['infisical']['redis_password']}

# Encryption Keys
INFISICAL_ENCRYPTION_KEY={credentials['infisical']['encryption_key']}
INFISICAL_AUTH_SECRET={credentials['infisical']['auth_secret']}
INFISICAL_JWT_SECRET={credentials['infisical']['jwt_secret']}

# Admin Account
INFISICAL_ADMIN_EMAIL={credentials['infisical']['admin_email']}
INFISICAL_ADMIN_PASSWORD={credentials['infisical']['admin_password']}

# Agent Configuration
INFISICAL_AGENT_TOKEN={credentials['infisical']['agent_token']}
INFISICAL_DEAN_PROJECT_ID={credentials['infisical']['dean_project_id']}
"""
    return env_content

def generate_deployment_script():
    """Generate PowerShell script for Windows deployment."""
    script_content = '''# Infisical Deployment Script for Windows
param(
    [string]$DeploymentPath = "C:\\DEAN"
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
    "BUILTIN\\Administrators", "FullControl", "Allow")
$systemRule = New-Object System.Security.AccessControl.FileSystemAccessRule(
    "NT AUTHORITY\\SYSTEM", "FullControl", "Allow")
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
'''
    return script_content

def main():
    """Generate and save Infisical credentials."""
    print("🔐 Generating Infisical credentials...")
    
    credentials = generate_infisical_credentials()
    
    # Save credentials as JSON (for reference)
    with open("infisical_credentials.json", "w") as f:
        json.dump(credentials, f, indent=2)
    print("✓ Saved credentials to infisical_credentials.json")
    
    # Generate .env.infisical file
    env_content = generate_env_file(credentials)
    with open(".env.infisical", "w") as f:
        f.write(env_content)
    print("✓ Generated .env.infisical file")
    
    # Generate deployment script
    script_content = generate_deployment_script()
    with open("deploy_infisical.ps1", "w") as f:
        f.write(script_content)
    print("✓ Generated deploy_infisical.ps1 script")
    
    print("\n⚠️  IMPORTANT SECURITY NOTES:")
    print("1. Protect infisical_credentials.json and .env.infisical files")
    print("2. Never commit these files to version control")
    print("3. Transfer securely to deployment server")
    print("4. Delete local copies after deployment")
    print("\n✅ Infisical credentials generated successfully!")

if __name__ == "__main__":
    main()