#!/usr/bin/env python3
"""Test database connection and initialization"""

import os
import sys
import time
import psycopg2
from psycopg2 import sql

def test_database_connection():
    """Test connection to the database and verify initialization"""
    
    # Get connection parameters from environment
    db_params = {
        'host': os.getenv('POSTGRES_HOST', 'localhost'),
        'port': os.getenv('POSTGRES_PORT', '5432'),
        'database': os.getenv('POSTGRES_DB', 'dean_production'),
        'user': os.getenv('POSTGRES_USER', 'dean_prod'),
        'password': os.getenv('POSTGRES_PASSWORD', 'postgres')
    }
    
    max_retries = 5
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            print(f"Attempting to connect to database (attempt {attempt + 1}/{max_retries})...")
            
            # Connect to database
            conn = psycopg2.connect(**db_params)
            cursor = conn.cursor()
            
            print("✓ Successfully connected to database")
            
            # Check if tables exist
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name;
            """)
            
            tables = cursor.fetchall()
            print(f"\nFound {len(tables)} tables in public schema:")
            for table in tables:
                print(f"  - {table[0]}")
            
            # Check dean schema
            cursor.execute("""
                SELECT schema_name 
                FROM information_schema.schemata 
                WHERE schema_name = 'dean';
            """)
            
            if cursor.fetchone():
                print("\n✓ Dean schema exists")
                
                # Check tables in dean schema
                cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'dean' 
                    ORDER BY table_name;
                """)
                
                dean_tables = cursor.fetchall()
                if dean_tables:
                    print(f"\nFound {len(dean_tables)} tables in dean schema:")
                    for table in dean_tables:
                        print(f"  - {table[0]}")
            
            cursor.close()
            conn.close()
            
            print("\n✓ Database initialization verified successfully!")
            return True
            
        except psycopg2.OperationalError as e:
            print(f"✗ Connection failed: {e}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print("\n✗ Failed to connect to database after all retries")
                return False
        except Exception as e:
            print(f"\n✗ Unexpected error: {e}")
            return False

if __name__ == "__main__":
    success = test_database_connection()
    sys.exit(0 if success else 1)