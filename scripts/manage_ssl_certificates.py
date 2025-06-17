#!/usr/bin/env python3
"""
SSL Certificate Management System for DEAN
Handles generation, validation, and management of SSL certificates.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path
from datetime import datetime, timedelta
import shutil
from typing import Dict, Tuple, Optional

class CertificateManager:
    """Manages SSL certificates for DEAN deployment."""
    
    def __init__(self, cert_dir: Path):
        self.cert_dir = cert_dir
        self.cert_dir.mkdir(parents=True, exist_ok=True)
        
    def check_openssl(self) -> bool:
        """Check if OpenSSL is available."""
        try:
            result = subprocess.run(['openssl', 'version'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✓ OpenSSL available: {result.stdout.strip()}")
                return True
        except FileNotFoundError:
            pass
        
        print("✗ OpenSSL not found. Please install OpenSSL.")
        return False
    
    def generate_self_signed_cert(self, 
                                 hostname: str = "localhost",
                                 days: int = 365) -> Tuple[bool, str]:
        """
        Generate a self-signed certificate for development.
        
        Args:
            hostname: Hostname for the certificate
            days: Certificate validity in days
            
        Returns:
            Tuple of (success, message)
        """
        if not self.check_openssl():
            return False, "OpenSSL not available"
        
        key_file = self.cert_dir / "server.key"
        cert_file = self.cert_dir / "server.crt"
        
        # Generate private key
        print(f"\nGenerating private key...")
        key_cmd = [
            'openssl', 'genrsa', 
            '-out', str(key_file), 
            '2048'
        ]
        
        result = subprocess.run(key_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return False, f"Failed to generate private key: {result.stderr}"
        
        # Generate certificate
        print(f"Generating self-signed certificate for '{hostname}'...")
        cert_cmd = [
            'openssl', 'req', '-new', '-x509',
            '-key', str(key_file),
            '-out', str(cert_file),
            '-days', str(days),
            '-subj', f'/CN={hostname}/O=DEAN Development/C=US'
        ]
        
        # Add Subject Alternative Names for localhost
        if hostname == "localhost":
            san_file = self.cert_dir / "san.cnf"
            san_content = """
[req]
distinguished_name = req_distinguished_name
x509_extensions = v3_req

[req_distinguished_name]

[v3_req]
subjectAltName = @alt_names

