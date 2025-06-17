# DEAN External Service Interfaces

**Version**: 1.0.0  
**Last Updated**: June 13, 2025  
**Source**: Based on analysis of dean-agent-workspace documentation

## Overview

This document specifies the external service interfaces that the DEAN orchestration layer integrates with. These interfaces are provided by the IndexAgent, airflow-hub, and infra repositories.

## IndexAgent API (Port 8081)

### Base Configuration
- **Base URL**: `http://localhost:8081`
- **Protocol**: HTTP/1.1
- **Content Type**: `application/json`

### Endpoints Used by Orchestration

#### Agent Management

**GET /agents**  
Lists all agents in the system.

**POST /agents**  
Creates a new agent with specified configuration.

**GET /agents/{agent_id}**  
Retrieves details for a specific agent.

**DELETE /agents/{agent_id}**  
Removes an agent from the system.

#### Evolution Operations

**POST /evolution/population**  
Initializes a new agent population.

**GET /evolution/metrics**  
Retrieves evolution metrics and performance data.

**POST /evolution/generation**  
Triggers a new generation in the evolution process.

#### Code Search

**POST /search**  
Searches code repositories using Zoekt backend.

**GET /search/index/status**  
Returns the status of code indexing operations.

### Expected Response Formats

Based on existing implementations in dean-agent-workspace, responses follow this structure:
```json
{
  "success": true,
  "data": {},
  "timestamp": "2025-06-13T10:00:00Z"
}
```

## Airflow API (Port 8080)

### Base Configuration
- **Base URL**: `http://localhost:8080`
- **Protocol**: HTTP/1.1
- **Authentication**: Basic Auth (username/password)
- **API Version**: `/api/v1`

### Endpoints Used by Orchestration

#### DAG Management

**GET /api/v1/dags**  
Lists all available DAGs.

**GET /api/v1/dags/{dag_id}**  
Retrieves details for a specific DAG.

**PATCH /api/v1/dags/{dag_id}**  
Updates DAG properties (pause/unpause).

#### DAG Execution

**POST /api/v1/dags/{dag_id}/dagRuns**  
Triggers a new DAG run.
```json
{
  "conf": {},
  "dag_run_id": "manual__2025-06-13T10:00:00",
  "execution_date": "2025-06-13T10:00:00"
}
```

**GET /api/v1/dags/{dag_id}/dagRuns/{dag_run_id}**  
Retrieves status of a DAG run.

#### Task Information

**GET /api/v1/dags/{dag_id}/tasks**  
Lists all tasks in a DAG.

**GET /api/v1/dags/{dag_id}/dagRuns/{dag_run_id}/taskInstances**  
Retrieves task instance details for a DAG run.

### Authentication

Airflow uses Basic Authentication:
```
Authorization: Basic base64(username:password)
```

## Evolution API (Port 8090)

### Base Configuration
- **Base URL**: `http://localhost:8090`
- **Protocol**: HTTP/1.1
- **Content Type**: `application/json`

### Endpoints Used by Orchestration

#### Evolution Control

**POST /evolution/start**  
Starts a new evolution cycle.
```json
{
  "population_size": 50,
  "generations": 10,
  "mutation_rate": 0.1
}
```

**GET /evolution/status**  
Returns current evolution status.

**POST /evolution/stop**  
Stops the current evolution cycle.

#### Meta-Learning

**GET /patterns**  
Retrieves discovered patterns.

**POST /patterns/apply**  
Applies patterns to agent population.

#### Metrics

**GET /metrics**  
Returns evolution metrics in Prometheus format.

## Infrastructure Services

### PostgreSQL (Port 5432)

**Database**: `agent_evolution`

**Schemas Used**:
- `agent_evolution` - Evolution history and metrics
- `public` - Shared configuration

**Tables Accessed** (from DATABASE_SPECIFICATION_MAPPING.md):
- `agents` - Agent definitions and lineage
- `performance_metrics` - Performance tracking
- `evolution_history` - Evolution trial history
- `patterns` - Discovered patterns

**Connection Configuration**:
```python
{
    "host": "localhost",
    "port": 5432,
    "database": "agent_evolution",
    "user": "postgres",
    "password": "postgres"
}
```

### Redis (Port 6379)

**Purpose**: Agent registry and pattern caching

**Key Patterns**:
- `agent:{agent_id}` - Agent state
- `pattern:{pattern_id}` - Pattern definitions
- `metrics:{metric_type}:{timestamp}` - Time-series metrics

**Connection Configuration**:
```python
{
    "host": "localhost",
    "port": 6379,
    "db": 0
}
```

## Monitoring Services

### Prometheus (Port 9090)

**Metrics Endpoint**: `/metrics`

**Scraped Metrics**:
- Evolution performance metrics
- Service health metrics
- Resource utilization

### Grafana (Port 3000)

**Dashboard Access**: Web UI for visualization

**Integration**: Queries Prometheus for metrics

## Service Discovery

**Note**: Policy for service discovery in distributed deployments has not been defined and requires stakeholder input.

Currently, all services use static configuration with localhost endpoints.

## Error Handling

All services are expected to return errors in a consistent format:
```json
{
  "error": {
    "message": "Descriptive error message",
    "code": "ERROR_CODE",
    "details": {}
  }
}
```

## Retry Policies

The orchestration layer implements:
- Exponential backoff for transient failures
- Maximum of 3 retries by default
- Circuit breaker pattern for persistent failures

**Note**: Specific retry policies per service have not been defined and require stakeholder input.

## Performance Expectations

Based on existing system documentation:
- IndexAgent API: < 100ms response time
- Airflow API: < 500ms for DAG triggers
- Evolution API: < 1s for generation processing
- Database queries: < 50ms for standard queries

## Security Considerations

**Note**: The following security aspects have not been defined and require stakeholder input:
- Service-to-service authentication methods
- API key management
- Certificate validation for HTTPS
- Network isolation requirements

## Versioning

Current versions based on dean-agent-workspace:
- IndexAgent: No versioning (assumed v1)
- Airflow: API v1
- Evolution API: No versioning (assumed v1)

**Note**: Version compatibility matrix has not been defined and requires stakeholder input.

## Health Checks

All services are expected to provide health endpoints:
- IndexAgent: `/health`
- Airflow: `/api/v1/health`
- Evolution API: `/health`

Health check format:
```json
{
  "status": "healthy|unhealthy",
  "checks": {
    "database": "ok",
    "redis": "ok"
  }
}
```