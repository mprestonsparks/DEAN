"""Centralized database configuration module for DEAN system"""

import os
from typing import Optional, Dict, Any


def get_database_url() -> str:
    """Get database URL with consistent database name.
    
    Returns:
        str: PostgreSQL connection URL
    """
    host = os.getenv("POSTGRES_HOST", "postgres")
    port = os.getenv("POSTGRES_PORT", "5432")
    user = os.getenv("POSTGRES_USER", "dean_prod")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")
    # Ensure consistent database name
    database = os.getenv("POSTGRES_DB", "dean_production")
    
    # Override any legacy dean_prod references
    if database == "dean_prod":
        database = "dean_production"
    
    return f"postgresql://{user}:{password}@{host}:{port}/{database}"


def get_database_params() -> Dict[str, Any]:
    """Get database connection parameters as a dictionary.
    
    Returns:
        dict: Database connection parameters for psycopg2
    """
    # Ensure consistent database name
    database = os.getenv("POSTGRES_DB", "dean_production")
    
    # Override any legacy dean_prod references
    if database == "dean_prod":
        database = "dean_production"
    
    return {
        'host': os.getenv('POSTGRES_HOST', 'postgres'),
        'port': os.getenv('POSTGRES_PORT', '5432'),
        'database': database,
        'user': os.getenv('POSTGRES_USER', 'dean_prod'),
        'password': os.getenv('POSTGRES_PASSWORD', 'postgres')
    }


def validate_database_config() -> bool:
    """Validate that database configuration is correct.
    
    Returns:
        bool: True if configuration is valid
    """
    params = get_database_params()
    
    # Check that database name is correct
    if params['database'] != 'dean_production':
        print(f"WARNING: Database name '{params['database']}' does not match expected 'dean_production'")
        return False
    
    # Check that required parameters are present
    required_params = ['host', 'port', 'database', 'user', 'password']
    for param in required_params:
        if not params.get(param):
            print(f"ERROR: Missing required database parameter: {param}")
            return False
    
    return True


if __name__ == "__main__":
    # Test the configuration
    print("Database Configuration:")
    print("-" * 40)
    params = get_database_params()
    for key, value in params.items():
        if key == 'password':
            print(f"{key}: {'*' * len(str(value))}")
        else:
            print(f"{key}: {value}")
    
    print("\nDatabase URL:")
    print("-" * 40)
    url = get_database_url()
    # Mask password in URL
    if '@' in url:
        parts = url.split('@')
        creds = parts[0].split('://')[-1]
        if ':' in creds:
            user, _ = creds.split(':', 1)
            masked_url = f"{parts[0].split('://')[0]}://{user}:****@{parts[1]}"
            print(masked_url)
        else:
            print(url)
    else:
        print(url)
    
    print("\nValidation:")
    print("-" * 40)
    if validate_database_config():
        print("✓ Database configuration is valid")
    else:
        print("✗ Database configuration has issues")