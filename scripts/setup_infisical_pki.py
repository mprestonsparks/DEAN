#!/usr/bin/env python3
"""Set up PKI infrastructure in Infisical for DEAN mTLS."""

import os
import sys
import json
import requests
from datetime import datetime, timedelta
from cryptography import x509
from cryptography.x509.oid import NameOID, ExtensionOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from typing import Tuple, Optional

class InfisicalPKIManager:
    """Manages PKI infrastructure in Infisical."""
    
    def __init__(self, base_url: str, access_token: str, workspace_id: str):
        self.base_url = base_url.rstrip('/')
        self.access_token = access_token
        self.workspace_id = workspace_id
        self.headers = {"Authorization": f"Bearer {self.access_token}"}
        
    def generate_key_pair(self, key_size: int = 4096) -> Tuple[rsa.RSAPrivateKey, bytes]:
        """Generate RSA key pair."""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=key_size
        )
        
        private_key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        return private_key, private_key_pem
    
    def create_root_ca(self) -> Tuple[x509.Certificate, bytes, bytes]:
        """Create DEAN Root Certificate Authority."""
        print("\n🏛️ Creating DEAN Root CA...")
        
        # Generate key pair
        private_key, private_key_pem = self.generate_key_pair()
        
        # Create certificate
        subject = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "California"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "DEAN System"),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "Security"),
            x509.NameAttribute(NameOID.COMMON_NAME, "DEAN Root CA"),
        ])
        
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            subject  # Self-signed
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.utcnow()
        ).not_valid_after(
            datetime.utcnow() + timedelta(days=3650)  # 10 years
        ).add_extension(
            x509.BasicConstraints(ca=True, path_length=None),
            critical=True,
        ).add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_cert_sign=True,
                crl_sign=True,
                key_encipherment=False,
                content_commitment=False,
                data_encipherment=False,
                key_agreement=False,
                encipher_only=False,
                decipher_only=False
            ),
            critical=True,
        ).add_extension(
            x509.SubjectKeyIdentifier.from_public_key(private_key.public_key()),
            critical=False,
        ).sign(private_key, hashes.SHA256())
        
        cert_pem = cert.public_bytes(serialization.Encoding.PEM)
        
        print("✅ Root CA created")
        return cert, cert_pem, private_key_pem
    
    def create_intermediate_ca(self, root_cert: x509.Certificate, root_key_pem: bytes) -> Tuple[x509.Certificate, bytes, bytes]:
        """Create DEAN Intermediate CA for service certificates."""
        print("\n🏛️ Creating DEAN Intermediate CA...")
        
        # Load root private key
        root_key = serialization.load_pem_private_key(root_key_pem, password=None)
        
        # Generate key pair for intermediate CA
        private_key, private_key_pem = self.generate_key_pair()
        
        # Create certificate
        subject = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "California"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "DEAN System"),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "Services"),
            x509.NameAttribute(NameOID.COMMON_NAME, "DEAN Services CA"),
        ])
        
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            root_cert.subject
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.utcnow()
        ).not_valid_after(
            datetime.utcnow() + timedelta(days=1825)  # 5 years
        ).add_extension(
            x509.BasicConstraints(ca=True, path_length=0),
            critical=True,
        ).add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_cert_sign=True,
                crl_sign=False,
                key_encipherment=False,
                content_commitment=False,
                data_encipherment=False,
                key_agreement=False,
                encipher_only=False,
                decipher_only=False
            ),
            critical=True,
        ).add_extension(
            x509.SubjectKeyIdentifier.from_public_key(private_key.public_key()),
            critical=False,
        ).add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(root_key.public_key()),
            critical=False,
        ).sign(root_key, hashes.SHA256())
        
        cert_pem = cert.public_bytes(serialization.Encoding.PEM)
        
        print("✅ Intermediate CA created")
        return cert, cert_pem, private_key_pem
    
    def create_service_certificate(self, service_name: str, intermediate_cert: x509.Certificate, 
                                 intermediate_key_pem: bytes) -> Tuple[bytes, bytes]:
        """Create certificate for a DEAN service."""
        print(f"  📜 Creating certificate for {service_name}...")
        
        # Load intermediate private key
        intermediate_key = serialization.load_pem_private_key(intermediate_key_pem, password=None)
        
        # Generate key pair for service
        private_key, private_key_pem = self.generate_key_pair(2048)  # Smaller key for services
        
        # Create certificate
        subject = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "California"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "DEAN System"),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "Services"),
            x509.NameAttribute(NameOID.COMMON_NAME, f"{service_name}.dean.local"),
        ])
        
        # Add SANs for service
        san_list = [
            x509.DNSName(f"{service_name}.dean.local"),
            x509.DNSName(f"{service_name}"),
            x509.DNSName("localhost"),
            x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
            x509.IPAddress(ipaddress.IPv4Address("10.7.0.2"))
        ]
        
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            intermediate_cert.subject
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.utcnow()
        ).not_valid_after(
            datetime.utcnow() + timedelta(days=365)  # 1 year
        ).add_extension(
            x509.BasicConstraints(ca=False, path_length=None),
            critical=True,
        ).add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_cert_sign=False,
                crl_sign=False,
                key_encipherment=True,
                content_commitment=False,
                data_encipherment=False,
                key_agreement=False,
                encipher_only=False,
                decipher_only=False
            ),
            critical=True,
        ).add_extension(
            x509.ExtendedKeyUsage([
                x509.oid.ExtendedKeyUsageOID.SERVER_AUTH,
                x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH
            ]),
            critical=True,
        ).add_extension(
            x509.SubjectAlternativeName(san_list),
            critical=False,
        ).add_extension(
            x509.SubjectKeyIdentifier.from_public_key(private_key.public_key()),
            critical=False,
        ).add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(intermediate_key.public_key()),
            critical=False,
        ).sign(intermediate_key, hashes.SHA256())
        
        cert_pem = cert.public_bytes(serialization.Encoding.PEM)
        
        print(f"    ✅ Certificate created for {service_name}")
        return cert_pem, private_key_pem
    
    def store_pki_in_infisical(self, root_cert_pem: bytes, root_key_pem: bytes,
                              intermediate_cert_pem: bytes, intermediate_key_pem: bytes,
                              service_certs: Dict[str, Tuple[bytes, bytes]]) -> None:
        """Store all PKI materials in Infisical."""
        print("\n💾 Storing PKI materials in Infisical...")
        
        # Store root CA
        self.create_secret("/dean/pki/ca", "ROOT_CA_CERT", root_cert_pem.decode())
        self.create_secret("/dean/pki/ca", "ROOT_CA_KEY", root_key_pem.decode())
        
        # Store intermediate CA
        self.create_secret("/dean/pki/ca", "INTERMEDIATE_CA_CERT", intermediate_cert_pem.decode())
        self.create_secret("/dean/pki/ca", "INTERMEDIATE_CA_KEY", intermediate_key_pem.decode())
        
        # Store CA bundle
        ca_bundle = root_cert_pem + intermediate_cert_pem
        self.create_secret("/dean/pki/ca", "CA_BUNDLE", ca_bundle.decode())
        
        # Store service certificates
        for service_name, (cert_pem, key_pem) in service_certs.items():
            path = f"/dean/pki/services/{service_name}"
            self.create_secret(path, "TLS_CERT", cert_pem.decode())
            self.create_secret(path, "TLS_KEY", key_pem.decode())
            self.create_secret(path, "TLS_CA_BUNDLE", ca_bundle.decode())
        
        print("✅ All PKI materials stored in Infisical")
    
    def create_secret(self, path: str, key: str, value: str) -> bool:
        """Create a secret in Infisical."""
        response = requests.post(
            f"{self.base_url}/api/v3/secrets",
            headers=self.headers,
            json={
                "workspaceId": self.workspace_id,
                "environment": "production",
                "secretPath": path,
                "secretKey": key,
                "secretValue": value,
                "secretComment": f"PKI material created on {datetime.utcnow().isoformat()}"
            }
        )
        
        return response.status_code in [200, 201]

