#!/usr/bin/env python3
"""Configure all DEAN secrets in Infisical."""

import os
import sys
import json
import requests
import time
from typing import Dict, Any, Optional
from datetime import datetime

class InfisicalSecretsManager:
    """Manages secret configuration in Infisical."""
    
    def __init__(self, base_url: str, admin_email: str, admin_password: str):
        self.base_url = base_url.rstrip('/')
        self.admin_email = admin_email
        self.admin_password = admin_password
        self.access_token = None
        self.organization_id = None
        self.workspace_id = None
        
    def login(self) -> bool:
        """Login to Infisical and get access token."""
        print("🔐 Logging into Infisical...")
        
        response = requests.post(
            f"{self.base_url}/api/v1/auth/login",
            json={
                "email": self.admin_email,
                "password": self.admin_password
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            self.access_token = data.get("accessToken")
            print("✅ Login successful")
            return True
        else:
            print(f"❌ Login failed: {response.status_code} - {response.text}")
            return False
    
    def create_organization(self, org_name: str = "DEAN System") -> bool:
        """Create DEAN organization."""
        print(f"\n📁 Creating organization: {org_name}")
        
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        # Check if organization exists
        response = requests.get(
            f"{self.base_url}/api/v1/organizations",
            headers=headers
        )
        
        if response.status_code == 200:
            orgs = response.json().get("organizations", [])
            for org in orgs:
                if org["name"] == org_name:
                    self.organization_id = org["_id"]
                    print(f"✅ Organization already exists: {self.organization_id}")
                    return True
        
        # Create new organization
        response = requests.post(
            f"{self.base_url}/api/v1/organizations",
            headers=headers,
            json={"name": org_name}
        )
        
        if response.status_code in [200, 201]:
            data = response.json()
            self.organization_id = data.get("organization", {}).get("_id")
            print(f"✅ Organization created: {self.organization_id}")
            return True
        else:
            print(f"❌ Failed to create organization: {response.status_code}")
            return False
    
    def create_workspace(self, workspace_name: str = "DEAN Production") -> bool:
        """Create DEAN workspace/project."""
        print(f"\n📂 Creating workspace: {workspace_name}")
        
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        # Create workspace
        response = requests.post(
            f"{self.base_url}/api/v2/workspaces",
            headers=headers,
            json={
                "workspaceName": workspace_name,
                "organizationId": self.organization_id
            }
        )
        
        if response.status_code in [200, 201]:
            data = response.json()
            self.workspace_id = data.get("workspace", {}).get("_id")
            print(f"✅ Workspace created: {self.workspace_id}")
            return True
        else:
            print(f"❌ Failed to create workspace: {response.status_code}")
            return False
    
    def create_secret(self, path: str, key: str, value: str, environment: str = "production") -> bool:
        """Create a secret in Infisical."""
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        response = requests.post(
            f"{self.base_url}/api/v3/secrets",
            headers=headers,
            json={
                "workspaceId": self.workspace_id,
                "environment": environment,
                "secretPath": path,
                "secretKey": key,
                "secretValue": value,
                "secretComment": f"Created by setup script on {datetime.utcnow().isoformat()}"
            }
        )
        
        return response.status_code in [200, 201]
    
    def configure_all_secrets(self) -> None:
        """Configure all DEAN system secrets."""
        print("\n🔑 Configuring DEAN secrets...")
        
        # Read existing credentials from files
        with open("credentials.json", "r") as f:
            dean_creds = json.load(f)
        
        secrets_config = {
            # Common secrets for all services
            "/dean/common": {
                "DEAN_ENV": "production",
                "LOG_LEVEL": "info",
                "DEAN_ORGANIZATION": "DEAN System"
            },
            
            # Database configuration
            "/dean/database": {
                "POSTGRES_USER": dean_creds["database"]["postgres_user"],
                "POSTGRES_PASSWORD": dean_creds["database"]["postgres_password"],
                "POSTGRES_DB": dean_creds["database"]["database_name"],
                "DATABASE_URL": f"postgresql://{dean_creds['database']['postgres_user']}:{dean_creds['database']['postgres_password']}@postgres:5432/{dean_creds['database']['database_name']}"
            },
            
            # Redis configuration
            "/dean/redis": {
                "REDIS_PASSWORD": dean_creds["redis"]["password"],
                "REDIS_URL": f"redis://:{dean_creds['redis']['password']}@redis:6379/0"
            },
            
            # DEAN Orchestration service
            "/dean/orchestration": {
                "DEAN_SERVICE_API_KEY": dean_creds["dean"]["service_api_key"],
                "DEAN_JWT_SECRET_KEY": dean_creds["dean"]["jwt_secret_key"],
                "DEAN_ADMIN_PASSWORD": dean_creds["dean"]["admin_password"],
                "DEAN_SERVER_HOST": "0.0.0.0",
                "DEAN_SERVER_PORT": "8082",
                "DEAN_WEB_PORT": "8083"
            },
            
            # IndexAgent service
            "/dean/indexagent": {
                "INDEXAGENT_API_KEY": dean_creds["services"]["indexagent_api_key"],
                "INDEXAGENT_PORT": "8081",
                "CLAUDE_API_KEY": "PLACEHOLDER_CLAUDE_API_KEY",
                "INDEXAGENT_GPU_ENABLED": "true"
            },
            
            # Evolution API service
            "/dean/evolution": {
                "EVOLUTION_API_KEY": dean_creds["services"]["evolution_api_key"],
                "EVOLUTION_PORT": "8090",
                "EVOLUTION_MAX_GENERATIONS": "100",
                "EVOLUTION_TOKEN_BUDGET": "100000"
            },
            
            # Airflow configuration
            "/dean/airflow": {
                "AIRFLOW_ADMIN_PASSWORD": dean_creds["airflow"]["admin_password"],
                "AIRFLOW__CORE__FERNET_KEY": dean_creds["airflow"]["fernet_key"],
                "AIRFLOW__WEBSERVER__SECRET_KEY": dean_creds["airflow"]["secret_key"],
                "AIRFLOW__CORE__EXECUTOR": "LocalExecutor"
            },
            
            # Monitoring configuration
            "/dean/monitoring/prometheus": {
                "PROMETHEUS_RETENTION": "30d",
                "PROMETHEUS_SCRAPE_INTERVAL": "15s"
            },
            
            "/dean/monitoring/grafana": {
                "GF_SECURITY_ADMIN_USER": "admin",
                "GF_SECURITY_ADMIN_PASSWORD": dean_creds["dean"]["admin_password"],
                "GF_INSTALL_PLUGINS": "grafana-clock-panel,grafana-simple-json-datasource"
            },
            
            # External services (must be provided by user)
            "/dean/external": {
                "CLAUDE_API_KEY": "PLACEHOLDER_MUST_BE_PROVIDED",
                "GITHUB_TOKEN": "PLACEHOLDER_MUST_BE_PROVIDED"
            }
        }
        
        total_secrets = sum(len(secrets) for secrets in secrets_config.values())
        created_count = 0
        
        for path, secrets in secrets_config.items():
            print(f"\n📁 Creating secrets in {path}")
            for key, value in secrets.items():
                if self.create_secret(path, key, value):
                    created_count += 1
                    print(f"  ✅ {key}")
                else:
                    print(f"  ❌ {key}")
        
        print(f"\n✅ Created {created_count}/{total_secrets} secrets")
        
        # Create service tokens
        self.create_service_tokens()
    
    def create_service_tokens(self) -> None:
        """Create service authentication tokens."""
        print("\n🎫 Creating service tokens...")
        
        services = [
            "dean-orchestration",
            "indexagent",
            "evolution-api",
            "airflow",
            "prometheus",
            "grafana"
        ]
        
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        for service in services:
            response = requests.post(
                f"{self.base_url}/api/v2/service-tokens",
                headers=headers,
                json={
                    "name": f"{service}-token",
                    "workspaceId": self.workspace_id,
                    "scopes": ["read"],
                    "expiresIn": 365  # days
                }
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                token = data.get("serviceToken")
                print(f"  ✅ {service}: {token}")
                
                # Save token as secret
                self.create_secret(
                    f"/dean/service-tokens",
                    f"{service.upper().replace('-', '_')}_TOKEN",
                    token
                )
            else:
                print(f"  ❌ Failed to create token for {service}")

def main():
    """Main setup function."""
    print("🔐 DEAN Infisical Secret Configuration")
    print("=====================================")
    
    # Configuration
    infisical_url = "http://10.7.0.2:8090"
    admin_email = "admin@dean-system.local"
    admin_password = "YlncUtqCtu0LasRzwEG_VxNN"
    
    # Check if credentials file exists
    if not os.path.exists("credentials.json"):
        print("❌ credentials.json not found. Run generate_credentials.py first.")
        sys.exit(1)
    
    # Initialize manager
    manager = InfisicalSecretsManager(infisical_url, admin_email, admin_password)
    
    # Wait for Infisical to be ready
    print("⏳ Waiting for Infisical to be ready...")
    max_attempts = 30
    for i in range(max_attempts):
        try:
            response = requests.get(f"{infisical_url}/api/status", timeout=5)
            if response.status_code == 200:
                print("✅ Infisical is ready")
                break
        except:
            pass
        
        if i < max_attempts - 1:
            time.sleep(5)
            print(f"  Attempt {i+1}/{max_attempts}...")
    else:
        print("❌ Infisical is not responding")
        sys.exit(1)
    
    # Setup process
    if not manager.login():
        print("❌ Failed to login to Infisical")
        sys.exit(1)
    
    if not manager.create_organization():
        print("❌ Failed to create organization")
        sys.exit(1)
    
    if not manager.create_workspace():
        print("❌ Failed to create workspace")
        sys.exit(1)
    
    # Configure all secrets
    manager.configure_all_secrets()
    
    print("\n✅ Infisical configuration complete!")
    print("\n⚠️  IMPORTANT NEXT STEPS:")
    print("1. Login to Infisical UI at http://10.7.0.2:8090")
    print("2. Replace PLACEHOLDER_CLAUDE_API_KEY with actual Claude API key")
    print("3. Replace PLACEHOLDER_GITHUB_TOKEN with actual GitHub token")
    print("4. Configure PKI certificates for mTLS")
    print("\nWorkspace ID:", manager.workspace_id)

if __name__ == "__main__":
    main()