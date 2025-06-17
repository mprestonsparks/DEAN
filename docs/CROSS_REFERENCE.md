# DEAN System Cross-Reference Index

**Generated**: 2025-06-16T14:40:00-08:00  
**Version**: 1.0.0

## Overview

This document provides a comprehensive mapping between DEAN system requirements, implementation locations, and test coverage across all components.

## Functional Requirements to Implementation Mapping

| Requirement | Description | Implementation Location | Test Location | Status |
|-------------|-------------|------------------------|---------------|--------|
| FR-001 | Agent Creation | `src/orchestration/coordination/evolution_trial.py` | `tests/unit/orchestration/test_evolution.py` | ✓ |
| FR-002 | Agent Configuration | `src/integration/service_adapters.py` | `tests/unit/test_service_clients.py` | ✓ |
| FR-003 | Agent Lifecycle | `src/orchestration/coordination/unified_server.py` | `tests/integration/test_evolution_workflow.py` | ✓ |
| FR-004 | Evolution Trials | `src/orchestration/coordination/evolution_trial.py` | `tests/integration/test_complete_workflow.py` | ✓ |
| FR-005 | Pattern Discovery | `src/integration/indexagent_client.py` | `tests/unit/integration/test_pattern_discovery.py` | ✓ |
| FR-006 | Token Management | `src/auth/auth_utils.py` | `tests/unit/test_token_management.py` | ✓ |
| FR-007 | Diversity Control | `src/orchestration/coordination/evolution_trial.py` | `tests/unit/orchestration/test_diversity.py` | ✓ |
| FR-008 | Service Integration | `src/integration/base.py` | `tests/integration/test_service_communication.py` | ✓ |
| FR-009 | Monitoring | `src/orchestration/monitoring/__init__.py` | `tests/unit/orchestration/test_monitoring.py` | ✓ |
| FR-010 | API Endpoints | `src/interfaces/web/app.py` | `tests/security/test_api_security.py` | ✓ |

## Non-Functional Requirements to Implementation Mapping

| Requirement | Description | Implementation Location | Verification Method | Status |
|-------------|-------------|------------------------|-------------------|--------|
| NFR-001 | Performance | `src/orchestration/coordination/unified_server.py` | `scripts/performance_test.py` | ✓ |
| NFR-002 | Scalability | `configs/deployment/production_single_machine.yaml` | Load testing | ✓ |
| NFR-003 | Security | `src/auth/auth_middleware.py` | `tests/security/` | ✓ |
| NFR-004 | Reliability | `scripts/deploy/health_check.sh` | Integration tests | ✓ |
| NFR-005 | Maintainability | Code structure and documentation | Code review | ✓ |

## Component Dependencies

### Core Services

#### DEAN Orchestration
**Depends on:**
- IndexAgent API (port 8081)
- Airflow API (port 8080)
- Infrastructure API (port 8090)
- PostgreSQL (port 5432)
- Redis (port 6379)

**Provides:**
- Unified API (port 8082)
- Web Dashboard (port 8093)
- CLI Interface

#### Integration Points
```
DEAN Orchestration
├── IndexAgent Client (src/integration/indexagent_client.py)
│   ├── Pattern discovery API calls
│   ├── Agent worktree management
│   └── Code analysis requests
├── Airflow Client (src/integration/airflow_client.py)
│   ├── DAG triggering
│   ├── Task status monitoring
│   └── Workflow orchestration
└── Infrastructure Client (src/integration/infra_client.py)
    ├── Resource allocation
    ├── Service health checks
    └── Deployment automation
```

### Authentication Flow

1. **Entry Point**: `src/auth/auth_middleware.py`
2. **Token Generation**: `src/auth/auth_utils.py`
3. **User Management**: `src/auth/auth_manager.py`
4. **Model Definitions**: `src/auth/auth_models.py`

### Configuration Loading

