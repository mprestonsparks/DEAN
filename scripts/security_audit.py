#!/usr/bin/env python3
"""
DEAN Security Audit Script

Performs automated security checks on the DEAN orchestration system.
Checks for common vulnerabilities, misconfigurations, and security best practices.
"""

import os
import sys
import re
import yaml
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Any

# ANSI color codes
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'  # No Color


class SecurityAuditor:
    """Performs security audit on DEAN system."""
    
    def __init__(self, root_path: str):
        self.root_path = Path(root_path)
        self.issues = []
        self.warnings = []
        self.passed = []
        
    def audit(self) -> Dict[str, Any]:
        """Run complete security audit."""
        print(f"{BLUE}{'='*60}{NC}")
        print(f"{BLUE}DEAN Security Audit{NC}")
        print(f"{BLUE}{'='*60}{NC}\n")
        
        # Run all checks
        self.check_default_credentials()
        self.check_jwt_configuration()
        self.check_ssl_configuration()
        self.check_exposed_secrets()
        self.check_docker_security()
        self.check_api_security()
        self.check_dependencies()
        self.check_file_permissions()
        self.check_authentication_implementation()
        self.check_logging_security()
        
        # Generate report
        return self.generate_report()
    
    def check_default_credentials(self):
        """Check for default credentials in configuration."""
        print(f"\n{YELLOW}1. Checking for default credentials...{NC}")
        
        default_creds = [
            ("admin", "admin123"),
            ("user", "user123"),
            ("viewer", "viewer123"),
            ("airflow", "airflow"),
            ("postgres", "postgres"),
        ]
        
        # Check auth_manager.py for default users
        auth_manager = self.root_path / "src" / "auth" / "auth_manager.py"
        if auth_manager.exists():
            content = auth_manager.read_text()
            for username, password in default_creds:
                if f'"{username}"' in content and f'"{password}"' in content:
                    self.issues.append(
                        f"Default credentials found: {username}:{password} in auth_manager.py"
                    )
        
        # Check configuration files
        config_patterns = ["**/*.yaml", "**/*.yml", "**/*.env", "**/*.json"]
        for pattern in config_patterns:
            for config_file in self.root_path.rglob(pattern):
                if self._is_ignored_path(config_file):
                    continue
                    
                content = config_file.read_text()
                for username, password in default_creds:
                    if password in content:
                        self.warnings.append(
                            f"Possible default password '{password}' in {config_file.relative_to(self.root_path)}"
                        )
        
        if not self.issues and not self.warnings:
            self.passed.append("No hardcoded default credentials found in code")
    
    def check_jwt_configuration(self):
        """Check JWT secret configuration."""
        print(f"\n{YELLOW}2. Checking JWT configuration...{NC}")
        
        # Check for weak JWT secrets
        weak_secrets = [
            "secret", "your-secret-key", "change-me", "changeme",
            "your-secret-key-change-in-production", "test-secret"
        ]
        
        for pattern in ["**/*.py", "**/*.env*", "**/*.yaml", "**/*.yml"]:
            for file_path in self.root_path.rglob(pattern):
                if self._is_ignored_path(file_path):
                    continue
                    
                content = file_path.read_text()
                for weak_secret in weak_secrets:
                    if weak_secret in content.lower():
                        if "test" not in str(file_path) and "example" not in str(file_path):
                            self.issues.append(
                                f"Weak JWT secret '{weak_secret}' found in {file_path.relative_to(self.root_path)}"
                            )
        
        # Check JWT algorithm
        auth_files = self.root_path.rglob("**/auth*.py")
        for auth_file in auth_files:
            if self._is_ignored_path(auth_file):
                continue
                
            content = auth_file.read_text()
            if "HS256" in content:
                self.passed.append("JWT using HS256 algorithm (acceptable for symmetric keys)")
            elif "none" in content.lower() and "algorithm" in content:
                self.issues.append(f"Potentially unsafe JWT algorithm in {auth_file.relative_to(self.root_path)}")
    
    def check_ssl_configuration(self):
        """Check SSL/TLS configuration."""
        print(f"\n{YELLOW}3. Checking SSL/TLS configuration...{NC}")
        
        # Check for SSL in docker-compose files
        compose_files = list(self.root_path.rglob("**/docker-compose*.yml"))
        for compose_file in compose_files:
            content = compose_file.read_text()
            if "443" in content or "https" in content.lower():
                self.passed.append(f"HTTPS configured in {compose_file.name}")
            else:
                self.warnings.append(f"No HTTPS configuration found in {compose_file.name}")
        
        # Check for SSL certificates
        cert_patterns = ["**/*.pem", "**/*.crt", "**/*.key"]
        certs_found = False
        for pattern in cert_patterns:
            if list(self.root_path.rglob(pattern)):
                certs_found = True
                break
        
        if certs_found:
            self.warnings.append("SSL certificate files found - ensure they're not committed to Git")
        
        # Check Nginx configuration
        nginx_configs = list(self.root_path.rglob("**/nginx*.conf"))
        for nginx_conf in nginx_configs:
            content = nginx_conf.read_text()
            if "ssl_protocols" in content:
                if "TLSv1.2" in content or "TLSv1.3" in content:
                    self.passed.append("Modern TLS protocols configured in Nginx")
                else:
                    self.issues.append("Outdated SSL/TLS protocols in Nginx configuration")
    
    def check_exposed_secrets(self):
        """Check for exposed secrets and credentials."""
        print(f"\n{YELLOW}4. Checking for exposed secrets...{NC}")
        
        secret_patterns = [
            r'(api[_\-]?key|apikey)\s*[:=]\s*["\']([^"\']+)["\']',
            r'(secret[_\-]?key|secretkey)\s*[:=]\s*["\']([^"\']+)["\']',
            r'(password|passwd|pwd)\s*[:=]\s*["\']([^"\']+)["\']',
            r'(token)\s*[:=]\s*["\']([^"\']+)["\']',
            r'(aws[_\-]?access[_\-]?key[_\-]?id)\s*[:=]\s*["\']([^"\']+)["\']',
            r'(aws[_\-]?secret[_\-]?access[_\-]?key)\s*[:=]\s*["\']([^"\']+)["\']',
        ]
        
        for pattern in ["**/*.py", "**/*.js", "**/*.yml", "**/*.yaml", "**/*.json"]:
            for file_path in self.root_path.rglob(pattern):
                if self._is_ignored_path(file_path):
                    continue
                    
                content = file_path.read_text()
                for secret_pattern in secret_patterns:
                    matches = re.finditer(secret_pattern, content, re.IGNORECASE)
                    for match in matches:
                        secret_value = match.group(2)
                        # Skip obvious placeholders
                        if not any(placeholder in secret_value.lower() for placeholder in 
                                 ["xxx", "your", "change", "example", "placeholder", "<", ">"]):
                            if len(secret_value) > 6:  # Skip short values
                                self.warnings.append(
                                    f"Possible exposed secret in {file_path.relative_to(self.root_path)}: {match.group(1)}"
                                )
    
    def check_docker_security(self):
        """Check Docker security configuration."""
        print(f"\n{YELLOW}5. Checking Docker security...{NC}")
        
        dockerfiles = list(self.root_path.rglob("**/Dockerfile*"))
        for dockerfile in dockerfiles:
            content = dockerfile.read_text()
            
            # Check for running as root
            if "USER" not in content:
                self.warnings.append(f"{dockerfile.name} runs as root user")
            else:
                self.passed.append(f"{dockerfile.name} specifies non-root user")
            
            # Check for latest tags
            if ":latest" in content:
                self.warnings.append(f"{dockerfile.name} uses :latest tag (not recommended for production)")
            
            # Check for COPY vs ADD
            if "ADD http" in content or "ADD git" in content:
                self.issues.append(f"{dockerfile.name} uses ADD for remote resources (security risk)")
    
    def check_api_security(self):
        """Check API security implementation."""
        print(f"\n{YELLOW}6. Checking API security...{NC}")
        
        # Check for security headers
        api_files = list(self.root_path.rglob("**/app.py")) + list(self.root_path.rglob("**/main.py"))
        for api_file in api_files:
            if self._is_ignored_path(api_file):
                continue
                
            content = api_file.read_text()
            
            # Check CORS configuration
            if "CORSMiddleware" in content:
                if 'allow_origins=["*"]' in content or "allow_origins=['*']" in content:
                    self.warnings.append(f"Overly permissive CORS in {api_file.relative_to(self.root_path)}")
                else:
                    self.passed.append(f"CORS properly configured in {api_file.relative_to(self.root_path)}")
            
            # Check for rate limiting
            if "RateLimiter" in content or "rate_limit" in content.lower():
                self.passed.append(f"Rate limiting implemented in {api_file.relative_to(self.root_path)}")
            
            # Check for authentication decorators
            if "@require_auth" in content or "Depends(security)" in content:
                self.passed.append(f"Authentication required in {api_file.relative_to(self.root_path)}")
    
    def check_dependencies(self):
        """Check for vulnerable dependencies."""
        print(f"\n{YELLOW}7. Checking dependencies...{NC}")
        
        requirements_files = list(self.root_path.rglob("**/requirements*.txt"))
        
        # Known vulnerable versions (simplified check)
        vulnerable_packages = {
            "flask": ["<2.0.0", "Security fixes in 2.0+"],
            "django": ["<3.2", "Security fixes in 3.2+"],
            "requests": ["<2.26.0", "Security fixes in 2.26+"],
            "urllib3": ["<1.26.5", "Security fixes in 1.26.5+"],
            "pyyaml": ["<5.4", "Security fixes in 5.4+"],
        }
        
        for req_file in requirements_files:
            content = req_file.read_text()
            for package, (version, reason) in vulnerable_packages.items():
                if package in content.lower():
                    self.warnings.append(
                        f"Check {package} version in {req_file.name} - {reason}"
                    )
        
        # Check for pip audit file
        if not list(self.root_path.rglob("**/.pip-audit*")):
            self.warnings.append("Consider using pip-audit for vulnerability scanning")
    
    def check_file_permissions(self):
        """Check file permissions for sensitive files."""
        print(f"\n{YELLOW}8. Checking file permissions...{NC}")
        
        sensitive_patterns = ["**/*.key", "**/*.pem", "**/.env*", "**/secrets*"]
        
        for pattern in sensitive_patterns:
            for sensitive_file in self.root_path.rglob(pattern):
                if self._is_ignored_path(sensitive_file):
                    continue
                    
                if sensitive_file.is_file():
                    mode = oct(sensitive_file.stat().st_mode)[-3:]
                    if mode != "600" and mode != "400":
                        self.warnings.append(
                            f"Permissive permissions ({mode}) on {sensitive_file.relative_to(self.root_path)}"
                        )
    
    def check_authentication_implementation(self):
        """Check authentication implementation details."""
        print(f"\n{YELLOW}9. Checking authentication implementation...{NC}")
        
        auth_middleware = self.root_path / "src" / "auth" / "auth_middleware.py"
        if auth_middleware.exists():
            content = auth_middleware.read_text()
            
            # Check for timing attack prevention
            if "secrets.compare_digest" in content or "hmac.compare_digest" in content:
                self.passed.append("Timing-attack resistant comparison implemented")
            
            # Check for proper error messages
            if "Invalid username or password" in content:
                self.passed.append("Generic error messages for failed authentication")
            elif "User not found" in content or "Wrong password" in content:
                self.issues.append("Authentication errors reveal too much information")
            
            # Check for account lockout
            if "lockout" in content.lower() or "failed_attempts" in content:
                self.passed.append("Account lockout mechanism implemented")
    
    def check_logging_security(self):
        """Check for security in logging."""
        print(f"\n{YELLOW}10. Checking logging security...{NC}")
        
        log_patterns = ["**/*.py"]
        sensitive_log_terms = ["password", "token", "secret", "key", "credit"]
        
        for pattern in log_patterns:
            for file_path in self.root_path.rglob(pattern):
                if self._is_ignored_path(file_path):
                    continue
                    
                content = file_path.read_text()
                lines = content.split('\n')
                
                for i, line in enumerate(lines):
                    if any(log_func in line for log_func in ["logger.", "log.", "print("]):
                        for term in sensitive_log_terms:
                            if term in line.lower() and not "error" in line:
                                # Check if it's actually logging sensitive data
                                if "{" in line and term in line:
                                    self.warnings.append(
                                        f"Possible sensitive data in logs: {file_path.relative_to(self.root_path)}:{i+1}"
                                    )
    
    def _is_ignored_path(self, path: Path) -> bool:
        """Check if path should be ignored."""
        ignored_dirs = ["venv", "env", ".git", "__pycache__", "node_modules", ".pytest_cache"]
        return any(ignored in str(path) for ignored in ignored_dirs)
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate security audit report."""
        print(f"\n{BLUE}{'='*60}{NC}")
        print(f"{BLUE}Security Audit Summary{NC}")
        print(f"{BLUE}{'='*60}{NC}\n")
        
        # Print results
        print(f"{RED}Critical Issues: {len(self.issues)}{NC}")
        for issue in self.issues:
            print(f"  ❌ {issue}")
        
        print(f"\n{YELLOW}Warnings: {len(self.warnings)}{NC}")
        for warning in self.warnings[:10]:  # Limit output
            print(f"  ⚠️  {warning}")
        if len(self.warnings) > 10:
            print(f"  ... and {len(self.warnings) - 10} more warnings")
        
        print(f"\n{GREEN}Passed Checks: {len(self.passed)}{NC}")
        for check in self.passed:
            print(f"  ✅ {check}")
        
        # Calculate score
        total_checks = len(self.issues) + len(self.warnings) + len(self.passed)
        if total_checks > 0:
            score = (len(self.passed) / total_checks) * 100
        else:
            score = 0
        
        print(f"\n{BLUE}Security Score: {score:.1f}%{NC}")
        
        # Recommendations
        print(f"\n{BLUE}Recommendations:{NC}")
        recommendations = []
        
        if any("default" in issue.lower() for issue in self.issues):
            recommendations.append("Change all default credentials before deployment")
        
        if any("jwt" in issue.lower() for issue in self.issues):
            recommendations.append("Generate strong JWT secret key for production")
        
        if any("https" not in warning for warning in self.warnings):
            recommendations.append("Enable HTTPS/TLS for all services")
        
        if not recommendations:
            recommendations.append("Run regular security audits")
            recommendations.append("Keep dependencies updated")
            recommendations.append("Implement security monitoring")
        
        for rec in recommendations:
            print(f"  • {rec}")
        
        # Save report
        report = {
            "timestamp": datetime.now().isoformat(),
            "score": score,
            "issues": self.issues,
            "warnings": self.warnings,
            "passed": self.passed,
            "recommendations": recommendations
        }
        
        report_path = self.root_path / f"security_audit_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n{BLUE}Full report saved to: {report_path}{NC}")
        
        return report


def main():
    """Run security audit."""
    # Get DEAN root directory
    script_dir = Path(__file__).parent
    dean_root = script_dir.parent
    
    # Run audit
    auditor = SecurityAuditor(dean_root)
    report = auditor.audit()
    
    # Exit with appropriate code
    if report["issues"]:
        sys.exit(1)
    elif report["warnings"]:
        sys.exit(0)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()