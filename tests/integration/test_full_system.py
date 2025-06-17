"""
Full system integration test for DEAN orchestration.

Tests the complete system integration including:
- Service discovery and connection
- CLI command execution
- Web dashboard data flow
- Configuration loading
- File path resolution
"""

import pytest
import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile
import json

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from integration import ServicePool, create_service_pool
from orchestration.config_loader import ConfigLoader, load_config


@pytest.mark.integration
class TestFullSystemIntegration:
    """Test complete system integration."""
    
    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary config directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "configs"
            config_dir.mkdir()
            
            # Create minimal test configs
            (config_dir / "services").mkdir()
            service_config = {
                "services": {
                    "orchestration": {
                        "base_url": "http://localhost:8082",
                        "health_endpoint": "/health"
                    },
                    "indexagent": {
                        "base_url": "http://localhost:8081",
                        "health_endpoint": "/health"
                    }
                }
            }
            
            with open(config_dir / "services" / "test.yaml", "w") as f:
                json.dump(service_config, f)
                
            yield config_dir
            
    @pytest.mark.asyncio
    async def test_service_discovery_and_connection(self):
        """Test that all services can be discovered and connected."""
        # Create service pool
        async with create_service_pool() as pool:
            assert pool is not None
            
            # Check that clients are initialized
            assert hasattr(pool, 'indexagent')
            assert hasattr(pool, 'airflow')
            assert hasattr(pool, 'evolution')
            assert hasattr(pool, 'health')
            
            # Test health check adapter
            assert hasattr(pool.health, 'check_all_services')
            
    @pytest.mark.asyncio
    async def test_configuration_loading(self, temp_config_dir):
        """Test that configuration files are properly loaded."""
        with patch.object(ConfigLoader, '__init__', return_value=None):
            loader = ConfigLoader()
            loader.config_dir = temp_config_dir
            loader._cache = {}
            
            # Test loading config directory
            config = loader.load_config_dir("services")
            assert isinstance(config, dict)
            assert "services" in config
            
    def test_file_paths_resolution(self):
        """Test that file paths are correctly resolved across the system."""
        # Test paths that should exist
        project_root = Path(__file__).parent.parent.parent
        
        assert (project_root / "pyproject.toml").exists()
        assert (project_root / "src").is_dir()
        assert (project_root / "tests").is_dir()
        assert (project_root / "configs").is_dir()
        assert (project_root / "scripts").is_dir()
        
        # Test configuration files
        assert (project_root / "configs" / "orchestration" / "single_machine.yaml").exists()
        assert (project_root / "configs" / "deployment" / "local.yaml").exists()
        
    def test_cli_command_structure(self):
        """Test that CLI commands are properly structured."""
        # Import CLI module to check command registration
        from interfaces.cli.dean_cli import cli
        
        # Check main commands exist
        commands = cli.commands
        command_names = list(commands.keys())
        
        assert 'deploy' in command_names
        assert 'status' in command_names
        assert 'interactive' in command_names
        assert 'evolution' in command_names
        assert 'config' in command_names
        
        # Check subcommands
        evolution_cmd = commands.get('evolution')
        assert evolution_cmd is not None
        assert hasattr(evolution_cmd, 'commands')
        
    @pytest.mark.asyncio
    async def test_web_dashboard_endpoints(self):
        """Test that web dashboard endpoints are defined."""
        from interfaces.web.app import app
        
        # Check that routes are defined
        routes = []
        for route in app.routes:
            if hasattr(route, 'path'):
                routes.append(route.path)
                
        # Check API endpoints
        assert any('/api/system/status' in str(r) for r in routes)
        assert any('/api/evolution/trials' in str(r) for r in routes)
        assert any('/api/agents' in str(r) for r in routes)
        assert any('/api/patterns' in str(r) for r in routes)
        
        # Check WebSocket endpoint
        assert any('/ws' in str(r) for r in routes)
        
    def test_import_structure(self):
        """Test that all major imports work correctly."""
        # Test orchestration imports
        from orchestration.deployment.system_deployer import SystemDeployer
        from orchestration.coordination.evolution_trial import EvolutionTrialCoordinator
        from orchestration.config_loader import ConfigLoader
        
        # Test integration imports  
        from integration import (
            ServiceClient,
            IndexAgentClient,
            AirflowClient,
            EvolutionAPIClient,
            ServicePool
        )
        
        # Test interface imports
        from interfaces.cli.interactive import InteractiveCLI
        from interfaces.web.app import app
        
        # Verify classes are importable
        assert SystemDeployer is not None
        assert EvolutionTrialCoordinator is not None
        assert ServiceClient is not None
        
    def test_environment_variables_usage(self):
        """Test that environment variables are properly used."""
        # Check common environment variables
        env_vars = [
            'DEAN_SERVER_HOST',
            'DEAN_SERVER_PORT',
            'INDEXAGENT_API_URL',
            'AIRFLOW_API_URL',
            'EVOLUTION_API_URL',
            'POSTGRES_HOST',
            'POSTGRES_PORT',
            'REDIS_HOST',
            'REDIS_PORT',
        ]
        
        # These don't need to be set, just check they can be accessed
        for var in env_vars:
            value = os.getenv(var)  # Should not raise exception
            
    @pytest.mark.asyncio 
    async def test_service_client_initialization(self):
        """Test that service clients can be properly initialized."""
        from integration.indexagent_client import IndexAgentClient
        from integration.airflow_client import AirflowClient
        from integration.infra_client import EvolutionAPIClient
        
        # Test creating clients
        indexagent = IndexAgentClient("http://localhost:8081")
        assert indexagent.base_url == "http://localhost:8081"
        
        airflow = AirflowClient("http://localhost:8080")
        assert airflow.base_url == "http://localhost:8080"
        
        evolution = EvolutionAPIClient("http://localhost:8083")
        assert evolution.base_url == "http://localhost:8083"
        
    def test_static_files_exist(self):
        """Test that static web files exist."""
        project_root = Path(__file__).parent.parent.parent
        static_dir = project_root / "src" / "interfaces" / "web" / "static"
        
        # Check static files
        assert (static_dir / "index.html").exists()
        assert (static_dir / "css" / "dashboard.css").exists()
        assert (static_dir / "js" / "dashboard.js").exists()
        
    def test_migration_files_exist(self):
        """Test that database migration files exist."""
        project_root = Path(__file__).parent.parent.parent
        migrations_dir = project_root / "migrations"
        
        assert migrations_dir.exists()
        
        # Check initial schema
        assert (migrations_dir / "20240101000001_initial_schema.sql").exists()
        assert (migrations_dir / "20240101000001_initial_schema.rollback.sql").exists()
        
    def test_deployment_scripts_executable(self):
        """Test that deployment scripts are marked executable."""
        project_root = Path(__file__).parent.parent.parent
        scripts_dir = project_root / "scripts"
        
        # Check deploy scripts
        deploy_scripts = [
            scripts_dir / "deploy" / "deploy_local.sh",
            scripts_dir / "deploy" / "deploy_production.sh",
            scripts_dir / "deploy" / "health_check.sh",
            scripts_dir / "deploy" / "rollback.sh",
        ]
        
        for script in deploy_scripts:
            assert script.exists(), f"Script {script} does not exist"
            # Check if executable (Unix only)
            if os.name != 'nt':  # Not Windows
                assert os.access(script, os.X_OK), f"Script {script} is not executable"
                
    def test_utility_scripts_executable(self):
        """Test that utility scripts are marked executable."""
        project_root = Path(__file__).parent.parent.parent
        utilities_dir = project_root / "scripts" / "utilities"
        
        # Check utility scripts
        utility_scripts = [
            utilities_dir / "monitor_system.py",
            utilities_dir / "backup_restore.sh",
            utilities_dir / "db_migrate.py",
            utilities_dir / "analyze_logs.py",
            utilities_dir / "verify_paths.py",
        ]
        
        for script in utility_scripts:
            assert script.exists(), f"Script {script} does not exist"
            # Check if executable (Unix only)
            if os.name != 'nt':  # Not Windows
                assert os.access(script, os.X_OK), f"Script {script} is not executable"


