"""Configuration loader for DEAN orchestration.

This module provides utilities to load and merge configuration from multiple sources:
- Default configuration files
- Environment-specific overrides
- Environment variables
- Runtime overrides
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional, Union
import yaml
from pydantic import BaseModel, Field, validator
from structlog import get_logger

logger = get_logger(__name__)


class ConfigurationError(Exception):
    """Raised when configuration loading fails."""
    pass


class ServiceConfig(BaseModel):
    """Configuration for a single service."""
    
    name: Optional[str] = None
    base_url: str
    api_base: Optional[str] = None
    health_endpoint: str = "/health"
    timeout: int = 30
    retries: int = 3
    auth: Optional[Dict[str, Any]] = None
    

class EvolutionConfig(BaseModel):
    """Evolution trial configuration."""
    
    class DefaultsConfig(BaseModel):
        generations: int = 10
        population_size: int = 20
        mutation_rate: float = 0.1
        crossover_rate: float = 0.7
        elite_size: int = 2
        tournament_size: int = 3
        
    class FitnessConfig(BaseModel):
        weights: Dict[str, float]
        thresholds: Dict[str, float]
        
    class ConstraintsConfig(BaseModel):
        max_trial_duration: int = 3600
        max_memory_per_agent: int = 512
        max_cpu_per_agent: float = 1.0
        max_concurrent_evaluations: int = 5
        
    defaults: DefaultsConfig = Field(default_factory=DefaultsConfig)
    fitness: FitnessConfig
    constraints: ConstraintsConfig = Field(default_factory=ConstraintsConfig)
    

class DeploymentConfig(BaseModel):
    """Deployment configuration."""
    
    environment: str = "development"
    deployment_order: list[str]
    health_checks: Dict[str, Any]
    dependencies: Dict[str, Dict[str, Any]]
    rollback: Dict[str, Any]
    resources: Dict[str, Any]
    

class MonitoringConfig(BaseModel):
    """Monitoring configuration."""
    
    metrics: Dict[str, Any]
    logging: Dict[str, Any]
    tracing: Dict[str, Any]
    alerts: Dict[str, Any]
    

class DEANConfig(BaseModel):
    """Complete DEAN orchestration configuration."""
    
    services: Dict[str, ServiceConfig]
    evolution: Optional[EvolutionConfig] = None
    deployment: Optional[DeploymentConfig] = None
    monitoring: Optional[MonitoringConfig] = None
    
    class Config:
        extra = "allow"  # Allow additional fields


class ConfigLoader:
    """Loads and manages DEAN configuration."""
    
    def __init__(self, config_dir: Optional[Path] = None):
        """Initialize the configuration loader.
        
        Args:
            config_dir: Base directory for configuration files.
                       Defaults to configs/ in the project root.
        """
        if config_dir is None:
            # Find project root (where pyproject.toml is)
            current = Path(__file__).parent
            while current != current.parent:
                if (current / "pyproject.toml").exists():
                    config_dir = current / "configs"
                    break
                current = current.parent
            else:
                config_dir = Path.cwd() / "configs"
                
        self.config_dir = Path(config_dir)
        self._cache: Dict[str, Any] = {}
        
    def load_yaml_file(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """Load a YAML configuration file.
        
        Args:
            file_path: Path to the YAML file
            
        Returns:
            Parsed configuration dictionary
            
        Raises:
            ConfigurationError: If file cannot be loaded
        """
        path = Path(file_path)
        
        try:
            with open(path) as f:
                content = f.read()
                
            # Expand environment variables
            content = os.path.expandvars(content)
            
            return yaml.safe_load(content) or {}
            
        except FileNotFoundError:
            raise ConfigurationError(f"Configuration file not found: {path}")
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML in {path}: {e}")
        except Exception as e:
            raise ConfigurationError(f"Failed to load {path}: {e}")
            
    def load_config_dir(self, subdir: str) -> Dict[str, Any]:
        """Load all YAML files from a configuration subdirectory.
        
        Args:
            subdir: Subdirectory name (e.g., 'orchestration', 'services')
            
        Returns:
            Merged configuration from all files in the directory
        """
        dir_path = self.config_dir / subdir
        
        if not dir_path.exists():
            logger.warning(f"Configuration directory not found: {dir_path}")
            return {}
            
        config = {}
        
        for file_path in sorted(dir_path.glob("*.yaml")):
            logger.debug(f"Loading config file: {file_path}")
            file_config = self.load_yaml_file(file_path)
            
            # Deep merge configurations
            config = self._deep_merge(config, file_config)
            
        return config
        
    def load_full_config(
        self,
        environment: Optional[str] = None,
        overrides: Optional[Dict[str, Any]] = None
    ) -> DEANConfig:
        """Load the complete DEAN configuration.
        
        Args:
            environment: Environment name (development, staging, production)
            overrides: Runtime configuration overrides
            
        Returns:
            Complete configuration object
        """
        # Start with base configuration
        config = {}
        
        # Load orchestration configs
        orchestration_config = self.load_config_dir("orchestration")
        config = self._deep_merge(config, orchestration_config)
        
        # Load service configs
        service_config = self.load_config_dir("services")
        config = self._deep_merge(config, service_config)
        
        # Load environment-specific config if specified
        if environment:
            env_file = self.config_dir / f"{environment}.yaml"
            if env_file.exists():
                env_config = self.load_yaml_file(env_file)
                config = self._deep_merge(config, env_config)
                
        # Apply runtime overrides
        if overrides:
            config = self._deep_merge(config, overrides)
            
        # Convert service configs to ServiceConfig objects
        if "services" in config:
            for name, service_data in config["services"].items():
                if isinstance(service_data, dict):
                    if "name" not in service_data:
                        service_data["name"] = name
                    config["services"][name] = ServiceConfig(**service_data)
                    
        # Create and validate configuration object
        try:
            return DEANConfig(**config)
        except Exception as e:
            raise ConfigurationError(f"Invalid configuration: {e}")
            
    def _deep_merge(self, base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries.
        
        Args:
            base: Base dictionary
            update: Dictionary with updates
            
        Returns:
            Merged dictionary
        """
        result = base.copy()
        
        for key, value in update.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
                
        return result
        
    def get_service_config(self, service_name: str) -> ServiceConfig:
        """Get configuration for a specific service.
        
        Args:
            service_name: Name of the service
            
        Returns:
            Service configuration
            
        Raises:
            ConfigurationError: If service not found
        """
        config = self.load_full_config()
        
        if service_name not in config.services:
            raise ConfigurationError(f"Service not found: {service_name}")
            
        return config.services[service_name]


# Singleton instance
_config_loader: Optional[ConfigLoader] = None


def get_config_loader() -> ConfigLoader:
    """Get the singleton configuration loader instance."""
    global _config_loader
    
    if _config_loader is None:
        _config_loader = ConfigLoader()
        
    return _config_loader


def load_config(
    environment: Optional[str] = None,
    overrides: Optional[Dict[str, Any]] = None
) -> DEANConfig:
    """Convenience function to load configuration.
    
    Args:
        environment: Environment name
        overrides: Runtime overrides
        
    Returns:
        Complete configuration object
    """
    loader = get_config_loader()
    return loader.load_full_config(environment, overrides)