"""Centralized database configuration module for DEAN system"""

import os
from typing import Optional, Dict, Any
from urllib.parse import urlparse


def get_database_url() -> str:
    """Get database URL with proper configuration precedence.
    
    Returns:
        str: PostgreSQL connection URL
    """
    # First, check if DATABASE_URL is provided
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        # Ensure the database name is correct in the URL
        if "/dean_prod" in database_url and "/dean_production" not in database_url:
            database_url = database_url.replace("/dean_prod", "/dean_production")
        return database_url
    
    # Fallback to constructing from individual components
    host = os.getenv("POSTGRES_HOST", "dean-postgres")  # Updated default
    port = os.getenv("POSTGRES_PORT", "5432")
    user = os.getenv("POSTGRES_USER", "dean_prod")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")
    database = os.getenv("POSTGRES_DB", "dean_production")
    
    # Ensure correct database name
    if database == "dean_prod":
        database = "dean_production"
    
    return f"postgresql://{user}:{password}@{host}:{port}/{database}"


def get_database_params() -> Dict[str, Any]:
    """Get database connection parameters from URL or components.
    
    Returns:
        dict: Database connection parameters for psycopg2
    """
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        # Parse DATABASE_URL if available
        parsed = urlparse(database_url)
        database_name = parsed.path.lstrip('/')
        
        # Ensure correct database name
        if database_name == "dean_prod":
            database_name = "dean_production"
        
        return {
            'host': parsed.hostname or 'dean-postgres',
            'port': parsed.port or 5432,
            'database': database_name,
            'user': parsed.username or 'dean_prod',
            'password': parsed.password or 'postgres'
        }
    
    # Fallback to individual environment variables
    database = os.getenv("POSTGRES_DB", "dean_production")
    if database == "dean_prod":
        database = "dean_production"
    
    return {
        'host': os.getenv('POSTGRES_HOST', 'dean-postgres'),
        'port': int(os.getenv('POSTGRES_PORT', '5432')),
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