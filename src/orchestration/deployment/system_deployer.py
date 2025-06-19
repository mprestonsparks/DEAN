"""System deployment orchestration for DEAN.

Adapted from dean-agent-workspace/deploy_dean_system.py
Provides deployment orchestration without direct repository dependencies.
"""

import os
import sys
import json
import time
import subprocess
import logging
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

import structlog
from pydantic import BaseModel, Field

from ...integration import ServicePool

# Configure structured logging
logger = structlog.get_logger(__name__)


class DeploymentConfig(BaseModel):
    """Configuration for DEAN system deployment."""
    
    skip_build: bool = Field(False, description="Skip Docker image builds")
    init_repos: bool = Field(False, description="Initialize test repositories")
    check_only: bool = Field(False, description="Only check prerequisites")
    docker_compose_path: Path = Field(
        Path("../infra/docker-compose.yml"),
        description="Path to docker-compose file in infra repository"
    )
    env_template_path: Path = Field(
        Path("../infra/.env.example"),
        description="Path to environment template in infra repository"
    )
    env_file_path: Path = Field(
        Path("../infra/.env"),
        description="Path to environment file in infra repository"
    )
    service_timeout: int = Field(300, description="Service startup timeout in seconds")
    
    # Service endpoints
    service_endpoints: Dict[str, str] = Field(
        default_factory=lambda: {
            'airflow': 'http://localhost:8080',
            'indexagent': 'http://localhost:8081',
            'evolution': 'http://localhost:8090',
        }
    )


class DeploymentStatus(BaseModel):
    """Tracks deployment status."""
    
    environment: bool = False
    docker: bool = False
    services: bool = False
    claude_cli: bool = False
    test_repos: bool = False
    training_data: bool = False
    ready: bool = False
    start_time: datetime = Field(default_factory=datetime.utcnow)
    errors: List[str] = Field(default_factory=list)