1. **Primary Loader**: `src/orchestration/config_loader.py`
2. **Environment Override**: Via os.environ
3. **YAML Parsing**: `configs/` directory
4. **Validation**: On startup in `src/orchestration/coordination/unified_server.py`

## API Endpoint Mapping

| Endpoint | Handler | Integration | Tests |
|----------|---------|-------------|-------|
| `/auth/login` | `auth_manager.login()` | Local auth | `test_authentication.py` |
| `/agents` | `evolution_trial.create_agent()` | IndexAgent | `test_evolution_workflow.py` |
| `/evolution/trials` | `evolution_trial.start_trial()` | All services | `test_complete_workflow.py` |
| `/patterns/discovered` | `indexagent_client.get_patterns()` | IndexAgent | `test_pattern_discovery.py` |
| `/health` | `unified_server.health_check()` | All services | `test_service_communication.py` |

## Database Schema References

### Tables
- `agents`: Agent definitions and state
- `evolution_trials`: Trial history and results
- `patterns`: Discovered code patterns
- `metrics`: Performance and efficiency metrics
- `auth_users`: User authentication data

### Migrations
Located in `migrations/`:
- `20240101000001_initial_schema.sql`: Base schema creation

## Testing Strategy

### Unit Tests
- Location: `tests/unit/`
- Coverage Target: >90%
- Framework: pytest

### Integration Tests
- Location: `tests/integration/`
- Service Stubs: `service_stubs/`
- Full System: `test_full_system.py`

### Security Tests
- Location: `tests/security/`
- API Security: `test_api_security.py`
- Authentication: `test_authentication.py`
- Authorization: `test_authorization.py`

## Deployment Artifacts

### Scripts
- `install.sh`: System installation
- `scripts/deploy/deploy_local.sh`: Local deployment
- `scripts/deploy/deploy_production.sh`: Production deployment
- `scripts/deploy/health_check.sh`: Health verification

### Configuration
- `configs/deployment/local.yaml`: Development settings
- `configs/deployment/production_single_machine.yaml`: Production settings
- `docker-compose.dev.yml`: Development containers

### Documentation
- `docs/DEPLOYMENT_GUIDE.md`: Step-by-step deployment
- `docs/OPERATIONS_RUNBOOK.md`: Operational procedures
- `docs/QUICK_START.md`: Getting started guide

## External Dependencies

### Python Packages
See `requirements/base.txt`:
- FastAPI (web framework)
- SQLAlchemy (ORM)
- Redis (caching)
- httpx (HTTP client)
- pydantic (validation)

### System Requirements
- Python 3.10+
- PostgreSQL 14+
- Redis 6+
- Docker 20+

## Monitoring and Metrics

### Metrics Collection
- Implementation: `src/orchestration/monitoring/`
- Prometheus endpoint: `/metrics`
- Custom metrics: `src/orchestration/coordination/unified_server.py`

### Logging
- Configuration: Via LOG_LEVEL environment variable
- Format: JSON structured logging
- Destinations: stdout, file (optional)

### Alerting
- Health checks: `scripts/deploy/health_check.sh`
- Monitoring script: `scripts/utilities/monitor_system.py`

## Security Considerations

### Authentication
- JWT-based authentication
- Token expiration: 1 hour default
- Refresh tokens supported

### Authorization
- Role-based access control
- Middleware: `src/auth/auth_middleware.py`
- Protected endpoints defined in `src/interfaces/web/app.py`

### Secrets Management
- Environment variables for sensitive data
- No secrets in configuration files
- Vault integration supported

## Maintenance Procedures

### Backup
- Script: `scripts/utilities/backup_restore.sh`
- Includes: Database, configurations
- Schedule: Defined in deployment config

### Updates
- Rolling updates supported
- Rollback: `scripts/deploy/rollback.sh`
- Zero-downtime deployment capable

### Monitoring
- Real-time: `scripts/utilities/monitor_system.py`
- Log analysis: `scripts/utilities/analyze_logs.py`
- Performance: `scripts/performance_test.py`