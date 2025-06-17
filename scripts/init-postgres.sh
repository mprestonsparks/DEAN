#!/bin/bash
set -e

# Create multiple databases for development
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE orchestration;
    CREATE DATABASE indexagent;
    CREATE DATABASE airflow;
    CREATE DATABASE evolution;
    GRANT ALL PRIVILEGES ON DATABASE orchestration TO $POSTGRES_USER;
    GRANT ALL PRIVILEGES ON DATABASE indexagent TO $POSTGRES_USER;
    GRANT ALL PRIVILEGES ON DATABASE airflow TO $POSTGRES_USER;
    GRANT ALL PRIVILEGES ON DATABASE evolution TO $POSTGRES_USER;
EOSQL