# DEAN Environment Variables Documentation

This document provides a comprehensive reference for all environment variables used in the DEAN system.

## Table of Contents
- [Core System Variables](#core-system-variables)
- [Database Configuration](#database-configuration)
- [Redis Configuration](#redis-configuration)
- [Service Endpoints](#service-endpoints)
- [Authentication & Security](#authentication--security)
- [Monitoring & Metrics](#monitoring--metrics)
- [Resource Limits](#resource-limits)
- [Feature Flags](#feature-flags)
- [Email & Alerts](#email--alerts)
- [Distributed Deployment](#distributed-deployment)

## Core System Variables

| Variable | Description | Default | Required | Used By |
|----------|-------------|---------|----------|---------|
| `ENV` | Environment mode | `development` | Yes | All services |
| `LOG_LEVEL` | Logging verbosity | `INFO` | No | All services |
| `DEBUG` | Enable debug mode | `false` | No | All services |
| `API_PORT` | Main API port | `8082` | No | Orchestrator |
| `HOST` | Service host binding | `0.0.0.0` | No | All services |

## Database Configuration

### PostgreSQL

| Variable | Description | Default | Required | Used By |
|----------|-------------|---------|----------|---------|
| `DATABASE_URL` | Full database connection URL | - | No* | All services |
| `POSTGRES_HOST` | PostgreSQL host | `dean-postgres` | Yes** | All services |
| `POSTGRES_PORT` | PostgreSQL port | `5432` | No | All services |
| `POSTGRES_USER` | Database user | `dean_prod` | Yes** | All services |
| `POSTGRES_PASSWORD` | Database password | `postgres` | Yes** | All services |
| `POSTGRES_DB` | Database name | `dean_production` | Yes** | All services |
| `POSTGRES_POOL_SIZE` | Connection pool size | `10` | No | All services |
| `POSTGRES_POOL_MAX_OVERFLOW` | Max overflow connections | `20` | No | All services |
| `POSTGRES_MULTIPLE_DATABASES` | Comma-separated list for dev | - | No | Dev only |

\* DATABASE_URL takes precedence over individual variables
\** Required if DATABASE_URL is not provided

### Important Notes:
- Always use `dean_production` as the database name in production
- The system automatically corrects `dean_prod` to `dean_production` if found
- DATABASE_URL format: `postgresql://user:password@host:port/database`

## Redis Configuration

| Variable | Description | Default | Required | Used By |
|----------|-------------|---------|----------|---------|
| `REDIS_URL` | Full Redis connection URL | - | No* | All services |
| `REDIS_HOST` | Redis host | `dean-redis` | Yes** | All services |
| `REDIS_PORT` | Redis port | `6379` | No | All services |
| `REDIS_PASSWORD` | Redis password | - | No*** | All services |
| `REDIS_MAX_CONNECTIONS` | Connection pool size | `50` | No | All services |

\* REDIS_URL takes precedence over individual variables
\** Required if REDIS_URL is not provided
\*** Required in production

## Service Endpoints

### Internal Services

| Variable | Description | Default | Required | Used By |
|----------|-------------|---------|----------|---------|
| `ORCHESTRATOR_URL` | Orchestrator service URL | `http://dean-orchestrator:8082` | No | Other services |
| `INDEXAGENT_API_URL` | IndexAgent service URL | `http://indexagent:8080` | No | Orchestrator |
| `AIRFLOW_API_URL` | Airflow service URL | `http://airflow-webserver:8080` | No | Orchestrator |
| `EVOLUTION_API_URL` | Evolution service URL | `http://evolution:8084` | No | Orchestrator |
| `AUTH_SERVICE_URL` | Authentication service URL | `http://auth:8085` | No | All services |

### External Services

| Variable | Description | Default | Required | Used By |
|----------|-------------|---------|----------|---------|
| `GITHUB_API_URL` | GitHub API endpoint | `https://api.github.com` | No | IndexAgent |
| `EXTERNAL_API_TIMEOUT` | External API timeout (seconds) | `30` | No | All services |

## Authentication & Security

| Variable | Description | Default | Required | Used By |
|----------|-------------|---------|----------|---------|
| `JWT_SECRET_KEY` | JWT signing key | - | Yes | Auth, Orchestrator |
| `JWT_ALGORITHM` | JWT algorithm | `HS256` | No | Auth service |
| `JWT_EXPIRATION_DELTA` | Token expiry (seconds) | `3600` | No | Auth service |
| `DEAN_API_KEY` | Main API key | - | Yes | External clients |
| `AIRFLOW_USERNAME` | Airflow auth username | `admin` | No | Orchestrator |
| `AIRFLOW_PASSWORD` | Airflow auth password | `admin` | No | Orchestrator |
| `GITHUB_TOKEN` | GitHub API token | - | No | IndexAgent |
| `API_KEYS` | Comma-separated API keys | - | No | Auth service |
| `ENABLE_AUTH` | Enable authentication | `true` | No | All services |
| `SSL_VERIFY` | Verify SSL certificates | `true` | No | All services |

### Security Best Practices:
1. **Never commit secrets to version control**
2. Use strong, unique values for production
3. Rotate keys regularly
4. Use environment-specific secrets management

## Monitoring & Metrics

| Variable | Description | Default | Required | Used By |
|----------|-------------|---------|----------|---------|
| `ENABLE_METRICS` | Enable metrics collection | `true` | No | All services |
| `METRICS_PORT` | Metrics endpoint port | `9090` | No | All services |
| `PROMETHEUS_URL` | Prometheus server URL | `http://prometheus:9090` | No | Monitoring |
| `GRAFANA_URL` | Grafana dashboard URL | `http://grafana:3000` | No | Monitoring |
| `SENTRY_DSN` | Sentry error tracking DSN | - | No | All services |
| `ENABLE_TRACING` | Enable distributed tracing | `false` | No | All services |
| `JAEGER_AGENT_HOST` | Jaeger agent host | `localhost` | No | All services |
| `HEALTH_CHECK_INTERVAL` | Health check interval (seconds) | `30` | No | All services |

## Resource Limits

| Variable | Description | Default | Required | Used By |
|----------|-------------|---------|----------|---------|
| `MAX_WORKERS` | Maximum worker processes | `4` | No | All services |
| `WORKER_TIMEOUT` | Worker timeout (seconds) | `300` | No | All services |
| `MAX_MEMORY_MB` | Memory limit (MB) | `1024` | No | Resource manager |
| `MAX_CPU_PERCENT` | CPU usage limit (%) | `80` | No | Resource manager |
| `TASK_TIMEOUT` | Default task timeout (seconds) | `3600` | No | Orchestrator |
| `MAX_CONCURRENT_TASKS` | Concurrent task limit | `10` | No | Orchestrator |
| `QUEUE_MAX_SIZE` | Task queue size limit | `1000` | No | Orchestrator |

## Feature Flags

| Variable | Description | Default | Required | Used By |
|----------|-------------|---------|----------|---------|
| `ENABLE_EVOLUTION` | Enable evolution features | `true` | No | Orchestrator |
| `ENABLE_DISTRIBUTED` | Enable distributed mode | `false` | No | All services |
| `ENABLE_CACHING` | Enable response caching | `true` | No | All services |
| `ENABLE_WEBSOCKET` | Enable WebSocket support | `true` | No | Orchestrator |
| `USE_MOCK_SERVICES` | Use mock services | `false` | No | Testing |
| `ENABLE_AUTO_SCALING` | Enable auto-scaling | `false` | No | Orchestrator |
| `ENABLE_RATE_LIMITING` | Enable API rate limiting | `true` | No | API services |

## Email & Alerts

| Variable | Description | Default | Required | Used By |
|----------|-------------|---------|----------|---------|
| `SMTP_HOST` | SMTP server host | - | No* | Alert system |
| `SMTP_PORT` | SMTP server port | `587` | No | Alert system |
| `SMTP_USERNAME` | SMTP username | - | No* | Alert system |
| `SMTP_PASSWORD` | SMTP password | - | No* | Alert system |
| `SMTP_USE_TLS` | Use TLS for SMTP | `true` | No | Alert system |
| `ALERT_EMAIL_FROM` | Alert sender email | - | No* | Alert system |
| `ALERT_EMAIL_TO` | Alert recipient emails | - | No* | Alert system |
| `ENABLE_EMAIL_ALERTS` | Enable email alerts | `false` | No | Alert system |

\* Required if email alerts are enabled

## Distributed Deployment

| Variable | Description | Default | Required | Used By |
|----------|-------------|---------|----------|---------|
| `ORCHESTRATOR_HOSTS` | Comma-separated orchestrator hosts | - | No* | Distributed mode |
| `REDIS_SENTINEL_HOSTS` | Redis Sentinel hosts | - | No* | Distributed mode |
| `REDIS_SENTINEL_MASTER` | Redis Sentinel master name | `mymaster` | No | Distributed mode |
| `CLUSTER_NAME` | Cluster identifier | `dean-cluster` | No | Distributed mode |
| `NODE_NAME` | Unique node identifier | hostname | No | Distributed mode |
| `SYNC_INTERVAL` | Cluster sync interval (seconds) | `60` | No | Distributed mode |

\* Required for distributed deployment

## Environment Variable Precedence

1. **Explicit environment variables** (highest priority)
2. **DATABASE_URL / REDIS_URL** (parsed for components)
3. **Configuration files** (YAML, JSON)
4. **Default values** (lowest priority)

## Validation Script

Use the environment validation script to check your configuration:

```bash
python scripts/validate_environment.py
```

This script will:
- Check for required variables
- Validate variable formats
- Test service connectivity
- Report configuration issues

## Best Practices

1. **Use .env files** for local development
2. **Use secrets management** for production (Vault, AWS Secrets Manager, etc.)
3. **Document custom variables** in your deployment
4. **Validate before deployment** using provided scripts
5. **Keep this documentation updated** when adding new variables

## Security Considerations

1. **Sensitive Variables** (never commit to version control):
   - All passwords and secret keys
   - API tokens and credentials
   - Database connection strings
   - SMTP credentials

2. **Production Requirements**:
   - Use strong, unique passwords
   - Enable SSL/TLS where available
   - Rotate credentials regularly
   - Audit access logs

3. **Development vs Production**:
   - Use different credentials for each environment
   - Disable debug mode in production
   - Enable all security features in production
   - Use proper SSL certificates (not self-signed)

## Troubleshooting

Common issues and solutions:

1. **Database connection failures**:
   - Verify POSTGRES_DB is set to `dean_production`
   - Check DATABASE_URL format
   - Ensure all PostgreSQL variables are set

2. **Service discovery failures**:
   - Verify service URLs match Docker service names
   - Check network connectivity
   - Ensure services are healthy

3. **Authentication failures**:
   - Verify JWT_SECRET_KEY is set
   - Check token expiration settings
   - Ensure auth service is running

4. **Missing variables**:
   - Run validation script
   - Check service logs for warnings
   - Review this documentation