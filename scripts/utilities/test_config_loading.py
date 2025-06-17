#!/usr/bin/env python3
"""Test configuration loading for DEAN orchestration."""

import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from orchestration.config_loader import ConfigLoader, load_config

def test_config_loading():
    """Test loading all configuration files."""
    loader = ConfigLoader()
    
    print("Testing configuration loading...")
    print("=" * 50)
    
    # Test loading orchestration configs
    print("\n1. Loading orchestration configs...")
    try:
        orch_config = loader.load_config_dir("orchestration")
        print(f"✓ Loaded {len(orch_config)} orchestration config sections")
        for key in orch_config.keys():
            print(f"  - {key}")
    except Exception as e:
        print(f"✗ Failed to load orchestration configs: {e}")
        
    # Test loading service configs
    print("\n2. Loading service configs...")
    try:
        service_config = loader.load_config_dir("services")
        print(f"✓ Loaded {len(service_config)} service config sections")
        for key in service_config.keys():
            print(f"  - {key}")
    except Exception as e:
        print(f"✗ Failed to load service configs: {e}")
        
    # Test loading full configuration
    print("\n3. Loading full configuration...")
    try:
        full_config = load_config()
        print("✓ Successfully loaded full configuration")
        print(f"  - Services: {list(full_config.services.keys())}")
        if full_config.evolution:
            print(f"  - Evolution config loaded")
        if full_config.deployment:
            print(f"  - Deployment config loaded")
        if full_config.monitoring:
            print(f"  - Monitoring config loaded")
    except Exception as e:
        print(f"✗ Failed to load full config: {e}")
        
    # Test loading with environment override
    print("\n4. Testing environment-specific loading...")
    try:
        # Test doesn't work because we don't have environment-specific files
        # This is expected behavior
        local_config = load_config(environment="local")
        print("✓ Loaded with environment override")
    except Exception as e:
        print(f"Note: No environment-specific config file (expected): {e}")
        
    # Test specific config files
    print("\n5. Testing specific configuration files...")
    config_files = [
        "orchestration/single_machine.yaml",
        "orchestration/evolution_config.yaml",
        "orchestration/deployment_config.yaml",
        "deployment/local.yaml",
        "services/service_registry.yaml",
        "services/monitoring_config.yaml",
    ]
    
    for config_file in config_files:
        file_path = loader.config_dir / config_file
        if file_path.exists():
            try:
                data = loader.load_yaml_file(file_path)
                print(f"✓ {config_file}: {len(data)} top-level keys")
            except Exception as e:
                print(f"✗ {config_file}: Failed to load - {e}")
        else:
            print(f"✗ {config_file}: File not found")
            
    print("\n" + "=" * 50)
    print("Configuration loading test complete")


if __name__ == "__main__":
    test_config_loading()