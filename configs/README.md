# DEAN Configuration Reference

**Last Updated**: 2025-06-16T14:30:00-08:00  
**Version**: 1.0.0

This directory contains configuration files for the DEAN orchestration system.

## Directory Structure

```
configs/
├── deployment/         # Deployment-specific configurations
│   ├── local.yaml      # Local development settings
│   └── production_single_machine.yaml  # Single-machine production deployment
├── hardware/           # Hardware-specific optimizations
│   └── i7_rtx3080.yaml # Configuration for specific hardware profiles
├── orchestration/      # Core orchestration configurations
│   ├── deployment_config.yaml   # Deployment orchestration settings
│   ├── evolution_config.yaml    # Evolution algorithm parameters
│   └── single_machine.yaml      # Single-machine orchestration
└── services/           # External service configurations
    ├── monitoring_config.yaml   # Monitoring and metrics settings
    └── service_registry.yaml    # Service discovery and endpoints
```

## Configuration Files

### orchestration/evolution_config.yaml
Defines agent evolution parameters and genetic algorithm settings:
- Population size and diversity thresholds
- Mutation rates and crossover strategies
- Fitness evaluation criteria
- Resource allocation constraints

### orchestration/deployment_config.yaml
Controls deployment and service orchestration:
- Service startup sequences
- Health check intervals
- Dependency management
- Rollback strategies

### services/service_registry.yaml
Manages service endpoints and connection settings:
- IndexAgent API endpoints
- Airflow connection parameters
- Infrastructure service URLs
- Authentication credentials (via env vars)

### deployment/local.yaml
Local development environment settings:
- Simplified authentication
- Debug logging levels
- Local service endpoints
- Resource constraints for development

### deployment/production_single_machine.yaml
Production deployment for single-machine installations:
- Security hardening settings
- Production logging configuration
- Performance optimizations
- Backup and recovery settings

## Environment Variables

All sensitive configuration values should be provided via environment variables:

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DEAN_ENV` | Environment (local/staging/production) | local | Yes |
| `DEAN_CONFIG_PATH` | Path to configuration directory | ./configs | No |
| `INDEXAGENT_URL` | IndexAgent API endpoint | http://localhost:8081 | Yes |
| `AIRFLOW_URL` | Airflow API endpoint | http://localhost:8080 | Yes |
| `INFRA_URL` | Infrastructure API endpoint | http://localhost:8090 | Yes |
| `POSTGRES_URL` | PostgreSQL connection string | - | Yes |
| `REDIS_URL` | Redis connection string | - | Yes |
| `AUTH_SECRET_KEY` | JWT signing key | - | Yes |
| `AGENT_TOKEN_LIMIT` | Per-agent token budget | 4096 | No |
| `DEAN_MIN_DIVERSITY` | Minimum population diversity | 0.3 | No |
| `LOG_LEVEL` | Logging level | INFO | No |

## Configuration Loading Order

1. Default values from code
2. Configuration files (YAML)
3. Environment variables (highest priority)

## Validation

All configurations are validated on startup:
- Required fields presence check
- Type validation
- Range and constraint validation
- Service connectivity verification

## Security Considerations

- Never commit sensitive values to configuration files
- Use environment variables for all credentials
- Rotate secrets regularly
- Implement least-privilege access
- Enable audit logging in production

## Configuration Management Best Practices

1. **Version Control**: Track all configuration changes in git
2. **Documentation**: Document all custom settings
3. **Testing**: Test configuration changes in staging first
4. **Backup**: Maintain configuration backups
5. **Monitoring**: Alert on configuration drift

## Examples

### Local Development
```bash
export DEAN_ENV=local
export AUTH_SECRET_KEY=dev-secret
dean serve --config configs/deployment/local.yaml
```

### Production Deployment
```bash
export DEAN_ENV=production
export AUTH_SECRET_KEY=$(vault kv get -field=key secret/dean/auth)
dean serve --config configs/deployment/production_single_machine.yaml
```