#!/usr/bin/env python3
"""Verify database configuration consistency."""

import os
import sys
import psycopg2
from pathlib import Path

# Add parent directory to path to import from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from src.core.database import get_database_url, get_database_params
except ImportError:
    print("ERROR: Could not import database configuration module")
    print("Please ensure src/core/database.py exists")
    sys.exit(1)


def check_environment():
    """Verify environment variables."""
    db_name = os.getenv("POSTGRES_DB", "dean_production")
    print(f"Environment POSTGRES_DB: {db_name}")
    
    if db_name != "dean_production":
        print(f"WARNING: POSTGRES_DB is '{db_name}', expected 'dean_production'")
        return False
    return True


def check_connection_string():
    """Verify database connection string."""
    try:
        url = get_database_url()
        print(f"Database URL: {url.replace(os.getenv('POSTGRES_PASSWORD', 'postgres'), '****')}")
        
        if "dean_prod/" in url and "dean_production" not in url:
            print("ERROR: Database URL contains 'dean_prod' instead of 'dean_production'")
            return False
            
        if "/dean_production" not in url:
            print("ERROR: Database URL does not contain '/dean_production'")
            return False
            
    except Exception as e:
        print(f"ERROR: Could not get database URL: {e}")
        return False
    
    return True


def check_configuration_files():
    """Check configuration files for consistency."""
    issues = []
    
    # Check .env.production.template
    prod_template = Path(__file__).parent.parent / ".env.production.template"
    if prod_template.exists():
        with open(prod_template, 'r') as f:
            content = f.read()
            if "POSTGRES_DB=dean_production" not in content:
                issues.append(f"{prod_template}: Missing or incorrect POSTGRES_DB setting")
            if "DATABASE_URL" in content and "/dean_production" not in content:
                issues.append(f"{prod_template}: DATABASE_URL does not reference dean_production")
    else:
        issues.append(".env.production.template not found")
    
    # Check docker-compose files
    compose_files = [
        Path(__file__).parent.parent / "docker-compose.prod.yml",
        Path(__file__).parent.parent / "docker-compose.dev.yml"
    ]
    
    for compose_file in compose_files:
        if compose_file.exists():
            with open(compose_file, 'r') as f:
                content = f.read()
                # Production should reference environment variables
                if "prod.yml" in str(compose_file) and "POSTGRES_DB}" not in content:
                    issues.append(f"{compose_file}: Should use POSTGRES_DB environment variable")
        else:
            print(f"Note: {compose_file} not found (may be okay)")
    
    if issues:
        print("\nConfiguration file issues found:")
        for issue in issues:
            print(f"  - {issue}")
        return False
    else:
        print("Configuration files are consistent")
        return True


def test_database_connection():
    """Test actual database connection."""
    try:
        params = get_database_params()
        print(f"\nTesting connection to: {params['database']} as user {params['user']}...")
        
        conn = psycopg2.connect(**params)
        cur = conn.cursor()
        
        # Check current database
        cur.execute("SELECT current_database();")
        db_name = cur.fetchone()[0]
        print(f"Successfully connected to database: {db_name}")
        
        if db_name != "dean_production":
            print(f"WARNING: Connected to '{db_name}' instead of 'dean_production'")
            conn.close()
            return False
        
        # Check if tables exist
        cur.execute("""
            SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name IN ('agents', 'tasks', 'patterns');
        """)
        table_count = cur.fetchone()[0]
        print(f"Found {table_count} DEAN tables in database")
        
        # Check for dean schema
        cur.execute("""
            SELECT COUNT(*) FROM information_schema.schemata 
            WHERE schema_name = 'dean';
        """)
        schema_exists = cur.fetchone()[0] > 0
        if schema_exists:
            print("Dean schema exists")
        
        conn.close()
        return True
        
    except psycopg2.OperationalError as e:
        error_msg = str(e)
        print(f"Database connection failed: {error_msg}")
        
        # Parse error to identify specific issue
        if "database \"dean_prod\" does not exist" in error_msg:
            print("\nERROR: The application is trying to connect to 'dean_prod' database")
            print("This indicates a configuration issue - check environment variables")
        elif "database \"dean_production\" does not exist" in error_msg:
            print("\nERROR: The 'dean_production' database does not exist")
            print("The database needs to be created with the initialization scripts")
        elif "password authentication failed" in error_msg:
            print("\nERROR: Authentication failed - check credentials")
        elif "could not connect to server" in error_msg:
            print("\nERROR: Cannot connect to PostgreSQL server")
            print("Check that PostgreSQL is running and accessible")
            
        return False
    except Exception as e:
        print(f"Unexpected error during connection test: {e}")
        return False


def check_python_source_files():
    """Check Python source files for hardcoded database references."""
    issues = []
    src_dir = Path(__file__).parent.parent / "src"
    
    # Check for files that might have hardcoded "dean_prod" as database name
    python_files = list(src_dir.rglob("*.py"))
    
    for py_file in python_files:
        try:
            with open(py_file, 'r') as f:
                content = f.read()
                # Check for potential database name issues
                if "'dean_prod'" in content or '"dean_prod"' in content:
                    # Check if it's being used as a database name (not username)
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if 'dean_prod' in line and 'database' in line.lower():
                            issues.append(f"{py_file}:{i+1} - Potential hardcoded database name")
        except Exception:
            pass
    
    if issues:
        print("\nPotential issues in Python source files:")
        for issue in issues:
            print(f"  - {issue}")
        return False
    else:
        print("No hardcoded database name issues found in Python sources")
        return True


if __name__ == "__main__":
    print("=== DEAN Database Configuration Verification ===\n")
    
    checks = [
        ("Environment Check", check_environment),
        ("Connection String Check", check_connection_string),
        ("Configuration Files Check", check_configuration_files),
        ("Python Source Files Check", check_python_source_files),
        ("Database Connection Test", test_database_connection)
    ]
    
    all_passed = True
    for check_name, check_func in checks:
        print(f"\n{check_name}:")
        print("-" * 40)
        try:
            if not check_func():
                all_passed = False
        except Exception as e:
            print(f"ERROR: Check failed with exception: {e}")
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("✅ All database configuration checks passed!")
        print("\nThe database configuration is consistent:")
        print("- Database name: dean_production")
        print("- Database user: dean_prod")
    else:
        print("❌ Some checks failed. Please review the configuration.")
        print("\nRecommended actions:")
        print("1. Ensure POSTGRES_DB environment variable is set to 'dean_production'")
        print("2. Verify PostgreSQL initialization scripts have been run")
        print("3. Check that no code is hardcoding 'dean_prod' as database name")
        
    sys.exit(0 if all_passed else 1)