[alt_names]
DNS.1 = localhost
DNS.2 = *.localhost
IP.1 = 127.0.0.1
IP.2 = ::1
"""
            san_file.write_text(san_content)
            cert_cmd.extend(['-extensions', 'v3_req', '-config', str(san_file)])
        
        result = subprocess.run(cert_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return False, f"Failed to generate certificate: {result.stderr}"
        
        # Set appropriate permissions
        key_file.chmod(0o600)
        cert_file.chmod(0o644)
        
        # Clean up temporary files
        san_file = self.cert_dir / "san.cnf"
        if san_file.exists():
            san_file.unlink()
        
        print(f"✓ Generated self-signed certificate:")
        print(f"  Private key: {key_file}")
        print(f"  Certificate: {cert_file}")
        print(f"  Valid for: {days} days")
        
        return True, "Certificate generated successfully"
    
    def generate_dhparam(self, bits: int = 2048) -> Tuple[bool, str]:
        """
        Generate Diffie-Hellman parameters for enhanced security.
        
        Args:
            bits: DH parameter size
            
        Returns:
            Tuple of (success, message)
        """
        if not self.check_openssl():
            return False, "OpenSSL not available"
        
        dhparam_file = self.cert_dir / "dhparam.pem"
        
        print(f"\nGenerating {bits}-bit DH parameters (this may take a while)...")
        cmd = [
            'openssl', 'dhparam',
            '-out', str(dhparam_file),
            str(bits)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return False, f"Failed to generate DH parameters: {result.stderr}"
        
        dhparam_file.chmod(0o644)
        print(f"✓ Generated DH parameters: {dhparam_file}")
        
        return True, "DH parameters generated successfully"
    
    def validate_certificate(self, cert_file: Path) -> Dict[str, any]:
        """
        Validate and get information about a certificate.
        
        Args:
            cert_file: Path to certificate file
            
        Returns:
            Dictionary with certificate information
        """
        if not cert_file.exists():
            return {"valid": False, "error": "Certificate file not found"}
        
        if not self.check_openssl():
            return {"valid": False, "error": "OpenSSL not available"}
        
        # Get certificate information
        cmd = [
            'openssl', 'x509',
            '-in', str(cert_file),
            '-noout', '-text'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return {"valid": False, "error": f"Invalid certificate: {result.stderr}"}
        
        # Extract key information
        info = {"valid": True}
        
        # Get subject
        cmd = ['openssl', 'x509', '-in', str(cert_file), '-noout', '-subject']
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            info["subject"] = result.stdout.strip()
        
        # Get dates
        cmd = ['openssl', 'x509', '-in', str(cert_file), '-noout', '-dates']
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            dates = result.stdout.strip()
            info["dates"] = dates
            
            # Check if expired
            cmd = ['openssl', 'x509', '-in', str(cert_file), '-noout', '-checkend', '0']
            result = subprocess.run(cmd, capture_output=True, text=True)
            info["expired"] = result.returncode != 0
        
        return info
    
    def setup_production_certs(self, cert_path: str, key_path: str) -> Tuple[bool, str]:
        """
        Set up production certificates by copying them to the certs directory.
        
        Args:
            cert_path: Path to production certificate
            key_path: Path to production private key
            
        Returns:
            Tuple of (success, message)
        """
        cert_src = Path(cert_path)
        key_src = Path(key_path)
        
        if not cert_src.exists():
            return False, f"Certificate not found: {cert_src}"
        
        if not key_src.exists():
            return False, f"Private key not found: {key_src}"
        
        # Validate certificate
        cert_info = self.validate_certificate(cert_src)
        if not cert_info["valid"]:
            return False, f"Invalid certificate: {cert_info.get('error', 'Unknown error')}"
        
        if cert_info.get("expired", False):
            return False, "Certificate has expired"
        
        # Copy files
        cert_dst = self.cert_dir / "server.crt"
        key_dst = self.cert_dir / "server.key"
        
        try:
            shutil.copy2(cert_src, cert_dst)
            shutil.copy2(key_src, key_dst)
            
            # Set appropriate permissions
            key_dst.chmod(0o600)
            cert_dst.chmod(0o644)
            
            print(f"✓ Production certificates installed:")
            print(f"  Certificate: {cert_dst}")
            print(f"  Private key: {key_dst}")
            print(f"  {cert_info.get('subject', '')}")
            print(f"  {cert_info.get('dates', '')}")
            
            return True, "Production certificates installed successfully"
            
        except Exception as e:
            return False, f"Failed to copy certificates: {e}"
    
    def check_cert_status(self) -> None:
        """Check the status of installed certificates."""
        print("\n=== Certificate Status ===\n")
        
        cert_file = self.cert_dir / "server.crt"
        key_file = self.cert_dir / "server.key"
        dhparam_file = self.cert_dir / "dhparam.pem"
        
        # Check certificate
        if cert_file.exists():
            info = self.validate_certificate(cert_file)
            if info["valid"]:
                print(f"✓ Certificate found: {cert_file}")
                print(f"  {info.get('subject', '')}")
                print(f"  {info.get('dates', '')}")
                if info.get("expired", False):
                    print("  ⚠️  WARNING: Certificate has expired!")
            else:
                print(f"✗ Invalid certificate: {info.get('error', 'Unknown error')}")
        else:
            print("✗ No certificate found")
        
        # Check private key
        if key_file.exists():
            print(f"✓ Private key found: {key_file}")
            # Check permissions
            mode = oct(key_file.stat().st_mode)[-3:]
            if mode != '600':
                print(f"  ⚠️  WARNING: Insecure permissions ({mode}), should be 600")
        else:
            print("✗ No private key found")
        
        # Check DH parameters
        if dhparam_file.exists():
            print(f"✓ DH parameters found: {dhparam_file}")
        else:
            print("⚠️  No DH parameters found (optional but recommended)")
    
    def create_readme(self) -> None:
        """Create README for the certs directory."""
        readme_content = """# SSL Certificates Directory

This directory contains SSL certificates for the DEAN system.

## Files

- `server.crt` - SSL certificate
- `server.key` - Private key (keep secure!)
- `dhparam.pem` - Diffie-Hellman parameters (optional, for enhanced security)

## Development Certificates

