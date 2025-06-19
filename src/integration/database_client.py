#!/usr/bin/env python3
"""
Database Client for DEAN Infrastructure
Provides direct database access and management capabilities
"""

import asyncio
import json
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import asyncpg
import logging
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class DatabaseClient:
    """
    Direct database client for DEAN system.
    Provides connection pooling, query execution, and transaction management.
    """
    
    def __init__(
        self,
        database_url: str,
        min_pool_size: int = 10,
        max_pool_size: int = 20,
        command_timeout: float = 60.0
    ):
        """
        Initialize database client.
        
        Args:
            database_url: PostgreSQL connection URL
            min_pool_size: Minimum number of connections in pool
            max_pool_size: Maximum number of connections in pool
            command_timeout: Default command timeout in seconds
        """
        self.database_url = database_url
        self.min_pool_size = min_pool_size
        self.max_pool_size = max_pool_size
        self.command_timeout = command_timeout
        self.pool: Optional[asyncpg.Pool] = None
        
    async def connect(self):
        """Establish database connection pool"""
        if self.pool:
            return
        
        try:
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=self.min_pool_size,
                max_size=self.max_pool_size,
                command_timeout=self.command_timeout
            )
            logger.info(f"Database pool created with {self.min_pool_size}-{self.max_pool_size} connections")
        except Exception as e:
            logger.error(f"Failed to create database pool: {e}")
            raise
    
    async def disconnect(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
            self.pool = None
            logger.info("Database pool closed")
    
    @asynccontextmanager
    async def acquire(self):
        """Acquire a database connection from the pool"""
        if not self.pool:
            await self.connect()
        
        async with self.pool.acquire() as connection:
            yield connection
    
    @asynccontextmanager
    async def transaction(self):
        """Execute queries within a transaction"""
        async with self.acquire() as connection:
            async with connection.transaction():
                yield connection
    
    async def execute(
        self,
        query: str,
        *args,
        timeout: Optional[float] = None
    ) -> str:
        """
        Execute a query without returning results.
        
        Args:
            query: SQL query to execute
            *args: Query parameters
            timeout: Query timeout in seconds
            
        Returns:
            Status message
        """
        async with self.acquire() as connection:
            result = await connection.execute(query, *args, timeout=timeout)
            return result
    
    async def fetch(
        self,
        query: str,
        *args,
        timeout: Optional[float] = None
    ) -> List[asyncpg.Record]:
        """
        Execute a query and fetch all results.
        
        Args:
            query: SQL query to execute
            *args: Query parameters
            timeout: Query timeout in seconds
            
        Returns:
            List of records
        """
        async with self.acquire() as connection:
            return await connection.fetch(query, *args, timeout=timeout)
    
    async def fetchrow(
        self,
        query: str,
        *args,
        timeout: Optional[float] = None
    ) -> Optional[asyncpg.Record]:
        """
        Execute a query and fetch a single row.
        
        Args:
            query: SQL query to execute
            *args: Query parameters
            timeout: Query timeout in seconds
            
        Returns:
            Single record or None
        """
        async with self.acquire() as connection:
            return await connection.fetchrow(query, *args, timeout=timeout)
    
    async def fetchval(
        self,
        query: str,
        *args,
        column: int = 0,
        timeout: Optional[float] = None
    ) -> Any:
        """
        Execute a query and fetch a single value.
        
        Args:
            query: SQL query to execute
            *args: Query parameters
            column: Column index to fetch
            timeout: Query timeout in seconds
            
        Returns:
            Single value
        """
        async with self.acquire() as connection:
            return await connection.fetchval(query, *args, column=column, timeout=timeout)
    
    async def create_table(
        self,
        table_name: str,
        columns: Dict[str, str],
        constraints: Optional[List[str]] = None,
        if_not_exists: bool = True
    ):
        """
        Create a table with specified columns and constraints.
        
        Args:
            table_name: Name of the table
            columns: Dict mapping column names to types
            constraints: List of constraint definitions
            if_not_exists: Whether to use IF NOT EXISTS clause
        """
        # Build column definitions
        column_defs = [f"{name} {dtype}" for name, dtype in columns.items()]
        
        # Add constraints if provided
        if constraints:
            column_defs.extend(constraints)
        
        # Build query
        if_not_exists_clause = "IF NOT EXISTS" if if_not_exists else ""
        query = f"""
            CREATE TABLE {if_not_exists_clause} {table_name} (
                {', '.join(column_defs)}
            )
        """
        
        await self.execute(query)
        logger.info(f"Table {table_name} created")
    
    async def insert(
        self,
        table_name: str,
        data: Union[Dict[str, Any], List[Dict[str, Any]]],
        returning: Optional[str] = None,
        on_conflict: Optional[str] = None
    ) -> Optional[List[asyncpg.Record]]:
        """
        Insert data into a table.
        
        Args:
            table_name: Name of the table
            data: Single dict or list of dicts to insert
            returning: RETURNING clause
            on_conflict: ON CONFLICT clause
            
        Returns:
            Returned records if RETURNING specified
        """
        # Normalize to list
        records = data if isinstance(data, list) else [data]
        
        if not records:
            return None
        
        # Get columns from first record
        columns = list(records[0].keys())
        
        # Build values clause
        values_clause = ", ".join(
            f"({', '.join(f'${i+1}' for i in range(len(columns)))})"
            for _ in records
        )
        
        # Build query
        query_parts = [
            f"INSERT INTO {table_name}",
            f"({', '.join(columns)})",
            f"VALUES {values_clause}"
        ]
        
        if on_conflict:
            query_parts.append(f"ON CONFLICT {on_conflict}")
        
        if returning:
            query_parts.append(f"RETURNING {returning}")
        
        query = " ".join(query_parts)
        
        # Flatten values
        values = []
        for record in records:
            values.extend(record[col] for col in columns)
        
        # Execute query
        if returning:
            return await self.fetch(query, *values)
        else:
            await self.execute(query, *values)
            return None
    
    async def update(
        self,
        table_name: str,
        set_values: Dict[str, Any],
        where_clause: str,
        where_params: Optional[List[Any]] = None,
        returning: Optional[str] = None
    ) -> Optional[List[asyncpg.Record]]:
        """
        Update records in a table.
        
        Args:
            table_name: Name of the table
            set_values: Dict of column:value to set
            where_clause: WHERE clause (without WHERE keyword)
            where_params: Parameters for WHERE clause
            returning: RETURNING clause
            
        Returns:
            Updated records if RETURNING specified
        """
        # Build SET clause
        set_parts = []
        params = []
        
        for i, (col, val) in enumerate(set_values.items(), 1):
            set_parts.append(f"{col} = ${i}")
            params.append(val)
        
        # Add WHERE parameters
        if where_params:
            params.extend(where_params)
        
        # Build query
        query_parts = [
            f"UPDATE {table_name}",
            f"SET {', '.join(set_parts)}",
            f"WHERE {where_clause}"
        ]
        
        if returning:
            query_parts.append(f"RETURNING {returning}")
        
        query = " ".join(query_parts)
        
        # Execute query
        if returning:
            return await self.fetch(query, *params)
        else:
            await self.execute(query, *params)
            return None
    
    async def delete(
        self,
        table_name: str,
        where_clause: str,
        where_params: Optional[List[Any]] = None,
        returning: Optional[str] = None
    ) -> Optional[List[asyncpg.Record]]:
        """
        Delete records from a table.
        
        Args:
            table_name: Name of the table
            where_clause: WHERE clause (without WHERE keyword)
            where_params: Parameters for WHERE clause
            returning: RETURNING clause
            
        Returns:
            Deleted records if RETURNING specified
        """
        query_parts = [
            f"DELETE FROM {table_name}",
            f"WHERE {where_clause}"
        ]
        
        if returning:
            query_parts.append(f"RETURNING {returning}")
        
        query = " ".join(query_parts)
        
        # Execute query
        if returning:
            return await self.fetch(query, *(where_params or []))
        else:
            await self.execute(query, *(where_params or []))
            return None
    
    async def table_exists(self, table_name: str, schema: str = "public") -> bool:
        """Check if a table exists"""
        query = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = $1 
                AND table_name = $2
            )
        """
        return await self.fetchval(query, schema, table_name)
    
    async def get_table_columns(
        self,
        table_name: str,
        schema: str = "public"
    ) -> List[Dict[str, Any]]:
        """Get column information for a table"""
        query = """
            SELECT 
                column_name,
                data_type,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_schema = $1
            AND table_name = $2
            ORDER BY ordinal_position
        """
        rows = await self.fetch(query, schema, table_name)
        
        return [
            {
                "name": row["column_name"],
                "type": row["data_type"],
                "nullable": row["is_nullable"] == "YES",
                "default": row["column_default"]
            }
            for row in rows
        ]
    
    async def copy_from_csv(
        self,
        table_name: str,
        file_path: str,
        columns: Optional[List[str]] = None,
        delimiter: str = ",",
        header: bool = True
    ):
        """
        Copy data from CSV file using COPY command.
        
        Args:
            table_name: Target table
            file_path: Path to CSV file
            columns: Column names (if not specified, uses table order)
            delimiter: CSV delimiter
            header: Whether CSV has header row
        """
        async with self.acquire() as connection:
            columns_clause = f"({', '.join(columns)})" if columns else ""
            header_clause = "HEADER" if header else ""
            
            query = f"""
                COPY {table_name} {columns_clause}
                FROM STDIN
                WITH (FORMAT CSV, DELIMITER '{delimiter}', {header_clause})
            """
            
            with open(file_path, 'r') as f:
                await connection.copy_from_query(query, f.read())
            
            logger.info(f"Data copied from {file_path} to {table_name}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform database health check"""
        try:
            # Check connection
            version = await self.fetchval("SELECT version()")
            
            # Check pool status
            pool_status = {
                "size": self.pool.get_size() if self.pool else 0,
                "free_connections": self.pool.get_idle_size() if self.pool else 0,
                "min_size": self.min_pool_size,
                "max_size": self.max_pool_size
            }
            
            return {
                "status": "healthy",
                "version": version,
                "pool": pool_status,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }