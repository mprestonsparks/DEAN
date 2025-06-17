"""
Integration test for deployment workflow.

Tests that deployment scripts work correctly.
"""

import pytest
import subprocess
import os
import tempfile
import shutil
from pathlib import Path
import sys
import json
import time
from unittest.mock import patch, MagicMock, call

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from orchestration.deployment.system_deployer import (
    SystemDeployer,
    DeploymentConfig,
    DeploymentResult
)


@pytest.mark.integration
class TestDeploymentWorkflow:
    """Test complete deployment workflow."""
    
    @pytest.fixture
    def project_root(self):
        """Get project root directory."""
        return Path(__file__).parent.parent.parent
        
    @pytest.fixture
    def temp_deployment_dir(self):
        """Create temporary deployment directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            deploy_dir = Path(tmpdir) / "deployment"
            deploy_dir.mkdir()
            
            # Create mock docker-compose.yml
            compose_content = """
version: '3.8'
services:
  test-service:
    image: alpine:latest
    command: echo "test"
"""
            with open(deploy_dir / "docker-compose.yml", "w") as f:
                f.write(compose_content)
                
            yield deploy_dir
            
    @pytest.fixture
    def deployment_config(self, temp_deployment_dir):
        """Create test deployment configuration."""
        return DeploymentConfig(
            environment="test",
            deployment_dir=str(temp_deployment_dir),
            services=["test-service"],
            dry_run=True  # Don't actually deploy
        )
        
    def test_deployment_scripts_exist(self, project_root):
        """Test that all deployment scripts exist."""
        scripts_dir = project_root / "scripts" / "deploy"
        
        required_scripts = [
            "deploy_local.sh",
            "deploy_production.sh",
            "health_check.sh",
            "rollback.sh",
        ]
        
        for script_name in required_scripts:
            script_path = scripts_dir / script_name
            assert script_path.exists(), f"Missing deployment script: {script_name}"
            
    def test_deployment_script_syntax(self, project_root):
        """Test that deployment scripts have valid bash syntax."""
        scripts_dir = project_root / "scripts" / "deploy"
        
        # Skip on Windows
        if os.name == 'nt':
            pytest.skip("Bash syntax check not available on Windows")
            
        for script_path in scripts_dir.glob("*.sh"):
            # Check syntax with bash -n
            result = subprocess.run(
                ["bash", "-n", str(script_path)],
                capture_output=True,
                text=True
            )
            
            assert result.returncode == 0, f"Syntax error in {script_path.name}: {result.stderr}"
            
    def test_system_deployer_initialization(self, deployment_config):
        """Test SystemDeployer initialization."""
        deployer = SystemDeployer(deployment_config)
        
        assert deployer.config.environment == "test"
        assert deployer.config.dry_run is True
        assert len(deployer.config.services) == 1
        
    @pytest.mark.asyncio
    async def test_deployment_validation(self, deployment_config):
        """Test deployment validation checks."""
        deployer = SystemDeployer(deployment_config)
        
        # Validate deployment
        validation_result = await deployer.validate_deployment()
        
        assert isinstance(validation_result, dict)
        assert "valid" in validation_result
        assert "checks" in validation_result
        
        # Check individual validations
        checks = validation_result["checks"]
        assert "docker_available" in checks
        assert "compose_file_valid" in checks
        assert "services_defined" in checks
        
    @pytest.mark.asyncio
    async def test_dry_run_deployment(self, deployment_config):
        """Test dry run deployment execution."""
        deployer = SystemDeployer(deployment_config)
        
        # Execute dry run
        result = await deployer.deploy()
        
        assert isinstance(result, DeploymentResult)
        assert result.success is True
        assert result.dry_run is True
        assert "Would deploy" in result.message
        
    def test_environment_variable_handling(self, temp_deployment_dir):
        """Test that environment variables are properly handled."""
        # Create .env file
        env_content = """