For development, self-signed certificates are generated automatically by the
`manage_ssl_certificates.py` script.

## Production Certificates

For production deployment, you should use certificates from a trusted CA.
Options include:
1. Let's Encrypt (free, automated)
2. Commercial CA (DigiCert, Comodo, etc.)
3. Internal CA (for corporate deployments)

### Installing Production Certificates

```bash
python scripts/manage_ssl_certificates.py --setup-production \\
    --cert /path/to/your/certificate.crt \\
    --key /path/to/your/private.key
```

## Security Notes

1. **Never commit private keys to version control**
2. Set appropriate permissions (600 for private keys)
3. Use strong key sizes (2048-bit RSA minimum)
4. Regularly renew certificates before expiration
5. Consider using Let's Encrypt for automatic renewal

## Certificate Requirements

- Common Name (CN) should match your domain
- Include Subject Alternative Names (SAN) for all domains
- Use SHA-256 or stronger for signature algorithm
- Valid for at least 90 days (1 year recommended)
"""
        readme_file = self.cert_dir / "README.md"
        readme_file.write_text(readme_content)
        print(f"✓ Created {readme_file}")
    
    def create_gitignore(self) -> None:
        """Create .gitignore for the certs directory."""
        gitignore_content = """# Ignore all certificate files
*.crt
*.key
*.pem
*.p12
*.pfx

# But track the README
!README.md
!.gitignore
"""
        gitignore_file = self.cert_dir / ".gitignore"
        gitignore_file.write_text(gitignore_content)
        print(f"✓ Created {gitignore_file}")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="SSL Certificate Management for DEAN",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate self-signed certificate for development
  %(prog)s --generate-dev
  
  # Generate with custom hostname
  %(prog)s --generate-dev --hostname myapp.local
  
  # Set up production certificates
  %(prog)s --setup-production --cert /path/to/cert.crt --key /path/to/key.pem
  
  # Check certificate status
  %(prog)s --status
  
  # Generate DH parameters
  %(prog)s --generate-dhparam
"""
    )
    
    parser.add_argument('--cert-dir', default='certs',
                       help='Certificate directory (default: certs)')
    parser.add_argument('--generate-dev', action='store_true',
                       help='Generate self-signed certificate for development')
    parser.add_argument('--hostname', default='localhost',
                       help='Hostname for certificate (default: localhost)')
    parser.add_argument('--days', type=int, default=365,
                       help='Certificate validity in days (default: 365)')
    parser.add_argument('--setup-production', action='store_true',
                       help='Set up production certificates')
    parser.add_argument('--cert', help='Path to production certificate')
    parser.add_argument('--key', help='Path to production private key')
    parser.add_argument('--generate-dhparam', action='store_true',
                       help='Generate Diffie-Hellman parameters')
    parser.add_argument('--dhparam-bits', type=int, default=2048,
                       help='DH parameter size (default: 2048)')
    parser.add_argument('--status', action='store_true',
                       help='Check certificate status')
    
    args = parser.parse_args()
    
    # Initialize certificate manager
    cert_dir = Path(args.cert_dir).resolve()
    manager = CertificateManager(cert_dir)
    
    # Create README and .gitignore if they don't exist
    readme_file = cert_dir / "README.md"
    if not readme_file.exists():
        manager.create_readme()
    
    gitignore_file = cert_dir / ".gitignore"
    if not gitignore_file.exists():
        manager.create_gitignore()
    
    # Execute requested action
    if args.generate_dev:
        success, message = manager.generate_self_signed_cert(
            hostname=args.hostname,
            days=args.days
        )
        if not success:
            print(f"✗ {message}", file=sys.stderr)
            return 1
            
    elif args.setup_production:
        if not args.cert or not args.key:
            print("✗ Both --cert and --key are required for production setup",
                  file=sys.stderr)
            return 1
        
        success, message = manager.setup_production_certs(args.cert, args.key)
        if not success:
            print(f"✗ {message}", file=sys.stderr)
            return 1
            
    elif args.generate_dhparam:
        success, message = manager.generate_dhparam(args.dhparam_bits)
        if not success:
            print(f"✗ {message}", file=sys.stderr)
            return 1
            
    elif args.status:
        manager.check_cert_status()
        
    else:
        # Default action: check status
        manager.check_cert_status()
        print("\nUse --help for more options")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())