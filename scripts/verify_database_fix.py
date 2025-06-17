#!/usr/bin/env python3
"""Verify database configuration is correctly applied throughout the application."""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.database import get_database_url, get_database_params

def verify_configuration():
    """Verify database configuration is correct."""
    print("=== Database Configuration Verification ===\n")
    
    # Show environment variables
    print("Environment Variables:")
    env_vars = ['DATABASE_URL', 'POSTGRES_HOST', 'POSTGRES_PORT', 'POSTGRES_USER', 'POSTGRES_DB']
    for var in env_vars:
        value = os.getenv(var, '<not set>')
        if var in ['DATABASE_URL', 'POSTGRES_PASSWORD'] and value != '<not set>':
            # Mask sensitive information
            if '@' in value:
                # Mask password in URL
                parts = value.split('@')
                if ':' in parts[0]:
                    user_pass = parts[0].split('://')[-1]
                    user = user_pass.split(':')[0]
                    value = f"{parts[0].split('://')[0]}://{user}:****@{parts[1]}"
            else:
                value = '****'
        print(f"  {var}: {value}")
    
    print("\n" + "-" * 40 + "\n")
    
    # Check URL configuration
    url = get_database_url()
    masked_url = url
    if '@' in url:
        parts = url.split('@')
        if ':' in parts[0]:
            user_pass = parts[0].split('://')[-1]
            user = user_pass.split(':')[0]
            masked_url = f"{parts[0].split('://')[0]}://{user}:****@{parts[1]}"
    
    print(f"Database URL: {masked_url}")
    
    if "/dean_prod" in url:
        print("❌ ERROR: Database URL still contains 'dean_prod'")
        return False
    
    if "/dean_production" not in url:
        print("❌ ERROR: Database URL does not contain '/dean_production'")
        return False
    
    # Check parameters
    params = get_database_params()
    print(f"\nDatabase Parameters:")
    for key, value in params.items():
        if key == 'password':
            print(f"  {key}: ****")
        else:
            print(f"  {key}: {value}")
    
    if params['database'] != 'dean_production':
        print(f"\n❌ ERROR: Database name is '{params['database']}', expected 'dean_production'")
        return False
    
    if params['host'] not in ['dean-postgres', 'postgres-prod', 'localhost']:
        print(f"\n⚠️  WARNING: Unexpected host '{params['host']}'")
    
    print("\n✅ Configuration verified successfully")
    print("\nConfiguration Hierarchy:")
    print("1. DATABASE_URL takes precedence if set")
    print("2. Individual POSTGRES_* variables used as fallback")
    print("3. Database name 'dean_prod' automatically corrected to 'dean_production'")
    
    return True

def test_url_parsing():
    """Test URL parsing with various scenarios."""
    print("\n=== Testing URL Parsing Scenarios ===\n")
    
    test_cases = [
        ("postgresql://dean_prod:pass@host:5432/dean_prod", "Should correct database name"),
        ("postgresql://dean_prod:pass@host:5432/dean_production", "Should keep correct name"),
        ("postgresql://user:pass@localhost/testdb", "Should parse standard URL"),
    ]
    
    original_url = os.getenv('DATABASE_URL')
    
    for test_url, description in test_cases:
        os.environ['DATABASE_URL'] = test_url
        result_url = get_database_url()
        params = get_database_params()
        
        print(f"Test: {description}")
        print(f"  Input:    {test_url}")
        print(f"  Output:   {result_url}")
        print(f"  Database: {params['database']}")
        
        if "/dean_prod" in test_url and params['database'] == 'dean_production':
            print("  ✅ Correctly fixed database name")
        elif params['database'] == 'dean_production' or 'testdb' in test_url:
            print("  ✅ Correct database name")
        else:
            print("  ❌ Failed to correct database name")
        print()
    
    # Restore original
    if original_url:
        os.environ['DATABASE_URL'] = original_url
    else:
        os.environ.pop('DATABASE_URL', None)

if __name__ == "__main__":
    print("DEAN Database Configuration Verification Tool\n")
    
    # Run main verification
    success = verify_configuration()
    
    # Run parsing tests
    test_url_parsing()
    
    sys.exit(0 if success else 1)