class SystemDeployer:
    """Orchestrates DEAN system deployment.
    
    Handles:
    - Environment validation
    - Docker infrastructure deployment
    - Service health verification
    - Test repository initialization
    """
    
    REQUIRED_ENV_VARS = ['ANTHROPIC_API_KEY']
    OPTIONAL_ENV_VARS = ['OPENAI_API_KEY', 'GITHUB_TOKEN']
    
    def __init__(self, config: Optional[DeploymentConfig] = None):
        """Initialize system deployer.
        
        Args:
            config: Deployment configuration
        """
        self.config = config or DeploymentConfig()
        self.status = DeploymentStatus()
        self.logger = logger.bind(component="system_deployer")
    
    async def deploy(self) -> DeploymentStatus:
        """Execute full system deployment.
        
        Returns:
            Deployment status with results
        """
        self.logger.info("Starting DEAN system deployment")
        
        try:
            # Check environment
            env_ok, missing = self._check_environment()
            if not env_ok:
                self.status.errors.extend(missing)
                if self.config.check_only:
                    return self.status
                raise RuntimeError(f"Missing prerequisites: {missing}")
            
            self.status.environment = True
            
            if self.config.check_only:
                self.logger.info("Check-only mode - skipping deployment")
                return self.status
            
            # Create environment file
            if not self._create_env_file():
                raise RuntimeError("Failed to create environment file")
            
            # Deploy Docker infrastructure
            if not self._deploy_docker_infrastructure():
                raise RuntimeError("Failed to deploy Docker infrastructure")
            
            self.status.docker = True
            
            # Wait for services
            if not await self._wait_for_services():
                raise RuntimeError("Services failed to become healthy")
            
            self.status.services = True
            
            # Setup Claude CLI
            if not self._setup_claude_cli():
                self.logger.warning("Claude CLI setup failed - continuing")
            else:
                self.status.claude_cli = True
            
            # Initialize test repositories
            if self.config.init_repos:
                if not self._initialize_test_repos():
                    self.logger.warning("Test repo initialization failed")
                else:
                    self.status.test_repos = True
            
            self.status.ready = True
            self.logger.info(
                "DEAN system deployment completed successfully",
                duration=(datetime.utcnow() - self.status.start_time).total_seconds()
            )
            
        except Exception as e:
            self.logger.error("Deployment failed", error=str(e))
            self.status.errors.append(str(e))
        
        return self.status
    
    def _check_environment(self) -> Tuple[bool, List[str]]:
        """Check environment variables and prerequisites.
        
        Returns:
            Tuple of (success, missing_items)
        """
        self.logger.info("Checking environment prerequisites")
        missing = []
        
        # Check required environment variables
        for var in self.REQUIRED_ENV_VARS:
            if not os.getenv(var):
                missing.append(f"Environment variable: {var}")
        
        # Check optional environment variables
        for var in self.OPTIONAL_ENV_VARS:
            if not os.getenv(var):
                self.logger.warning(
                    "Optional environment variable not set",
                    variable=var
                )
        
        # Check Docker
        try:
            subprocess.run(
                ['docker', '--version'],
                check=True,
                capture_output=True
            )
            self.logger.info("Docker is installed")
        except (subprocess.CalledProcessError, FileNotFoundError):
            missing.append("Docker installation")
        
        # Check Docker Compose
        try:
            subprocess.run(
                ['docker-compose', '--version'],
                check=True,
                capture_output=True
            )
            self.logger.info("Docker Compose is installed")
        except (subprocess.CalledProcessError, FileNotFoundError):
            try:
                subprocess.run(
                    ['docker', 'compose', 'version'],
                    check=True,
                    capture_output=True
                )
                self.logger.info("Docker Compose (plugin) is installed")
            except:
                missing.append("Docker Compose installation")
        
        return len(missing) == 0, missing
    
    def _create_env_file(self) -> bool:
        """Create .env file from template.
        
        Returns:
            Success status
        """
        self.logger.info("Creating environment configuration")
        
        try:
            if not self.config.env_template_path.exists():
                self.logger.error(
                    "Environment template not found",
                    path=str(self.config.env_template_path)
                )
                return False
            
            # Read template
            template_content = self.config.env_template_path.read_text()
            
            # Apply replacements
            replacements = {
                'ANTHROPIC_API_KEY=': f'ANTHROPIC_API_KEY={os.getenv("ANTHROPIC_API_KEY", "")}',
                'OPENAI_API_KEY=': f'OPENAI_API_KEY={os.getenv("OPENAI_API_KEY", "")}',
                'GITHUB_TOKEN=': f'GITHUB_TOKEN={os.getenv("GITHUB_TOKEN", "")}',
            }
            
            env_content = template_content
            for old, new in replacements.items():
                env_content = env_content.replace(old, new)
            
            # Write environment file
            self.config.env_file_path.write_text(env_content)
            
            self.logger.info(
                "Created environment file",
                path=str(self.config.env_file_path)
            )
            return True
            
        except Exception as e:
            self.logger.error("Failed to create environment file", error=str(e))
            return False
    
    def _deploy_docker_infrastructure(self) -> bool:
        """Deploy Docker infrastructure.
        
        Returns:
            Success status
        """
        self.logger.info("Deploying Docker infrastructure")
        
        try:
            # Get compose directory
            compose_dir = self.config.docker_compose_path.parent
            
            # Stop existing containers
            self.logger.info("Stopping existing containers")
            subprocess.run(
                ['docker-compose', 'down', '-v'],
                cwd=compose_dir,
                capture_output=True
            )
            
            # Build if not skipping
            if not self.config.skip_build:
                self.logger.info("Building Docker images")
                result = subprocess.run(
                    ['docker-compose', 'build', '--no-cache'],
                    cwd=compose_dir,
                    capture_output=True,
                    text=True
                )
                if result.returncode != 0:
                    self.logger.error(
                        "Docker build failed",
                        stderr=result.stderr
                    )
                    return False
            
            # Start containers
            self.logger.info("Starting Docker containers")
            result = subprocess.run(
                ['docker-compose', 'up', '-d'],
                cwd=compose_dir,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                self.logger.error(
                    "Docker deployment failed",
                    stderr=result.stderr
                )
                return False
            
            self.logger.info("Docker infrastructure deployed successfully")
            return True
            
        except Exception as e:
            self.logger.error("Failed to deploy Docker", error=str(e))
            return False
    
    async def _wait_for_services(self) -> bool:
        """Wait for all services to be healthy.
        
        Returns:
            Success status
        """
        self.logger.info("Waiting for services to be healthy")
        
        try:
            # Use service pool for health checks
            async with ServicePool(**self.config.service_endpoints) as pool:
                start_time = time.time()
                
                while time.time() - start_time < self.config.service_timeout:
                    health_status = await pool.health.check_all_services()
                    
                    if health_status['status'] == 'healthy':
                        self.logger.info("All services are healthy")
                        return True
                    
                    # Log unhealthy services
                    for service, status in health_status['services'].items():
                        if status.get('status') != 'healthy':
                            self.logger.debug(
                                "Service not ready",
                                service=service,
                                status=status
                            )
                    
                    await asyncio.sleep(5)
                
                # Timeout reached
                self.logger.error(
                    "Service health check timeout",
                    timeout=self.config.service_timeout
                )
                return False
                
        except Exception as e:
            self.logger.error("Health check failed", error=str(e))
            return False
    
    def _setup_claude_cli(self) -> bool:
        """Setup Claude Code CLI integration.
        
        Returns:
            Success status
        """
        self.logger.info("Setting up Claude Code CLI")
        
        try:
            # Check if Claude CLI container exists
            result = subprocess.run(
                ['docker', 'ps', '-a', '--format', '{{.Names}}'],
                capture_output=True,
                text=True
            )
            
            if 'claude-cli' not in result.stdout:
                self.logger.warning("Claude CLI container not found")
                return False
            
            # Ensure Claude CLI is running
            subprocess.run(
                ['docker', 'start', 'claude-cli'],
                capture_output=True
            )
            
            self.logger.info("Claude CLI setup completed")
            return True
            
        except Exception as e:
            self.logger.error("Claude CLI setup failed", error=str(e))
            return False
    
    def _initialize_test_repos(self) -> bool:
        """Initialize test repositories for evolution trials.
        
        Returns:
            Success status
        """
        self.logger.info("Initializing test repositories")
        
        try:
            # Use asyncio to run async repository initialization
            import asyncio
            from ..repository_manager import RepositoryManager
            
            async def init_repos():
                # Create repository manager
                repo_manager = RepositoryManager(
                    base_path=self.config.get("repository_base_path", "/repos"),
                    db_pool=None,  # Would be passed from main app context
                    redis_client=None  # Would be passed from main app context
                )
                
                # Define test repositories to create
                test_repos = [
                    {
                        "name": "test-python-package",
                        "template": "python_package",
                        "language": "python"
                    },
                    {
                        "name": "test-web-app",
                        "template": "web_app",
                        "language": "javascript"
                    },
                    {
                        "name": "test-simple-project",
                        "template": "default",
                        "language": "python"
                    }
                ]
                
                # Initialize each test repository
                created_repos = []
                for repo_config in test_repos:
                    try:
                        repo_info = await repo_manager.initialize_test_repository(
                            name=repo_config["name"],
                            template=repo_config["template"],
                            language=repo_config["language"]
                        )
                        created_repos.append(repo_info)
                        self.logger.info(f"Created test repository: {repo_info['name']} at {repo_info['path']}")
                    except Exception as e:
                        self.logger.error(f"Failed to create test repository {repo_config['name']}: {e}")
                
                return created_repos
            
            # Run async initialization
            created_repos = asyncio.run(init_repos())
            
            if created_repos:
                self.logger.info(f"Successfully initialized {len(created_repos)} test repositories")
                return True
            else:
                self.logger.error("Failed to initialize any test repositories")
                return False
                
        except Exception as e:
            self.logger.error(f"Test repository initialization failed: {e}")
            return False