@pytest.mark.integration
class TestSystemConfiguration:
    """Test system configuration integration."""
    
    def test_all_config_files_valid_structure(self):
        """Test that all configuration files have valid structure."""
        project_root = Path(__file__).parent.parent.parent
        configs_dir = project_root / "configs"
        
        # List all config files
        config_files = list(configs_dir.rglob("*.yaml")) + list(configs_dir.rglob("*.yml"))
        
        assert len(config_files) > 0, "No configuration files found"
        
        for config_file in config_files:
            # Just check they can be read
            content = config_file.read_text()
            assert len(content) > 0, f"Config file {config_file} is empty"
            
            # Check for basic YAML structure (crude check)
            assert ":" in content, f"Config file {config_file} doesn't look like YAML"
            
    def test_required_config_files_exist(self):
        """Test that all required configuration files exist."""
        project_root = Path(__file__).parent.parent.parent
        configs_dir = project_root / "configs"
        
        required_configs = [
            "orchestration/evolution_config.yaml",
            "orchestration/deployment_config.yaml",
            "orchestration/single_machine.yaml",
            "deployment/local.yaml",
            "services/service_registry.yaml",
            "services/monitoring_config.yaml",
        ]
        
        for config_path in required_configs:
            full_path = configs_dir / config_path
            assert full_path.exists(), f"Required config {config_path} is missing"
            
    def test_example_configs_exist(self):
        """Test that example configuration files exist."""
        project_root = Path(__file__).parent.parent.parent
        examples_dir = project_root / "examples" / "configs"
        
        assert examples_dir.exists()
        
        example_configs = [
            "local_development.yaml",
            "production_example.yaml",
        ]
        
        for config_name in example_configs:
            config_path = examples_dir / config_name
            assert config_path.exists(), f"Example config {config_name} is missing"