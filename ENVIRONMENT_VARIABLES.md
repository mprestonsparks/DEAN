# DEAN Environment Variables Documentation

This document lists all environment variables used throughout the DEAN (Distributed Evolutionary Agent Network) system.

## Docker Compose Environment Variables

### PostgreSQL Configuration
- `POSTGRES_USER` - PostgreSQL username (default: dean/dean_prod)
- `POSTGRES_PASSWORD` - PostgreSQL password 
- `POSTGRES_DB` - PostgreSQL database name (default: dean_production)
- `POSTGRES_HOST` - PostgreSQL host (default: dean-postgres/localhost)
- `POSTGRES_PORT` - PostgreSQL port (default: 5432)
- `POSTGRES_MULTIPLE_DATABASES` - Comma-separated list of databases to create
- `POSTGRES_POOL_SIZE` - Connection pool size (default: 10)
- `POSTGRES_POOL_MAX_OVERFLOW` - Max pool overflow (default: 20)

### Database URL
- `DATABASE_URL` - Full PostgreSQL connection URL (overrides individual settings)

### Redis Configuration
- `REDIS_HOST` - Redis host (default: redis/localhost)
- `REDIS_PORT` - Redis port (default: 6379)
- `REDIS_PASSWORD` - Redis password
- `REDIS_URL` - Full Redis connection URL
- `REDIS_DB` - Redis database number (default: 0)
- `REDIS_POOL_SIZE` - Redis connection pool size (default: 10)

### DEAN Service Configuration
- `DEAN_ENV` - Environment mode (development/production)
- `DEAN_SERVER_HOST` - Orchestration server host (default: 0.0.0.0)
- `DEAN_SERVER_PORT` - Orchestration server port (default: 8082)
- `DEAN_SERVER_WORKERS` - Number of server workers (default: 4)
- `DEAN_SERVER_RELOAD` - Enable auto-reload (default: false)
- `DEAN_LOG_LEVEL` - Log level (default: info)
- `DEAN_DEPLOYMENT_MODE` - Deployment mode (single-machine/distributed)
- `DEAN_SERVICE_API_KEY` - API key for service-to-service authentication
- `DEAN_ORCHESTRATION_URL` - Full orchestration service URL
- `DEAN_USERNAME` - Username for DEAN authentication
- `DEAN_PASSWORD` - Password for DEAN authentication
- `DEAN_API_KEY` - API key for DEAN authentication
- `DEAN_ADMIN_EMAIL` - Admin email address
- `DEAN_API_URL` - Public API URL
- `DEAN_TESTING` - Set to 'true' for testing mode

