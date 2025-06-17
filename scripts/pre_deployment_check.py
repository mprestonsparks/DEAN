#!/usr/bin/env python3
"""
Pre-deployment Validation Script for DEAN
Comprehensive checks before deploying to production.
"""

import os
import sys
import subprocess
import json
import yaml
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import hashlib
import socket

class PreDeploymentChecker:
    """Runs comprehensive pre-deployment checks."""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.passed = []
        self.root_dir = Path.cwd()
        
    def run_command(self, cmd: List[str], check: bool = True) -> Tuple[int, str, str]:
        """Run a command and return exit code, stdout, stderr."""
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=check)
            return result.returncode, result.stdout, result.stderr
        except subprocess.CalledProcessError as e:
            return e.returncode, e.stdout or "", e.stderr or ""
        except FileNotFoundError:
            return -1, "", f"Command not found: {cmd[0]}"
    
    def check_system_requirements(self) -> None:
        """Check system requirements."""
        print("🔍 Checking system requirements...")
        
        # Check Docker
        code, stdout, stderr = self.run_command(['docker', '--version'], check=False)
        if code == 0:
            self.passed.append(f"Docker installed: {stdout.strip()}")
        else:
            self.errors.append("Docker not installed or not in PATH")
        
        # Check Docker Compose
        code, stdout, stderr = self.run_command(['docker-compose', '--version'], check=False)
        if code == 0:
            self.passed.append(f"Docker Compose installed: {stdout.strip()}")
        else:
            self.errors.append("Docker Compose not installed or not in PATH")
        
        # Check Python version
        py_version = sys.version_info
        if py_version.major == 3 and py_version.minor >= 8:
            self.passed.append(f"Python version: {py_version.major}.{py_version.minor}.{py_version.micro}")
        else:
            self.warnings.append(f"Python 3.8+ recommended, found {py_version.major}.{py_version.minor}")
        
        # Check available disk space
        stat = os.statvfs(self.root_dir)
        free_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)
        if free_gb > 10:
            self.passed.append(f"Disk space available: {free_gb:.1f} GB")
        else:
            self.warnings.append(f"Low disk space: {free_gb:.1f} GB (recommend >10 GB)")
    
    def check_configuration_files(self) -> None:
        """Check configuration file integrity."""
        print("🔍 Checking configuration files...")
        
        required_files = [
            'docker-compose.prod.yml',
            'nginx/nginx.prod.conf',
            '.env.production.template',
            'postgres/00-create-schema.sql',
            'postgres/01-init-database.sql',
        ]
        
        for file in required_files:
            file_path = self.root_dir / file
            if file_path.exists():
                self.passed.append(f"Found: {file}")
                
                # Check for BOM
                with open(file_path, 'rb') as f:
                    if f.read(3) == b'\xef\xbb\xbf':
                        self.errors.append(f"BOM detected in {file} - must be removed")
                        
                # Validate YAML files
                if file.endswith('.yml') or file.endswith('.yaml'):
                    try:
                        with open(file_path, 'r') as f:
                            yaml.safe_load(f)
                        self.passed.append(f"Valid YAML: {file}")
                    except yaml.YAMLError as e:
                        self.errors.append(f"Invalid YAML in {file}: {e}")
            else:
                self.errors.append(f"Missing required file: {file}")
    
    def check_environment_variables(self) -> None:
        """Check environment variables."""
        print("🔍 Checking environment variables...")
        
        # Run the environment validation script
        env_script = self.root_dir / 'scripts' / 'validate_environment.py'
        if env_script.exists():
            code, stdout, stderr = self.run_command(
                [sys.executable, str(env_script), '--mode', 'production'],
                check=False
            )
            
            if code == 0:
                self.passed.append("Environment validation passed")
            else:
                # Parse output for specific issues
                if stdout:
                    for line in stdout.split('\n'):
                        if '❌' in line and 'Errors' not in line:
                            self.errors.append(f"Env: {line.strip()[2:]}")
                        elif '⚠️' in line and 'Warnings' not in line:
                            self.warnings.append(f"Env: {line.strip()[2:]}")
        else:
            self.warnings.append("Environment validation script not found")
        
        # Check for .env file
        env_file = self.root_dir / '.env'
        if not env_file.exists():
            self.warnings.append("No .env file found - ensure environment variables are set")
        else:
            with open(env_file, 'r') as f:
                content = f.read()
                if 'CHANGE_ME' in content or 'your-secret' in content:
                    self.errors.append(".env contains placeholder values - update before deployment")
    
    def check_ssl_certificates(self) -> None:
        """Check SSL certificate configuration."""
        print("🔍 Checking SSL certificates...")
        
        cert_dir = self.root_dir / 'certs'
        if not cert_dir.exists():
            self.warnings.append("No certs directory found - HTTPS will not work")
            return
        
        cert_file = cert_dir / 'server.crt'
        key_file = cert_dir / 'server.key'
        
        if cert_file.exists() and key_file.exists():
            self.passed.append("SSL certificate files found")
            
            # Check certificate validity
            code, stdout, stderr = self.run_command(
                ['openssl', 'x509', '-in', str(cert_file), '-noout', '-checkend', '0'],
                check=False
            )
            
            if code == 0:
                self.passed.append("SSL certificate is valid")
            else:
                self.warnings.append("SSL certificate appears to be expired or invalid")
                
            # Check key permissions
            key_mode = oct(key_file.stat().st_mode)[-3:]
            if key_mode == '600':
                self.passed.append("SSL private key has secure permissions")
            else:
                self.warnings.append(f"SSL private key has insecure permissions: {key_mode}")
        else:
            self.warnings.append("SSL certificate files not found - run manage_ssl_certificates.py")
    
    def check_database_configuration(self) -> None:
        """Check database configuration consistency."""
        print("🔍 Checking database configuration...")
        
        # Check for dean_prod vs dean_production issues
        issues = []
        
        # Check docker-compose files
        compose_files = list(self.root_dir.glob('docker-compose*.yml'))
        for file in compose_files:
            with open(file, 'r') as f:
                content = f.read()
                if 'POSTGRES_DB=dean_prod' in content:
                    issues.append(f"{file.name}: Contains POSTGRES_DB=dean_prod")
                elif 'POSTGRES_DB=${POSTGRES_DB}' in content:
                    self.passed.append(f"{file.name}: Uses environment variable for database")
        
        # Check SQL files
        sql_files = list((self.root_dir / 'postgres').glob('*.sql'))
        for file in sql_files:
            with open(file, 'r') as f:
                content = f.read()
                if 'dean_prod' in content and 'dean_production' not in content:
                    # Check if it's a username reference
                    if 'TO dean_prod' in content or 'USER dean_prod' in content:
                        self.passed.append(f"{file.name}: Correctly uses dean_prod as username")
                    else:
                        issues.append(f"{file.name}: May contain incorrect database reference")
        
        if issues:
            for issue in issues:
                self.errors.append(f"Database config: {issue}")
        else:
            self.passed.append("Database naming is consistent")
    
    def check_docker_configuration(self) -> None:
        """Check Docker configuration."""
        print("🔍 Checking Docker configuration...")
        
        # Validate docker-compose.prod.yml
        code, stdout, stderr = self.run_command(
            ['docker-compose', '-f', 'docker-compose.prod.yml', 'config'],
            check=False
        )
        
        if code == 0:
            self.passed.append("docker-compose.prod.yml is valid")
        else:
            self.errors.append(f"docker-compose.prod.yml validation failed: {stderr}")
        
        # Check for running containers that might conflict
        code, stdout, stderr = self.run_command(['docker', 'ps', '--format', 'table {{.Names}}'])
        if code == 0 and stdout:
            running = [line.strip() for line in stdout.split('\n')[1:] if 'dean-' in line]
            if running:
                self.warnings.append(f"DEAN containers already running: {', '.join(running)}")
    
    def check_ports(self) -> None:
        """Check if required ports are available."""
        print("🔍 Checking port availability...")
        
        required_ports = {
            80: "HTTP",
            443: "HTTPS", 
            8082: "Orchestrator API",
            5432: "PostgreSQL",
            6379: "Redis",
        }
        
        for port, service in required_ports.items():
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            
            if result == 0:
                self.warnings.append(f"Port {port} ({service}) is already in use")
            else:
                self.passed.append(f"Port {port} ({service}) is available")
    
    def check_file_permissions(self) -> None:
        """Check file permissions for security."""
        print("🔍 Checking file permissions...")
        
        # Check script permissions
        scripts = list((self.root_dir / 'scripts').glob('*.sh'))
        scripts.extend(list((self.root_dir / 'scripts').glob('*.py')))
        
        for script in scripts:
            if os.access(script, os.X_OK):
                self.passed.append(f"Executable: {script.name}")
            else:
                self.warnings.append(f"Not executable: {script.name}")
        
        # Check sensitive file permissions
        sensitive_files = [
            '.env',
            'certs/server.key',
        ]
        
        for file in sensitive_files:
            file_path = self.root_dir / file
            if file_path.exists():
                mode = oct(file_path.stat().st_mode)[-3:]
                if mode in ['600', '400']:
                    self.passed.append(f"Secure permissions on {file}")
                else:
                    self.warnings.append(f"Insecure permissions ({mode}) on {file}")
    
    def check_dependencies(self) -> None:
        """Check Python dependencies."""
        print("🔍 Checking dependencies...")
        
        req_files = [
            'requirements.txt',
            'requirements/base.txt',
            'src/orchestration/requirements.txt',
        ]
        
        for req_file in req_files:
            file_path = self.root_dir / req_file
            if file_path.exists():
                self.passed.append(f"Found requirements: {req_file}")
                
                # Check for security issues with safety
                code, stdout, stderr = self.run_command(
                    ['safety', 'check', '-r', str(file_path), '--json'],
                    check=False
                )
                
                if code == -1:
                    # Safety not installed
                    pass
                elif code == 0:
                    self.passed.append(f"No security vulnerabilities in {req_file}")
                else:
                    self.warnings.append(f"Security check failed for {req_file}")
    
    def generate_report(self) -> Tuple[bool, str]:
        """Generate pre-deployment report."""
        report = []
        report.append("=== DEAN Pre-Deployment Validation Report ===\n")
        report.append(f"Timestamp: {os.popen('date').read().strip()}")
        report.append(f"Directory: {self.root_dir}\n")
        
        # Summary counts
        report.append(f"✅ Passed: {len(self.passed)}")
        report.append(f"⚠️  Warnings: {len(self.warnings)}")
        report.append(f"❌ Errors: {len(self.errors)}\n")
        
        # Passed checks
        if self.passed:
            report.append("✅ Passed Checks:")
            for item in self.passed[:10]:  # Show first 10
                report.append(f"  - {item}")
            if len(self.passed) > 10:
                report.append(f"  ... and {len(self.passed) - 10} more")
            report.append("")
        
        # Warnings
        if self.warnings:
            report.append("⚠️  Warnings:")
            for warning in self.warnings:
                report.append(f"  - {warning}")
            report.append("")
        
        # Errors
        if self.errors:
            report.append("❌ Errors (must fix):")
            for error in self.errors:
                report.append(f"  - {error}")
            report.append("")
        
        # Deployment readiness
        if self.errors:
            report.append("❌ DEPLOYMENT BLOCKED - Fix errors before proceeding")
            ready = False
        elif len(self.warnings) > 5:
            report.append("⚠️  DEPLOYMENT NOT RECOMMENDED - Many warnings present")
            ready = True
        else:
            report.append("✅ READY FOR DEPLOYMENT")
            ready = True
        
        # Next steps
        report.append("\n=== Next Steps ===")
        if self.errors:
            report.append("1. Fix all errors listed above")
            report.append("2. Run this script again to verify")
        elif self.warnings:
            report.append("1. Review and address warnings if possible")
            report.append("2. Ensure you understand the impact of each warning")
            report.append("3. Proceed with deployment using deploy_windows.ps1 or deploy_production.sh")
        else:
            report.append("1. Run final deployment script")
            report.append("2. Monitor logs during deployment")
            report.append("3. Run post-deployment verification")
        
        return ready, '\n'.join(report)
    
    def run_all_checks(self) -> Tuple[bool, str]:
        """Run all pre-deployment checks."""
        checks = [
            self.check_system_requirements,
            self.check_configuration_files,
            self.check_environment_variables,
            self.check_ssl_certificates,
            self.check_database_configuration,
            self.check_docker_configuration,
            self.check_ports,
            self.check_file_permissions,
            self.check_dependencies,
        ]
        
        for check in checks:
            try:
                check()
            except Exception as e:
                self.errors.append(f"Check failed: {check.__name__} - {e}")
        
        return self.generate_report()


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Pre-deployment validation for DEAN system"
    )
    parser.add_argument(
        '--export',
        help='Export report to file'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output results as JSON'
    )
    
    args = parser.parse_args()
    
    print("🚀 DEAN Pre-Deployment Validation\n")
    
    # Run checks
    checker = PreDeploymentChecker()
    ready, report = checker.run_all_checks()
    
    # Output results
    if args.json:
        result = {
            'ready': ready,
            'passed': len(checker.passed),
            'warnings': len(checker.warnings),
            'errors': len(checker.errors),
            'details': {
                'passed': checker.passed,
                'warnings': checker.warnings,
                'errors': checker.errors,
            }
        }
        print(json.dumps(result, indent=2))
    else:
        print(report)
    
    # Export if requested
    if args.export:
        with open(args.export, 'w') as f:
            f.write(report)
        print(f"\nReport exported to: {args.export}")
    
    return 0 if ready else 1


if __name__ == "__main__":
    sys.exit(main())