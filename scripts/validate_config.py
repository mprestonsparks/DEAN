#\!/usr/bin/env python3
"""Validate DEAN configuration before deployment."""

import os
import sys
from pathlib import Path

def validate_env_file():
    """Ensure all required environment variables are set."""
    env_path = Path(".env")
    if not env_path.exists():
        print("ERROR: .env file not found. Copy .env.production.template to .env")
        return False
    
    required_vars = [
        "POSTGRES_PASSWORD",
        "REDIS_PASSWORD",
        "JWT_SECRET_KEY",
        "DATABASE_URL"
    ]
    
    with open(env_path) as f:
        env_content = f.read()
    
    missing = []
    insecure = []
    
    for var in required_vars:
        if var not in env_content:
            missing.append(var)
        elif "CHANGE_ME" in env_content:
            insecure.append(var)
    
    if missing:
        print(f"ERROR: Missing required variables: {', '.join(missing)}")
        return False
    
    if insecure:
        print(f"ERROR: Default passwords found for: {', '.join(insecure)}")
        return False
    
    print("✓ Environment configuration valid")
    return True

def validate_docker_setup():
    """Check Docker is properly configured."""
    try:
        import subprocess
        result = subprocess.run(["docker", "version"], capture_output=True)
        if result.returncode \!= 0:
            print("ERROR: Docker not accessible")
            return False
        print("✓ Docker configuration valid")
        return True
    except Exception as e:
        print(f"ERROR: Docker check failed: {e}")
        return False

if __name__ == "__main__":
    valid = all([
        validate_env_file(),
        validate_docker_setup()
    ])
    sys.exit(0 if valid else 1)
EOF < /dev/null