def main():
    """Main PKI setup function."""
    import ipaddress
    
    print("🔐 DEAN PKI Infrastructure Setup")
    print("================================")
    
    # This should be run after setup_infisical_secrets.py
    # Get workspace ID from previous setup or environment
    workspace_id = os.getenv("INFISICAL_DEAN_WORKSPACE_ID")
    if not workspace_id:
        print("❌ Workspace ID not found. Run setup_infisical_secrets.py first.")
        sys.exit(1)
    
    # Get access token (in production, use service token)
    # For now, we'll need to login again
    infisical_url = "http://10.7.0.2:8090"
    admin_email = "admin@dean-system.local"
    admin_password = "YlncUtqCtu0LasRzwEG_VxNN"
    
    # Login to get token
    response = requests.post(
        f"{infisical_url}/api/v1/auth/login",
        json={
            "email": admin_email,
            "password": admin_password
        }
    )
    
    if response.status_code != 200:
        print("❌ Failed to login to Infisical")
        sys.exit(1)
    
    access_token = response.json().get("accessToken")
    
    # Initialize PKI manager
    pki_manager = InfisicalPKIManager(infisical_url, access_token, workspace_id)
    
    # Create PKI hierarchy
    root_cert, root_cert_pem, root_key_pem = pki_manager.create_root_ca()
    intermediate_cert, intermediate_cert_pem, intermediate_key_pem = pki_manager.create_intermediate_ca(
        root_cert, root_key_pem
    )
    
    # Create service certificates
    print("\n📜 Creating service certificates...")
    services = [
        "dean-orchestration",
        "indexagent",
        "evolution-api",
        "airflow-webserver",
        "airflow-scheduler",
        "prometheus",
        "grafana"
    ]
    
    service_certs = {}
    for service in services:
        cert_pem, key_pem = pki_manager.create_service_certificate(
            service, intermediate_cert, intermediate_key_pem
        )
        service_certs[service] = (cert_pem, key_pem)
    
    # Store everything in Infisical
    pki_manager.store_pki_in_infisical(
        root_cert_pem, root_key_pem,
        intermediate_cert_pem, intermediate_key_pem,
        service_certs
    )
    
    # Export root CA for distribution
    ca_bundle_path = "dean-ca-bundle.pem"
    with open(ca_bundle_path, "wb") as f:
        f.write(root_cert_pem + intermediate_cert_pem)
    
    print(f"\n✅ PKI setup complete!")
    print(f"\n📁 CA bundle exported to: {ca_bundle_path}")
    print("\n🔧 Next steps:")
    print("1. Distribute CA bundle to all DEAN nodes")
    print("2. Configure services to use certificates from Infisical")
    print("3. Enable mTLS in service configurations")

if __name__ == "__main__":
    main()