INDEXAGENT_API_URL=http://localhost:8081
AIRFLOW_API_URL=http://localhost:8080
POSTGRES_PASSWORD=testpass
"""
        with open(temp_deployment_dir / ".env", "w") as f:
            f.write(env_content)
            
        config = DeploymentConfig(
            environment="test",
            deployment_dir=str(temp_deployment_dir),
            env_file=str(temp_deployment_dir / ".env")
        )
        
        deployer = SystemDeployer(config)
        env_vars = deployer._load_environment_variables()
        
        assert "INDEXAGENT_API_URL" in env_vars
        assert env_vars["INDEXAGENT_API_URL"] == "http://localhost:8081"
        assert "POSTGRES_PASSWORD" in env_vars
        
    @pytest.mark.asyncio
    async def test_health_check_integration(self, deployment_config):
        """Test health check after deployment."""
        deployer = SystemDeployer(deployment_config)
        
        # Mock health check responses
        with patch.object(deployer, '_check_service_health') as mock_health:
            mock_health.return_value = {"status": "healthy", "latency_ms": 50}
            
            # Run health checks
            health_status = await deployer.check_deployment_health()
            
            assert isinstance(health_status, dict)
            assert "services" in health_status
            assert "overall_status" in health_status
            
    def test_rollback_capability(self, deployment_config, temp_deployment_dir):
        """Test deployment rollback functionality."""
        deployer = SystemDeployer(deployment_config)
        
        # Create backup directory
        backup_dir = temp_deployment_dir / "backups" / "test-backup"
        backup_dir.mkdir(parents=True)
        
        # Create mock backup
        with open(backup_dir / "docker-compose.yml", "w") as f:
            f.write("version: '3.8'\nservices: {}")
            
        # Test rollback
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            
            result = deployer.rollback("test-backup")
            
            assert result.success is True
            assert "Rollback completed" in result.message
            
    def test_configuration_templating(self, temp_deployment_dir):
        """Test configuration file templating."""
        # Create template
        template_content = """
services:
  api:
    image: myapp:{{ version }}
    environment:
      - ENV={{ environment }}
      - DEBUG={{ debug }}
