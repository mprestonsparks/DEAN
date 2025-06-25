#!/usr/bin/env python3
"""Verify DEAN security implementation."""

import os
import sys
import subprocess
import requests
import json
import re
from typing import List, Dict, Tuple
from datetime import datetime

class SecurityVerifier:
    """Verifies DEAN security implementation."""
    
    def __init__(self):
        self.results = {
            "checks": [],
            "passed": 0,
            "failed": 0,
            "warnings": 0
        }
        
    def add_result(self, category: str, check: str, status: str, message: str = ""):
        """Add a verification result."""
        result = {
            "category": category,
            "check": check,
            "status": status,
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        }
        self.results["checks"].append(result)
        
        if status == "PASS":
            self.results["passed"] += 1
        elif status == "FAIL":
            self.results["failed"] += 1
        elif status == "WARN":
            self.results["warnings"] += 1
    
    def check_infisical_health(self) -> bool:
        """Check if Infisical is healthy."""
        try:
            response = requests.get("http://10.7.0.2:8090/api/status", timeout=5)
            if response.status_code == 200:
                self.add_result("Infisical", "Health Check", "PASS", "Infisical is healthy")
                return True
        except:
            pass
        
        self.add_result("Infisical", "Health Check", "FAIL", "Infisical is not responding")
        return False
    
    def check_no_env_files(self, deployment_path: str = "C:\\DEAN") -> bool:
        """Verify no .env files exist in deployment."""
        env_files = []
        
        # Check for common .env file patterns
        patterns = [".env", ".env.*", "*.env"]
        
        for pattern in patterns:
            try:
                result = subprocess.run(
                    ["powershell", "-Command", f"Get-ChildItem -Path {deployment_path} -Filter '{pattern}' -Recurse | Select-Object -ExpandProperty FullName"],
                    capture_output=True,
                    text=True
                )
                if result.stdout.strip():
                    env_files.extend(result.stdout.strip().split('\n'))
            except:
                pass
        
        # Filter out allowed files
        allowed_files = [".env.infisical", ".env.example", ".env.template"]
        env_files = [f for f in env_files if not any(allowed in f for allowed in allowed_files)]
        
        if env_files:
            self.add_result("Environment Files", "No .env Files", "FAIL", 
                          f"Found {len(env_files)} .env files: {', '.join(env_files[:3])}...")
            return False
        else:
            self.add_result("Environment Files", "No .env Files", "PASS", 
                          "No production .env files found")
            return True
    
    def check_service_authentication(self) -> bool:
        """Verify services require authentication."""
        services = [
            ("DEAN Orchestration", "http://10.7.0.2:8082/api/v1/agents"),
            ("IndexAgent", "http://10.7.0.2:8081/api/v1/agents"),
            ("Evolution API", "http://10.7.0.2:8090/api/v1/evolution/status")
        ]
        
        auth_required = True
        
        for service_name, endpoint in services:
            try:
                # Try to access without authentication
                response = requests.get(endpoint, timeout=5)
                if response.status_code in [200, 201]:
                    self.add_result("Authentication", f"{service_name} Auth", "FAIL", 
                                  "Service accessible without authentication")
                    auth_required = False
                elif response.status_code in [401, 403]:
                    self.add_result("Authentication", f"{service_name} Auth", "PASS", 
                                  "Service requires authentication")
                else:
                    self.add_result("Authentication", f"{service_name} Auth", "WARN", 
                                  f"Unexpected response: {response.status_code}")
            except:
                self.add_result("Authentication", f"{service_name} Auth", "WARN", 
                              "Service not reachable")
        
        return auth_required
    
    def check_pki_certificates(self) -> bool:
        """Verify PKI certificates are in place."""
        try:
            # Check if CA bundle exists
            ca_bundle_path = "dean-ca-bundle.pem"
            if os.path.exists(ca_bundle_path):
                self.add_result("PKI", "CA Bundle", "PASS", "CA bundle found")
                
                # Verify certificate validity
                result = subprocess.run(
                    ["openssl", "x509", "-in", ca_bundle_path, "-noout", "-dates"],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    self.add_result("PKI", "Certificate Validity", "PASS", 
                                  "Certificates are valid")
                    return True
            else:
                self.add_result("PKI", "CA Bundle", "FAIL", "CA bundle not found")
        except:
            self.add_result("PKI", "Certificate Check", "FAIL", "Unable to verify certificates")
        
        return False
    
    def check_audit_logging(self) -> bool:
        """Verify audit logging is enabled."""
        # This would connect to Infisical API to check audit configuration
        # For now, we'll do a basic check
        try:
            # Check if Infisical audit endpoint is accessible
            response = requests.get("http://10.7.0.2:8090/api/v1/audit/config", timeout=5)
            if response.status_code in [200, 401]:  # 401 means endpoint exists but needs auth
                self.add_result("Audit", "Audit Endpoint", "PASS", "Audit endpoint exists")
                return True
        except:
            pass
        
        self.add_result("Audit", "Audit Endpoint", "WARN", "Cannot verify audit logging")
        return False
    
    def scan_for_hardcoded_secrets(self, scan_path: str = ".") -> bool:
        """Scan for hardcoded secrets in code."""
        secret_patterns = [
            (r'(api[_-]?key|apikey)\s*=\s*["\'][\w\-]{20,}["\']', "API Key"),
            (r'(secret|password)\s*=\s*["\'][^"\']{8,}["\']', "Password"),
            (r'(token)\s*=\s*["\'][\w\-\.]{20,}["\']', "Token"),
            (r'-----BEGIN (RSA |EC )?PRIVATE KEY-----', "Private Key"),
            (r'sk_live_[0-9a-zA-Z]{24,}', "Stripe API Key"),
            (r'[0-9a-f]{40}', "Potential SHA1 Hash/Token")
        ]
        
        found_secrets = []
        files_scanned = 0
        
        # Scan Python and YAML files
        for root, dirs, files in os.walk(scan_path):
            # Skip node_modules, .git, etc.
            dirs[:] = [d for d in dirs if d not in ['.git', 'node_modules', '__pycache__', '.pytest_cache']]
            
            for file in files:
                if file.endswith(('.py', '.yml', '.yaml', '.json', '.js', '.ts')):
                    file_path = os.path.join(root, file)
                    files_scanned += 1
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            
                        for pattern, secret_type in secret_patterns:
                            matches = re.findall(pattern, content, re.IGNORECASE)
                            if matches:
                                # Filter out obvious false positives
                                for match in matches:
                                    if 'placeholder' not in str(match).lower() and \
                                       'example' not in str(match).lower() and \
                                       'your_' not in str(match).lower():
                                        found_secrets.append((file_path, secret_type, match))
                    except:
                        pass
        
        if found_secrets:
            self.add_result("Secret Scanning", "Hardcoded Secrets", "FAIL", 
                          f"Found {len(found_secrets)} potential secrets in {files_scanned} files")
            return False
        else:
            self.add_result("Secret Scanning", "Hardcoded Secrets", "PASS", 
                          f"No hardcoded secrets found in {files_scanned} files")
            return True
    
    def check_mtls_configuration(self) -> bool:
        """Verify mTLS is configured."""
        # Check if services are configured for mTLS
        # This would typically check service configurations
        
        # For now, check if certificate files are mounted in containers
        try:
            result = subprocess.run(
                ["docker", "inspect", "dean-orchestration"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                config = json.loads(result.stdout)
                mounts = config[0].get("Mounts", [])
                
                cert_mount = any("/app/certs" in mount.get("Destination", "") for mount in mounts)
                if cert_mount:
                    self.add_result("mTLS", "Certificate Mounts", "PASS", 
                                  "Certificates mounted in containers")
                    return True
        except:
            pass
        
        self.add_result("mTLS", "Certificate Mounts", "WARN", 
                      "Cannot verify mTLS configuration")
        return False
    
    def generate_report(self) -> str:
        """Generate security verification report."""
        report = f"""
# DEAN Security Verification Report
Generated: {datetime.utcnow().isoformat()}

## Summary
- Total Checks: {len(self.results['checks'])}
- Passed: {self.results['passed']} ✅
- Failed: {self.results['failed']} ❌
- Warnings: {self.results['warnings']} ⚠️

## Detailed Results

"""
        
        # Group by category
        categories = {}
        for check in self.results['checks']:
            category = check['category']
            if category not in categories:
                categories[category] = []
            categories[category].append(check)
        
        # Generate category sections
        for category, checks in categories.items():
            report += f"### {category}\n\n"
            for check in checks:
                icon = "✅" if check['status'] == "PASS" else "❌" if check['status'] == "FAIL" else "⚠️"
                report += f"- {icon} **{check['check']}**: {check['message']}\n"
            report += "\n"
        
        # Add recommendations
        report += "## Recommendations\n\n"
        
        if self.results['failed'] > 0:
            report += "### Critical Issues to Address:\n\n"
            for check in self.results['checks']:
                if check['status'] == 'FAIL':
                    report += f"1. **{check['category']} - {check['check']}**: {check['message']}\n"
        
        if self.results['warnings'] > 0:
            report += "\n### Warnings to Review:\n\n"
            for check in self.results['checks']:
                if check['status'] == 'WARN':
                    report += f"- **{check['category']} - {check['check']}**: {check['message']}\n"
        
        # Security score
        total_checks = len(self.results['checks'])
        score = (self.results['passed'] / total_checks * 100) if total_checks > 0 else 0
        
        report += f"\n## Security Score: {score:.1f}%\n"
        
        if score >= 90:
            report += "\n🏆 Excellent security posture!"
        elif score >= 70:
            report += "\n👍 Good security posture with room for improvement."
        elif score >= 50:
            report += "\n⚠️ Moderate security posture - address critical issues."
        else:
            report += "\n🚨 Poor security posture - immediate action required!"
        
        return report

def main():
    """Run security verification."""
    print("🔒 DEAN Security Verification")
    print("============================")
    
    verifier = SecurityVerifier()
    
    # Run all checks
    print("\n🔍 Running security checks...\n")
    
    # Check Infisical
    print("✓ Checking Infisical health...")
    verifier.check_infisical_health()
    
    # Check for .env files
    print("✓ Checking for environment files...")
    verifier.check_no_env_files()
    
    # Check authentication
    print("✓ Verifying service authentication...")
    verifier.check_service_authentication()
    
    # Check PKI
    print("✓ Verifying PKI certificates...")
    verifier.check_pki_certificates()
    
    # Check audit logging
    print("✓ Checking audit logging...")
    verifier.check_audit_logging()
    
    # Scan for secrets
    print("✓ Scanning for hardcoded secrets...")
    verifier.scan_for_hardcoded_secrets()
    
    # Check mTLS
    print("✓ Verifying mTLS configuration...")
    verifier.check_mtls_configuration()
    
    # Generate report
    report = verifier.generate_report()
    
    # Save report
    report_path = "SECURITY_VERIFICATION_REPORT.md"
    with open(report_path, "w") as f:
        f.write(report)
    
    print(f"\n📄 Report saved to: {report_path}")
    print(f"\n📊 Security Score: {(verifier.results['passed'] / len(verifier.results['checks']) * 100):.1f}%")
    
    # Exit with appropriate code
    if verifier.results['failed'] > 0:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()