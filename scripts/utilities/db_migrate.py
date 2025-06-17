#!/usr/bin/env python3
"""
Database migration tool for DEAN orchestration system.

Manages database schema migrations using a simple versioning system.
"""

import os
import sys
import argparse
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple
import hashlib
import json

# Migration directory
MIGRATIONS_DIR = Path(__file__).parent.parent.parent / "migrations"


class MigrationError(Exception):
    """Custom exception for migration errors."""
    pass


class DatabaseMigrator:
    """Handles database migrations for DEAN system."""
    
    def __init__(self, connection_params: dict):
        self.connection_params = connection_params
        self.conn = None
        self.cursor = None
        
    def connect(self):
        """Establish database connection."""
        try:
            self.conn = psycopg2.connect(**self.connection_params)
            self.conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            self.cursor = self.conn.cursor()
        except psycopg2.Error as e:
            raise MigrationError(f"Failed to connect to database: {e}")
            
    def disconnect(self):
        """Close database connection."""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
            
    def init_migration_table(self):
        """Create migration tracking table if it doesn't exist."""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS dean_migrations (
                id SERIAL PRIMARY KEY,
                version VARCHAR(255) UNIQUE NOT NULL,
                name VARCHAR(255) NOT NULL,
                checksum VARCHAR(64) NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                execution_time_ms INTEGER,
                success BOOLEAN DEFAULT TRUE,
                error_message TEXT
            );
            
            CREATE INDEX IF NOT EXISTS idx_migrations_version 
            ON dean_migrations(version);
            
            CREATE INDEX IF NOT EXISTS idx_migrations_applied_at 
            ON dean_migrations(applied_at);
        """)
        
    def get_applied_migrations(self) -> List[Tuple[str, str]]:
        """Get list of applied migrations."""
        self.cursor.execute("""
            SELECT version, checksum 
            FROM dean_migrations 
            WHERE success = TRUE 
            ORDER BY version
        """)
        return self.cursor.fetchall()
        
    def get_pending_migrations(self) -> List[Path]:
        """Get list of migrations that haven't been applied yet."""
        if not MIGRATIONS_DIR.exists():
            MIGRATIONS_DIR.mkdir(parents=True)
            return []
            
        applied = {version for version, _ in self.get_applied_migrations()}
        all_migrations = sorted([
            f for f in MIGRATIONS_DIR.glob("*.sql")
            if f.stem not in applied
        ])
        
        return all_migrations
        
    def calculate_checksum(self, content: str) -> str:
        """Calculate SHA256 checksum of migration content."""
        return hashlib.sha256(content.encode()).hexdigest()
        
    def verify_migration_checksum(self, version: str, content: str) -> bool:
        """Verify that migration hasn't been modified after application."""
        current_checksum = self.calculate_checksum(content)
        
        self.cursor.execute("""
            SELECT checksum FROM dean_migrations 
            WHERE version = %s AND success = TRUE
        """, (version,))
        
        result = self.cursor.fetchone()
        if result:
            stored_checksum = result[0]
            return current_checksum == stored_checksum
        return True
        
    def apply_migration(self, migration_file: Path) -> bool:
        """Apply a single migration."""
        version = migration_file.stem
        name = migration_file.name
        
        print(f"Applying migration: {name}")
        
        # Read migration content
        try:
            content = migration_file.read_text()
        except Exception as e:
            raise MigrationError(f"Failed to read migration file: {e}")
            
        # Verify checksum if migration was partially applied
        if not self.verify_migration_checksum(version, content):
            raise MigrationError(
                f"Migration {version} has been modified after being applied. "
                "This is not allowed for safety reasons."
            )
            
        # Apply migration
        start_time = datetime.now()
        try:
            self.cursor.execute(content)
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            # Record successful migration
            self.cursor.execute("""
                INSERT INTO dean_migrations 
                (version, name, checksum, execution_time_ms, success)
                VALUES (%s, %s, %s, %s, TRUE)
            """, (version, name, self.calculate_checksum(content), execution_time))
            
            print(f"  ✓ Applied successfully in {execution_time}ms")
            return True
            
        except psycopg2.Error as e:
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            # Record failed migration
            try:
                self.cursor.execute("""
                    INSERT INTO dean_migrations 
                    (version, name, checksum, execution_time_ms, success, error_message)
                    VALUES (%s, %s, %s, %s, FALSE, %s)
                """, (version, name, self.calculate_checksum(content), 
                      execution_time, str(e)))
            except:
                pass  # Ignore errors when recording failure
                
            print(f"  ✗ Failed: {e}")
            raise MigrationError(f"Migration {version} failed: {e}")
            
    def rollback_migration(self, version: str) -> bool:
        """Rollback a specific migration."""
        # Look for rollback file
        rollback_file = MIGRATIONS_DIR / f"{version}.rollback.sql"
        
        if not rollback_file.exists():
            raise MigrationError(
                f"No rollback file found for migration {version}. "
                f"Expected: {rollback_file}"
            )
            
        print(f"Rolling back migration: {version}")
        
        # Read rollback content
        try:
            content = rollback_file.read_text()
        except Exception as e:
            raise MigrationError(f"Failed to read rollback file: {e}")
            
        # Apply rollback
        start_time = datetime.now()
        try:
            self.cursor.execute(content)
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            # Remove migration record
            self.cursor.execute("""
                DELETE FROM dean_migrations 
                WHERE version = %s
            """, (version,))
            
            print(f"  ✓ Rolled back successfully in {execution_time}ms")
            return True
            
        except psycopg2.Error as e:
            print(f"  ✗ Rollback failed: {e}")
            raise MigrationError(f"Rollback of {version} failed: {e}")
            
    def create_migration(self, name: str) -> Path:
        """Create a new migration file."""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        version = f"{timestamp}_{name}"
        
        migration_file = MIGRATIONS_DIR / f"{version}.sql"
        rollback_file = MIGRATIONS_DIR / f"{version}.rollback.sql"
        
        # Create migration template
        migration_content = f"""-- Migration: {version}
-- Created: {datetime.now().isoformat()}
-- Description: {name.replace('_', ' ').title()}

-- Add your migration SQL here
-- Example:
-- CREATE TABLE IF NOT EXISTS example (
--     id SERIAL PRIMARY KEY,
--     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
-- );
"""
        
        rollback_content = f"""-- Rollback for migration: {version}
-- Created: {datetime.now().isoformat()}

-- Add your rollback SQL here
-- Example:
-- DROP TABLE IF EXISTS example;
"""
        
        # Write files
        migration_file.write_text(migration_content)
        rollback_file.write_text(rollback_content)
        
        print(f"Created migration files:")
        print(f"  - {migration_file}")
        print(f"  - {rollback_file}")
        
        return migration_file
        
    def get_status(self) -> dict:
        """Get migration status information."""
        applied = self.get_applied_migrations()
        pending = self.get_pending_migrations()
        
        # Get latest migration info
        self.cursor.execute("""
            SELECT version, name, applied_at, execution_time_ms
            FROM dean_migrations
            WHERE success = TRUE
            ORDER BY applied_at DESC
            LIMIT 1
        """)
        latest = self.cursor.fetchone()
        
        return {
            "applied_count": len(applied),
            "pending_count": len(pending),
            "latest_migration": {
                "version": latest[0] if latest else None,
                "name": latest[1] if latest else None,
                "applied_at": latest[2].isoformat() if latest else None,
                "execution_time_ms": latest[3] if latest else None
            } if latest else None,
            "pending_migrations": [f.name for f in pending]
        }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="DEAN Database Migration Tool")
    
    # Database connection arguments
    parser.add_argument('--host', default=os.getenv('POSTGRES_HOST', 'localhost'),
                       help='PostgreSQL host')
    parser.add_argument('--port', type=int, default=int(os.getenv('POSTGRES_PORT', 5432)),
                       help='PostgreSQL port')
    parser.add_argument('--database', default=os.getenv('POSTGRES_DB', 'dean_orchestration'),
                       help='Database name')
    parser.add_argument('--user', default=os.getenv('POSTGRES_USER', 'postgres'),
                       help='Database user')
    parser.add_argument('--password', default=os.getenv('POSTGRES_PASSWORD', ''),
                       help='Database password')
    
    # Commands
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Migrate command
    migrate_parser = subparsers.add_parser('migrate', help='Apply pending migrations')
    migrate_parser.add_argument('--dry-run', action='store_true',
                               help='Show what would be done without applying')
    
    # Rollback command
    rollback_parser = subparsers.add_parser('rollback', help='Rollback migrations')
    rollback_parser.add_argument('version', help='Migration version to rollback')
    
    # Create command
    create_parser = subparsers.add_parser('create', help='Create new migration')
    create_parser.add_argument('name', help='Migration name (use underscores)')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show migration status')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
        
    # Create connection parameters
    connection_params = {
        'host': args.host,
        'port': args.port,
        'database': args.database,
        'user': args.user,
    }
    
    if args.password:
        connection_params['password'] = args.password
        
    # Create migrator
    migrator = DatabaseMigrator(connection_params)
    
    try:
        # Connect to database
        migrator.connect()
        
        # Initialize migration table
        migrator.init_migration_table()
        
        # Execute command
        if args.command == 'migrate':
            pending = migrator.get_pending_migrations()
            
            if not pending:
                print("No pending migrations")
                return
                
            print(f"Found {len(pending)} pending migration(s)")
            
            if args.dry_run:
                print("\nPending migrations (dry run):")
                for migration in pending:
                    print(f"  - {migration.name}")
            else:
                for migration in pending:
                    migrator.apply_migration(migration)
                    
                print(f"\nApplied {len(pending)} migration(s) successfully")
                
        elif args.command == 'rollback':
            migrator.rollback_migration(args.version)
            
        elif args.command == 'create':
            migrator.create_migration(args.name)
            
        elif args.command == 'status':
            status = migrator.get_status()
            
            print("Migration Status")
            print("=" * 40)
            print(f"Applied migrations: {status['applied_count']}")
            print(f"Pending migrations: {status['pending_count']}")
            
            if status['latest_migration']:
                print(f"\nLatest migration:")
                print(f"  Version: {status['latest_migration']['version']}")
                print(f"  Applied: {status['latest_migration']['applied_at']}")
                print(f"  Duration: {status['latest_migration']['execution_time_ms']}ms")
                
            if status['pending_migrations']:
                print(f"\nPending migrations:")
                for name in status['pending_migrations']:
                    print(f"  - {name}")
                    
    except MigrationError as e:
        print(f"Migration error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        migrator.disconnect()


if __name__ == "__main__":
    main()