### Service Endpoints
- `INDEXAGENT_API_URL` - IndexAgent service URL (default: http://localhost:8081)
- `INDEXAGENT_API_TIMEOUT` - IndexAgent request timeout (default: 30)
- `INDEXAGENT_API_KEY` - IndexAgent API key

- `AIRFLOW_API_URL` - Airflow service URL (default: http://localhost:8080)
- `AIRFLOW_USERNAME` - Airflow username (default: airflow)
- `AIRFLOW_PASSWORD` - Airflow password (default: airflow)
- `AIRFLOW_API_KEY` - Airflow API key
- `AIRFLOW_URL` - Alternative Airflow URL configuration

- `EVOLUTION_API_URL` - Evolution service URL (default: http://localhost:8083)
- `EVOLUTION_API_TIMEOUT` - Evolution request timeout (default: 60)
- `EVOLUTION_API_KEY` - Evolution API key

### Monitoring & Metrics
- `PROMETHEUS_URL` - Prometheus URL (default: http://localhost:9090)
- `GRAFANA_URL` - Grafana URL (default: http://localhost:3000)
- `ENABLE_METRICS` - Enable metrics collection (default: true)
- `METRICS_PORT` - Metrics export port (default: 9091)
- `ENABLE_ALERTS` - Enable alerting (default: false)
- `ALERT_WEBHOOK_URL` - Webhook URL for alerts

### Security Configuration
- `JWT_SECRET_KEY` - JWT secret key for token generation
- `JWT_SECRET` - Alternative JWT secret configuration
- `CORS_ORIGINS` - Comma-separated list of allowed CORS origins
- `CORS_ALLOWED_ORIGINS` - Alternative CORS origins configuration

### Service Stub Configuration
- `SERVICE_NAME` - Name of the service stub
- `SERVICE_PORT` - Port for the service stub
- `LOG_LEVEL` - Logging level (INFO/DEBUG/WARNING/ERROR)

### Feature Flags
- `ENABLE_DISTRIBUTED_TRACING` - Enable distributed tracing (default: false)
- `ENABLE_PERFORMANCE_PROFILING` - Enable performance profiling (default: false)
- `ENABLE_DEBUG_MODE` - Enable debug mode (default: false)
- `ENABLE_GPU_ACCELERATION` - Enable GPU acceleration (default: false)
- `ENABLE_PATTERN_DISCOVERY` - Enable pattern discovery (default: true)
- `ENABLE_AUTO_EVOLUTION` - Enable auto evolution (default: true)
- `ENABLE_CACHE` - Enable caching (default: true)
- `ENABLE_BACKUP` - Enable backups (default: false)

### Resource Configuration
- `MAX_WORKERS` - Maximum number of workers (default: 16)
- `MAX_MEMORY_PER_WORKER` - Max memory per worker (default: 2G)
- `UVICORN_WORKERS` - Number of Uvicorn workers (default: 8)
- `DB_POOL_SIZE` - Database pool size (default: 20)
- `MAX_MEMORY_MB` - Maximum memory in MB (default: 4096)
- `MAX_CPU_PERCENT` - Maximum CPU percentage (default: 80)
- `WORKER_POOL_SIZE` - Worker pool size (default: 10)
- `TASK_QUEUE_SIZE` - Task queue size (default: 100)

### Retry & Timeout Configuration
- `MAX_RETRIES` - Maximum number of retries (default: 3)
- `RETRY_DELAY` - Retry delay in seconds (default: 1.0)
- `RETRY_BACKOFF_FACTOR` - Retry backoff factor (default: 2.0)
- `DEFAULT_TIMEOUT` - Default timeout in seconds (default: 30)
- `LONG_RUNNING_TIMEOUT` - Long running task timeout (default: 300)

### Cache Configuration
- `CACHE_TTL` - Cache TTL in seconds (default: 3600)

### Health Check Configuration
- `HEALTH_CHECK_INTERVAL` - Health check interval in seconds (default: 30)
- `HEALTH_CHECK_TIMEOUT` - Health check timeout in seconds (default: 10)

### File Storage
- `STORAGE_PATH` - File storage path (default: /tmp/dean-orchestration)
- `MAX_UPLOAD_SIZE_MB` - Maximum upload size in MB (default: 100)

### Email Configuration (for alerts)
- `SMTP_HOST` - SMTP server host
- `SMTP_PORT` - SMTP server port (default: 587)
- `SMTP_USER` - SMTP username
- `SMTP_PASSWORD` - SMTP password
- `ALERT_EMAIL_FROM` - Alert sender email
- `ALERT_EMAIL_TO` - Alert recipient email

### Distributed Deployment Settings
- `SERVICE_DISCOVERY_METHOD` - Service discovery method (default: dns)
- `SERVICE_REGISTRY_URL` - Service registry URL
- `CLUSTER_NAME` - Cluster name (default: dean-production)
- `NODE_NAME` - Node name (default: orchestrator-1)
- `MESSAGE_QUEUE_TYPE` - Message queue type (default: redis)
- `MESSAGE_QUEUE_URL` - Message queue URL (default: redis://localhost:6379/1)

### Backup Configuration
- `BACKUP_SCHEDULE` - Backup schedule cron expression (default: 0 2 * * *)
- `BACKUP_RETENTION_DAYS` - Backup retention in days (default: 7)
- `BACKUP_PATH` - Backup storage path (default: /backup/dean-orchestration)

### Custom Configuration
- `CUSTOM_CONFIG_PATH` - Path to custom configuration file

### Testing Environment
- `USE_MOCK_SERVICES` - Use mock services for testing (default: false in production)

### Production Specific
- `ENV` - Environment type (production/development)
- `GF_SECURITY_ADMIN_PASSWORD` - Grafana admin password
- `GF_USERS_ALLOW_SIGN_UP` - Allow Grafana user signup (default: false)

## Usage Notes

1. **Docker Compose**: Environment variables in docker-compose files can be overridden by creating a `.env` file in the same directory.

2. **Production**: Copy `.env.production.template` to `.env` and update with secure values before deployment.

3. **Development**: The `.env.example` file provides a complete set of development defaults.

4. **Security**: Never commit `.env` files with real credentials to version control.

5. **Precedence**: Environment variables typically follow this precedence:
   - Command line overrides
   - `.env` file values
   - Docker Compose environment sections
   - Default values in code

## Script Usage

### Shell Scripts (.sh)
- Scripts source environment variables using `export` commands
- Many scripts check for `.env` file and source it if present
- Critical scripts validate required environment variables before proceeding

### PowerShell Scripts (.ps1)
- Use `$env:VARIABLE_NAME` syntax for environment variables
- Scripts typically validate configuration before execution

### Python Code
- Uses `os.getenv()` with default values
- Database configuration uses `DATABASE_URL` with fallback to individual components
- Authentication checks for JWT_SECRET_KEY with development default