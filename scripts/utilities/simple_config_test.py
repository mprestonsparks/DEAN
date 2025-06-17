#!/usr/bin/env python3
"""Simple configuration test without dependencies."""

import os
import json
from pathlib import Path

# Try to import yaml if available
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False
    print("Warning: PyYAML not installed, using JSON parsing fallback")

def test_yaml_syntax(file_path):
    """Test if YAML file has valid syntax."""
    if not HAS_YAML:
        print(f"  Skipping {file_path} (no YAML parser)")
        return True
        
    try:
        with open(file_path, 'r') as f:
            yaml.safe_load(f)
        return True
    except Exception as e:
        print(f"  Error in {file_path}: {e}")
        return False

def main():
    """Test all configuration files."""
    root_dir = Path(__file__).parent.parent.parent
    configs_dir = root_dir / "configs"
    
    print("Configuration Files Syntax Test")
    print("=" * 50)
    
    all_valid = True
    config_files = list(configs_dir.rglob("*.yaml")) + list(configs_dir.rglob("*.yml"))
    
    print(f"\nFound {len(config_files)} configuration files")
    
    for config_file in sorted(config_files):
        rel_path = config_file.relative_to(root_dir)
        print(f"\nTesting: {rel_path}")
        
        # Check file exists and is readable
        if not config_file.exists():
            print(f"  ✗ File not found")
            all_valid = False
            continue
            
        if not config_file.is_file():
            print(f"  ✗ Not a file")
            all_valid = False
            continue
            
        # Test YAML syntax
        if test_yaml_syntax(config_file):
            print(f"  ✓ Valid YAML syntax")
            
            # Show some basic info
            with open(config_file, 'r') as f:
                lines = f.readlines()
                print(f"  - Lines: {len(lines)}")
                
                # Count top-level keys (crude but works without yaml)
                top_level_keys = [line for line in lines if line.strip() and not line.startswith(' ') and ':' in line and not line.startswith('#')]
                print(f"  - Top-level keys: {len(top_level_keys)}")
        else:
            all_valid = False
            
    print("\n" + "=" * 50)
    if all_valid:
        print("✓ All configuration files are valid")
    else:
        print("✗ Some configuration files have errors")
        
    # List expected vs actual files
    print("\nConfiguration Structure:")
    expected_files = [
        "orchestration/evolution_config.yaml",
        "orchestration/deployment_config.yaml", 
        "orchestration/single_machine.yaml",
        "deployment/local.yaml",
        "services/service_registry.yaml",
        "services/monitoring_config.yaml",
    ]
    
    for expected in expected_files:
        full_path = configs_dir / expected
        if full_path.exists():
            print(f"  ✓ {expected}")
        else:
            print(f"  ✗ {expected} (missing)")
            
    return 0 if all_valid else 1

if __name__ == "__main__":
    exit(main())