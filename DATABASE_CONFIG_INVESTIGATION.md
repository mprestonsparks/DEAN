# DATABASE_CONFIG_INVESTIGATION.md

## Investigation Summary
This document captures the investigation into database naming inconsistencies in the DEAN system, where initialization scripts create a database named "dean_production" but the application may attempt to connect to "dean_prod".

## Database Name References Found

### Docker Compose Configurations

#### Production Environment (`docker-compose.prod.yml`)
- **PostgreSQL Container**: `dean-postgres`
- **Database Name**: Uses `${POSTGRES_DB}` environment variable (defaults to `dean_production`)
- **User**: Uses `${POSTGRES_USER}` environment variable (defaults to `dean_prod`)
- **Connection String**: `postgresql://dean_prod:${POSTGRES_PASSWORD}@postgres-prod:5432/dean_production`
- **File Path**: `/Users/preston/Documents/gitRepos/DEAN/docker-compose.prod.yml`

#### Development Environment (`docker-compose.dev.yml`)
- **PostgreSQL Container**: `dean-postgres-dev`
- **Database Names**: Multiple databases - `orchestration`, `indexagent`, `airflow`, `evolution`
- **User**: `dean`
- **File Path**: `/Users/preston/Documents/gitRepos/DEAN/docker-compose.dev.yml`

### Environment Configuration Files

#### Production Template (`.env.production.template`)
```
POSTGRES_USER=dean_prod
POSTGRES_PASSWORD=CHANGE_ME_SECURE_PASSWORD
POSTGRES_DB=dean_production
DATABASE_URL=postgresql://dean_prod:CHANGE_ME_SECURE_PASSWORD@postgres-prod:5432/dean_production
```
- **File Path**: `/Users/preston/Documents/gitRepos/DEAN/.env.production.template`

#### Example Environment (`.env.example`)
```
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=agent_evolution
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
```
- **File Path**: `/Users/preston/Documents/gitRepos/DEAN/.env.example`

### Python Source Code References

#### Test Database Connection Script
- **File**: `/Users/preston/Documents/gitRepos/DEAN/scripts/test_db_connection.py`
- **Default Values**: 
  - `POSTGRES_DB='dean_production'`
  - `POSTGRES_USER='dean_prod'`
- **Purpose**: Tests database connectivity

#### Database Migration Script
- **File**: `/Users/preston/Documents/gitRepos/DEAN/scripts/utilities/db_migrate.py`
- **Default Values**:
  - `POSTGRES_DB='dean_orchestration'`
  - `POSTGRES_USER='postgres'`
- **Purpose**: Database migration utilities

#### Configuration Validation Script
- **File**: `/Users/preston/Documents/gitRepos/DEAN/scripts/validate_config.py`
- **Checks**: Validates presence of `DATABASE_URL` in environment

### SQL Initialization Scripts

#### Schema Creation
- **File**: `/Users/preston/Documents/gitRepos/DEAN/postgres/00-create-schema.sql`
- **References**: 
  - User: `dean_prod`
  - Database: `dean_production`

#### Database Initialization
- **File**: `/Users/preston/Documents/gitRepos/DEAN/postgres/01-init-database.sql`
- **Grants**: Privileges to `dean_prod` user

### Key Findings

1. **No Hardcoded "dean_prod" Database Name Found**: The search did not reveal any Python files with hardcoded references to "dean_prod" as a database name.

2. **Consistent Configuration**: The production configuration consistently uses:
   - Database name: `dean_production`
   - User name: `dean_prod`

3. **Environment Variable Usage**: The application appears to rely on environment variables for database configuration, which is a best practice.

## Root Cause Analysis

### Investigation Results

After thorough investigation, the database configuration appears to be consistent across the codebase:
- **Database Name**: `dean_production` (consistently used)
- **User Name**: `dean_prod` (for authentication)
- **No Hardcoded Mismatches**: No instances of hardcoded "dean_prod" as database name

### Potential Issues

1. **Runtime Environment Variables**: The connection failure might be due to:
   - Missing or incorrectly set environment variables at runtime
   - Application code attempting to use "dean_prod" as database name through dynamic configuration
   - Mismatched environment between initialization and runtime

2. **Application Code**: Need to verify:
   - How the application constructs database connection strings
   - Whether there's dynamic configuration that might use incorrect database name
   - If there are any ORM configurations with hardcoded values

### Recommended Standardized Database Name

Based on the investigation, the canonical database name is already standardized as:
- **Database**: `dean_production`
- **User**: `dean_prod`

This matches the PostgreSQL initialization scripts and environment templates.

## Next Steps

1. Search for any dynamic database configuration in the application code
2. Create a centralized database configuration module to ensure consistency
3. Implement verification scripts to validate configuration at runtime
4. Update any remaining references that might use incorrect database names