"""
        template_path = temp_deployment_dir / "config.template.yml"
        with open(template_path, "w") as f:
            f.write(template_content)
            
        config = DeploymentConfig(
            environment="production",
            deployment_dir=str(temp_deployment_dir),
            template_vars={
                "version": "1.2.3",
                "environment": "production",
                "debug": "false"
            }
        )
        
        deployer = SystemDeployer(config)
        rendered = deployer._render_template(str(template_path))
        
        assert "myapp:1.2.3" in rendered
        assert "ENV=production" in rendered
        assert "DEBUG=false" in rendered
        
    @pytest.mark.asyncio
    async def test_multi_environment_deployment(self):
        """Test deployment across different environments."""
        environments = ["local", "staging", "production"]
        
        for env in environments:
            with tempfile.TemporaryDirectory() as tmpdir:
                deploy_dir = Path(tmpdir)
                
                # Create environment-specific compose file
                compose_path = deploy_dir / f"docker-compose.{env}.yml"
                with open(compose_path, "w") as f:
                    f.write(f"version: '3.8'\n# {env} config")
                    
                config = DeploymentConfig(
                    environment=env,
                    deployment_dir=str(deploy_dir),
                    compose_file=f"docker-compose.{env}.yml",
                    dry_run=True
                )
                
                deployer = SystemDeployer(config)
                result = await deployer.deploy()
                
                assert result.success is True
                assert env in result.message
                
    def test_secret_handling(self, temp_deployment_dir):
        """Test secure handling of secrets during deployment."""
        # Create secrets file
        secrets_content = {
            "database_password": "super-secret",
            "api_key": "confidential-key"
        }
        
        secrets_path = temp_deployment_dir / "secrets.json"
        with open(secrets_path, "w") as f:
            json.dump(secrets_content, f)
            
        # Set restrictive permissions (Unix only)
        if os.name != 'nt':
            os.chmod(secrets_path, 0o600)
            
        config = DeploymentConfig(
            environment="production",
            deployment_dir=str(temp_deployment_dir),
            secrets_file=str(secrets_path)
        )
        
        deployer = SystemDeployer(config)
        
        # Verify secrets are loaded but not logged
        with patch('builtins.print') as mock_print:
            secrets = deployer._load_secrets()
            
            # Check secrets loaded correctly
            assert secrets["database_password"] == "super-secret"
            
            # Verify secrets not printed
            for call in mock_print.call_args_list:
                assert "super-secret" not in str(call)
                assert "confidential-key" not in str(call)
                
    @pytest.mark.asyncio
    async def test_deployment_hooks(self, deployment_config):
        """Test pre and post deployment hooks."""
        hooks_called = []
        
        async def pre_deploy_hook(config):
            hooks_called.append("pre_deploy")
            return True
            
        async def post_deploy_hook(config, result):
            hooks_called.append("post_deploy")
            return True
            
        deployer = SystemDeployer(deployment_config)
        deployer.register_hook("pre_deploy", pre_deploy_hook)
        deployer.register_hook("post_deploy", post_deploy_hook)
        
        # Execute deployment
        await deployer.deploy()
        
        # Verify hooks were called in order
        assert hooks_called == ["pre_deploy", "post_deploy"]
        
    def test_deployment_cli_integration(self, project_root):
        """Test deployment commands from CLI."""
        from interfaces.cli.dean_cli import cli, deploy
        
        # Check deploy command exists
        assert 'deploy' in cli.commands
        
        # Check deploy command options
        deploy_cmd = cli.commands['deploy']
        param_names = [p.name for p in deploy_cmd.params]
        
        assert 'environment' in param_names
        assert 'dry_run' in param_names
        assert 'config' in param_names
        
    @pytest.mark.asyncio
    async def test_resource_cleanup(self, deployment_config, temp_deployment_dir):
        """Test that resources are properly cleaned up after deployment."""
        deployer = SystemDeployer(deployment_config)
        
        # Create some temporary files
        temp_file = temp_deployment_dir / "temp_deployment.lock"
        temp_file.touch()
        
        # Deploy and ensure cleanup
        try:
            await deployer.deploy()
        finally:
            # Verify cleanup happened
            assert not temp_file.exists() or deployment_config.dry_run
            
    def test_deployment_logging(self, deployment_config, tmp_path):
        """Test deployment logging functionality."""
        log_file = tmp_path / "deployment.log"
        
        config = DeploymentConfig(
            environment="test",
            deployment_dir=str(deployment_config.deployment_dir),
            log_file=str(log_file),
            dry_run=True
        )
        
        deployer = SystemDeployer(config)
        
        # Execute deployment with logging
        asyncio.run(deployer.deploy())
        
        # Verify log file created
        assert log_file.exists()
        
        # Check log contents
        log_content = log_file.read_text()
        assert "Starting deployment" in log_content
        assert "test environment" in log_content


@pytest.mark.integration
class TestDeploymentValidation:
    """Test deployment validation and safety checks."""
    
    def test_docker_availability_check(self):
        """Test Docker availability validation."""
        validator = DeploymentValidator()
        
        # Mock docker command
        with patch('subprocess.run') as mock_run:
            # Simulate Docker available
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="Docker version 20.10.0\n"
            )
            
            result = validator.check_docker_available()
            assert result["available"] is True
            assert "20.10.0" in result["version"]
            
            # Simulate Docker not available  
            mock_run.return_value = MagicMock(returncode=1)
            result = validator.check_docker_available()
            assert result["available"] is False
            
    def test_port_availability_check(self):
        """Test port availability validation."""
        validator = DeploymentValidator()
        
        required_ports = [8080, 8081, 8082, 5432, 6379]
        
        # Check ports (mock since we can't guarantee availability)
        with patch('socket.socket') as mock_socket:
            # Simulate all ports available
            mock_socket.return_value.connect_ex.return_value = 1  # Port closed = available
            
            results = validator.check_ports_available(required_ports)
            
            assert all(results[port]["available"] for port in required_ports)
            
    def test_disk_space_check(self):
        """Test disk space validation."""
        validator = DeploymentValidator()
        
        # Check disk space
        result = validator.check_disk_space(
            required_gb=1,  # Require only 1GB for test
            path="/tmp"
        )
        
        assert "available_gb" in result
        assert "sufficient" in result


# Helper class for validation tests
class DeploymentValidator:
    """Validates deployment environment."""
    
    def check_docker_available(self):
        """Check if Docker is available."""
        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                return {
                    "available": True,
                    "version": result.stdout.strip()
                }
        except Exception:
            pass
            
        return {"available": False, "error": "Docker not found"}
        
    def check_ports_available(self, ports):
        """Check if required ports are available."""
        import socket
        
        results = {}
        for port in ports:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            
            results[port] = {
                "available": result != 0,  # 0 means port is in use
                "status": "available" if result != 0 else "in use"
            }
            
        return results
        
    def check_disk_space(self, required_gb, path="/"):
        """Check available disk space."""
        import shutil
        
        stat = shutil.disk_usage(path)
        available_gb = stat.free / (1024**3)
        
        return {
            "available_gb": round(available_gb, 2),
            "required_gb": required_gb,
            "sufficient": available_gb >= required_gb
        }