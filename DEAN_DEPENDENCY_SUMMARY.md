# DEAN External Service Dependencies - Executive Summary

## Quick Overview

DEAN (Distributed Evolutionary Agent Network) is designed as an orchestration layer that coordinates three external services:

1. **IndexAgent** (http://localhost:8081) - Agent management and code search
2. **Apache Airflow** (http://localhost:8080) - Workflow orchestration
3. **Evolution API** (http://localhost:8083/8084/8090) - Evolution control

## Key Findings

### 1. Service Integration Points

The DEAN codebase has extensive integration with external services through:
- **Client Libraries**: Dedicated client classes for each service in `src/integration/`
- **Service Adapters**: Workflow coordination in `src/integration/service_adapters.py`
- **Unified Server**: REST API proxy endpoints in `src/orchestration/unified_server_simple.py`

### 2. Dependency Locations

| Component | File | External Service Dependencies |
|-----------|------|------------------------------|
| Main Server | `unified_server_simple.py` | IndexAgent (agent creation), Service health checks |
| CLI | `dean_cli.py` | All services for status, evolution, deployment |
| Service Adapters | `service_adapters.py` | Complex workflows using all three services |
| Auth Service Pool | `auth_service_pool.py` | Authenticated clients for all services |

### 3. Configuration Management

Service URLs are configured via environment variables:
```bash
INDEXAGENT_URL=http://localhost:8081
AIRFLOW_URL=http://localhost:8080  
EVOLUTION_API_URL=http://localhost:8084
```

Additional configuration in:
- `configs/services/service_registry.yaml` - Service definitions
- `~/.dean/config.yaml` - User CLI configuration

### 4. Critical Operations Requiring External Services

**Can run without external services:**
- DEAN server startup
- Basic health endpoint
- Prometheus metrics endpoint

**Require external services:**
- Agent creation/management (needs IndexAgent)
- Workflow execution (needs Airflow)
- Evolution trials (needs all three services)
- Service status monitoring
- Pattern discovery and application

### 5. Issues Identified

1. **Port Inconsistency**: Evolution API referenced on ports 8083, 8084, and 8090
2. **Error Handling**: HTTP errors from external services bubble up as 500 errors
3. **No Fallback**: No graceful degradation when services unavailable
4. **Static Configuration**: Service URLs hardcoded with env var overrides

## Impact Analysis

When external services are unavailable:
- DEAN server starts successfully
- Health endpoint reports "healthy" for DEAN itself
- Service status endpoint shows services as "unreachable"
- All functional operations fail with HTTP 500 errors
- CLI commands fail with connection errors

## Recommendations

1. **Implement Mock Mode**: Add capability to run DEAN with mock services for testing/development
2. **Graceful Degradation**: Return meaningful errors when services unavailable
3. **Service Discovery**: Implement dynamic service discovery instead of static URLs
4. **Standardize Ports**: Fix Evolution API port inconsistency
5. **Circuit Breakers**: Add circuit breakers to prevent cascading failures
6. **Offline Capabilities**: Document what DEAN can do without external services