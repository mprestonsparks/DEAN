#!/usr/bin/env python3
"""
Environment Variable Validation Script for DEAN
Validates that all required environment variables are set and correctly formatted.
"""

import os
import sys
import re
from typing import Dict, List, Tuple, Optional
from urllib.parse import urlparse
from pathlib import Path

class EnvironmentValidator:
    """Validates environment configuration for DEAN deployment."""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.info = []
        
        # Define required variables by deployment mode
        self.required_vars = {
            'core': [
                'JWT_SECRET_KEY',
                'DEAN_API_KEY',
            ],
            'database': [
                # Either DATABASE_URL or individual components
                ('DATABASE_URL', ['POSTGRES_HOST', 'POSTGRES_USER', 'POSTGRES_PASSWORD', 'POSTGRES_DB'])
            ],
            'redis': [
                # Either REDIS_URL or individual components
                ('REDIS_URL', ['REDIS_HOST'])
            ],
            'production': [
                'REDIS_PASSWORD',
                'SMTP_HOST',
                'SMTP_USERNAME',
                'SMTP_PASSWORD',
                'ALERT_EMAIL_FROM',
                'ALERT_EMAIL_TO',
            ]
        }
        
        # Define format validators
        self.format_validators = {
            'urls': ['DATABASE_URL', 'REDIS_URL', 'ORCHESTRATOR_URL', 
                    'INDEXAGENT_API_URL', 'AIRFLOW_API_URL', 'SENTRY_DSN'],
            'emails': ['ALERT_EMAIL_FROM', 'ALERT_EMAIL_TO', 'SMTP_USERNAME'],
            'ports': ['API_PORT', 'POSTGRES_PORT', 'REDIS_PORT', 'METRICS_PORT', 'SMTP_PORT'],
            'booleans': ['DEBUG', 'ENABLE_AUTH', 'SSL_VERIFY', 'ENABLE_METRICS',
                        'ENABLE_EVOLUTION', 'ENABLE_DISTRIBUTED', 'ENABLE_CACHING'],
            'integers': ['MAX_WORKERS', 'WORKER_TIMEOUT', 'MAX_MEMORY_MB', 
                        'TASK_TIMEOUT', 'MAX_CONCURRENT_TASKS', 'JWT_EXPIRATION_DELTA'],
            'database_names': ['POSTGRES_DB'],
        }
    
    def validate_url(self, name: str, value: str) -> bool:
        """Validate URL format."""
        try:
            result = urlparse(value)
            if not all([result.scheme, result.netloc]):
                self.errors.append(f"{name}: Invalid URL format: {value}")
                return False
            return True
        except Exception as e:
            self.errors.append(f"{name}: URL parsing error: {e}")
            return False
    
    def validate_email(self, name: str, value: str) -> bool:
        """Validate email format."""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        emails = value.split(',') if ',' in value else [value]
        
        for email in emails:
            email = email.strip()
            if not re.match(email_pattern, email):
                self.errors.append(f"{name}: Invalid email format: {email}")
                return False
        return True
    
    def validate_port(self, name: str, value: str) -> bool:
        """Validate port number."""
        try:
            port = int(value)
            if port < 1 or port > 65535:
                self.errors.append(f"{name}: Port must be between 1-65535: {value}")
                return False
            return True
        except ValueError:
            self.errors.append(f"{name}: Invalid port number: {value}")
            return False
    
    def validate_boolean(self, name: str, value: str) -> bool:
        """Validate boolean value."""
        valid_values = ['true', 'false', '1', '0', 'yes', 'no', 'on', 'off']
        if value.lower() not in valid_values:
            self.warnings.append(
                f"{name}: Unexpected boolean value '{value}'. "
                f"Expected one of: {', '.join(valid_values)}"
            )
        return True
    
    def validate_integer(self, name: str, value: str) -> bool:
        """Validate integer value."""
        try:
            int(value)
            return True
        except ValueError:
            self.errors.append(f"{name}: Invalid integer value: {value}")
            return False
    
    def validate_database_name(self, name: str, value: str) -> bool:
        """Validate database name."""
        if value == "dean_prod":
            self.errors.append(
                f"{name}: Database name 'dean_prod' is incorrect. "
                "Use 'dean_production' instead."
            )
            return False
        elif value != "dean_production" and os.getenv('ENV') == 'production':
            self.warnings.append(
                f"{name}: Expected 'dean_production' for production, got '{value}'"
            )
        return True
    
    def check_required_variables(self, mode: str = 'production') -> None:
        """Check that required variables are set."""
        # Always check core variables
        for var in self.required_vars['core']:
            if not os.getenv(var):
                self.errors.append(f"Missing required variable: {var}")
        
        # Check database variables (either DATABASE_URL or components)
        for var_group in self.required_vars['database']:
            if isinstance(var_group, tuple):
                primary, alternates = var_group
                if not os.getenv(primary):
                    # Check if all alternates are provided
                    missing_alts = [v for v in alternates if not os.getenv(v)]
                    if missing_alts:
                        self.errors.append(
                            f"Missing {primary} and required components: "
                            f"{', '.join(missing_alts)}"
                        )
        
        # Check Redis variables
        for var_group in self.required_vars['redis']:
            if isinstance(var_group, tuple):
                primary, alternates = var_group
                if not os.getenv(primary):
                    missing_alts = [v for v in alternates if not os.getenv(v)]
                    if missing_alts:
                        self.warnings.append(
                            f"Missing {primary} and components: "
                            f"{', '.join(missing_alts)}"
                        )
        
        # Check production-specific variables
        if mode == 'production' and os.getenv('ENV') == 'production':
            for var in self.required_vars['production']:
                if not os.getenv(var):
                    # Email variables are warnings if email alerts are disabled
                    if var.startswith('SMTP_') or var.startswith('ALERT_'):
                        if os.getenv('ENABLE_EMAIL_ALERTS', 'false').lower() == 'true':
                            self.errors.append(
                                f"Missing required variable for email alerts: {var}"
                            )
                    else:
                        self.warnings.append(
                            f"Missing recommended production variable: {var}"
                        )
    
    def validate_formats(self) -> None:
        """Validate format of environment variables."""
        for var_type, var_names in self.format_validators.items():
            for var_name in var_names:
                value = os.getenv(var_name)
                if value:
                    if var_type == 'urls':
                        self.validate_url(var_name, value)
                    elif var_type == 'emails':
                        self.validate_email(var_name, value)
                    elif var_type == 'ports':
                        self.validate_port(var_name, value)
                    elif var_type == 'booleans':
                        self.validate_boolean(var_name, value)
                    elif var_type == 'integers':
                        self.validate_integer(var_name, value)
                    elif var_type == 'database_names':
                        self.validate_database_name(var_name, value)
    
    def check_database_configuration(self) -> None:
        """Validate database configuration."""
        db_url = os.getenv('DATABASE_URL')
        
        if db_url:
            # Parse DATABASE_URL
            try:
                parsed = urlparse(db_url)
                db_name = parsed.path.lstrip('/')
                
                if db_name == 'dean_prod':
                    self.errors.append(
                        "DATABASE_URL contains incorrect database name 'dean_prod'. "
                        "Use 'dean_production' instead."
                    )
                elif db_name != 'dean_production' and os.getenv('ENV') == 'production':
                    self.warnings.append(
                        f"DATABASE_URL database name '{db_name}' != 'dean_production'"
                    )
                
                self.info.append(f"Database URL parsed: {parsed.hostname}:{parsed.port}/{db_name}")
                
            except Exception as e:
                self.errors.append(f"Failed to parse DATABASE_URL: {e}")
        else:
            # Check individual components
            host = os.getenv('POSTGRES_HOST', 'dean-postgres')
            port = os.getenv('POSTGRES_PORT', '5432')
            user = os.getenv('POSTGRES_USER', 'dean_prod')
            db = os.getenv('POSTGRES_DB', 'dean_production')
            
            self.info.append(f"Database config: {user}@{host}:{port}/{db}")
    
    def check_redis_configuration(self) -> None:
        """Validate Redis configuration."""
        redis_url = os.getenv('REDIS_URL')
        
        if redis_url:
            try:
                parsed = urlparse(redis_url)
                self.info.append(f"Redis URL parsed: {parsed.hostname}:{parsed.port}")
            except Exception as e:
                self.errors.append(f"Failed to parse REDIS_URL: {e}")
        else:
            host = os.getenv('REDIS_HOST', 'dean-redis')
            port = os.getenv('REDIS_PORT', '6379')
            self.info.append(f"Redis config: {host}:{port}")
            
            if os.getenv('ENV') == 'production' and not os.getenv('REDIS_PASSWORD'):
                self.warnings.append("REDIS_PASSWORD not set for production")
    
    def check_service_endpoints(self) -> None:
        """Check service endpoint configuration."""
        services = {
            'ORCHESTRATOR_URL': 'http://dean-orchestrator:8082',
            'INDEXAGENT_API_URL': 'http://indexagent:8080',
            'AIRFLOW_API_URL': 'http://airflow-webserver:8080',
        }
        
        for var, default in services.items():
            value = os.getenv(var, default)
            if 'localhost' in value and os.getenv('ENV') == 'production':
                self.warnings.append(
                    f"{var} contains 'localhost' which may not work in production"
                )
    
    def check_security_configuration(self) -> None:
        """Check security-related configuration."""
        # JWT Secret
        jwt_secret = os.getenv('JWT_SECRET_KEY')
        if jwt_secret:
            if len(jwt_secret) < 32:
                self.warnings.append(
                    "JWT_SECRET_KEY should be at least 32 characters for security"
                )
            if jwt_secret == 'your-secret-key' or 'change' in jwt_secret.lower():
                self.errors.append(
                    "JWT_SECRET_KEY appears to be a placeholder. "
                    "Use a strong, unique secret."
                )
        
        # API Key
        api_key = os.getenv('DEAN_API_KEY')
        if api_key:
            if len(api_key) < 32:
                self.warnings.append(
                    "DEAN_API_KEY should be at least 32 characters for security"
                )
        
        # SSL Verification
        if os.getenv('SSL_VERIFY', 'true').lower() == 'false':
            self.warnings.append(
                "SSL_VERIFY is disabled. This is insecure for production."
            )
        
        # Debug mode
        if os.getenv('DEBUG', 'false').lower() == 'true' and os.getenv('ENV') == 'production':
            self.warnings.append(
                "DEBUG mode is enabled in production. This is a security risk."
            )
    
    def check_env_file(self) -> None:
        """Check for .env file and its contents."""
        env_file = Path('.env')
        if env_file.exists():
            self.info.append(f"Found .env file: {env_file.absolute()}")
            
            # Check if it contains placeholder values
            with open(env_file, 'r') as f:
                content = f.read()
                if 'CHANGE_ME' in content or 'your-' in content:
                    self.warnings.append(
                        ".env file contains placeholder values. "
                        "Update with actual values."
                    )
        else:
            self.info.append("No .env file found (using system environment)")
    
    def generate_report(self) -> Tuple[bool, str]:
        """Generate validation report."""
        report = []
        report.append("=== DEAN Environment Validation Report ===\n")
        
        # Environment info
        env_mode = os.getenv('ENV', 'development')
        report.append(f"Environment Mode: {env_mode}")
        report.append(f"Python Path: {sys.executable}")
        report.append(f"Working Directory: {os.getcwd()}\n")
        
        # Info messages
        if self.info:
            report.append("ℹ️  Information:")
            for msg in self.info:
                report.append(f"  - {msg}")
            report.append("")
        
        # Errors
        if self.errors:
            report.append("❌ Errors (must fix):")
            for error in self.errors:
                report.append(f"  - {error}")
            report.append("")
        
        # Warnings
        if self.warnings:
            report.append("⚠️  Warnings (should fix):")
            for warning in self.warnings:
                report.append(f"  - {warning}")
            report.append("")
        
        # Summary
        if not self.errors and not self.warnings:
            report.append("✅ All environment variables validated successfully!")
            success = True
        elif not self.errors:
            report.append("✅ No critical errors found, but warnings exist.")
            success = True
        else:
            report.append("❌ Validation failed with errors.")
            success = False
        
        return success, '\n'.join(report)
    
    def validate(self) -> Tuple[bool, str]:
        """Run all validation checks."""
        # Check .env file
        self.check_env_file()
        
        # Run validations
        self.check_required_variables()
        self.validate_formats()
        self.check_database_configuration()
        self.check_redis_configuration()
        self.check_service_endpoints()
        self.check_security_configuration()
        
        # Generate report
        return self.generate_report()


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Validate DEAN environment configuration"
    )
    parser.add_argument(
        '--mode', 
        choices=['development', 'production'],
        default='production',
        help='Validation mode (default: production)'
    )
    parser.add_argument(
        '--fix',
        action='store_true',
        help='Suggest fixes for common issues'
    )
    parser.add_argument(
        '--export',
        help='Export validation report to file'
    )
    
    args = parser.parse_args()
    
    # Set mode if not already set
    if not os.getenv('ENV'):
        os.environ['ENV'] = args.mode
    
    # Run validation
    validator = EnvironmentValidator()
    success, report = validator.validate()
    
    # Print report
    print(report)
    
    # Export if requested
    if args.export:
        with open(args.export, 'w') as f:
            f.write(report)
        print(f"\nReport exported to: {args.export}")
    
    # Suggest fixes if requested
    if args.fix and not success:
        print("\n=== Suggested Fixes ===\n")
        
        if any('dean_prod' in e for e in validator.errors):
            print("1. Fix database name:")
            print("   export POSTGRES_DB=dean_production")
            print("   # Update DATABASE_URL to use /dean_production")
            print()
        
        if any('Missing required' in e for e in validator.errors):
            print("2. Set required variables:")
            print("   export JWT_SECRET_KEY=$(openssl rand -hex 32)")
            print("   export DEAN_API_KEY=$(openssl rand -hex 32)")
            print()
        
        if any('placeholder' in w for w in validator.warnings):
            print("3. Replace placeholder values in .env")
            print("   Use strong, unique values for production")
            print()
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())