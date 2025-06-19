# DEAN External Service Dependencies

This document comprehensively lists all external service dependencies in the DEAN codebase and their usage.

## Overview

DEAN orchestrates and depends on three primary external services:
1. **IndexAgent** (Port 8081) - Code search, agent management, and evolution operations
2. **Apache Airflow** (Port 8080) - Workflow orchestration and DAG execution
3. **Evolution API** (Port 8083/8084/8090) - Evolution control and meta-learning

## Service Endpoints

### Environment Variables
```bash
# Primary service URLs
INDEXAGENT_URL=http://localhost:8081
INDEXAGENT_API_URL=http://localhost:8081  # Alternative naming
AIRFLOW_URL=http://localhost:8080
AIRFLOW_API_URL=http://localhost:8080      # Alternative naming
EVOLUTION_API_URL=http://localhost:8084    # Note: Multiple ports referenced (8083, 8084, 8090)

# Authentication
INDEXAGENT_API_KEY=<token>
AIRFLOW_USERNAME=airflow
AIRFLOW_PASSWORD=airflow
EVOLUTION_API_KEY=<token>
VAULT_TOKEN=<token>
```

## Service Dependencies by Component

### 1. IndexAgent Dependencies (Port 8081)

**Client Implementation**: `src/integration/indexagent_client.py`

#### API Endpoints Used:
- **Health Check**: `GET /health`
- **Agent Management**:
  - `GET /agents` - List agents with filtering
  - `POST /agents` - Create new agent
  - `GET /agents/{agent_id}` - Get agent details
  - `PATCH /agents/{agent_id}` - Update agent
  - `DELETE /agents/{agent_id}` - Delete agent
  - `GET /agents/{agent_id}/lineage` - Get agent lineage
- **Evolution Operations**:
  - `POST /evolution/population` - Initialize population
  - `POST /evolution/generation` - Trigger generation
  - `GET /evolution/metrics` - Get evolution metrics
- **Code Search**:
  - `POST /search` - Search code repositories
  - `GET /search/index/status` - Get indexing status
  - `POST /search/index/trigger` - Trigger reindexing
- **Pattern Management**:
  - `GET /patterns` - Get discovered patterns
  - `POST /patterns/apply` - Apply patterns to agents

#### Used By:
- `unified_server_simple.py`: Agent creation endpoint
- Service adapters for evolution workflows
- CLI commands for agent management

### 2. Apache Airflow Dependencies (Port 8080)

**Client Implementation**: `src/integration/airflow_client.py`

#### API Endpoints Used:
- **Health Check**: `GET /api/v1/health`
- **DAG Management**:
  - `GET /api/v1/dags` - List DAGs
  - `GET /api/v1/dags/{dag_id}` - Get DAG details
  - `PATCH /api/v1/dags/{dag_id}` - Update DAG (pause/unpause)
  - `GET /api/v1/dags/{dag_id}/source` - Get DAG source code
- **DAG Execution**:
  - `POST /api/v1/dags/{dag_id}/dagRuns` - Trigger DAG run
  - `GET /api/v1/dags/{dag_id}/dagRuns/{dag_run_id}` - Get run status
  - `GET /api/v1/dags/{dag_id}/dagRuns` - List DAG runs
  - `PATCH /api/v1/dags/{dag_id}/dagRuns/{dag_run_id}` - Cancel run
- **Task Information**:
  - `GET /api/v1/dags/{dag_id}/tasks` - List tasks
  - `GET /api/v1/dags/{dag_id}/tasks/{task_id}` - Get task details
  - `GET /api/v1/dags/{dag_id}/dagRuns/{dag_run_id}/taskInstances` - Get task instances
  - `GET /api/v1/dags/{dag_id}/dagRuns/{dag_run_id}/taskInstances/{task_id}` - Get specific task instance

#### Authentication:
- Uses Basic Authentication with username/password
- Default credentials: airflow/airflow

#### Used By:
- Evolution workflow coordination
- Task orchestration in service adapters
- Status monitoring

### 3. Evolution API Dependencies (Port 8083/8084/8090)

**Client Implementation**: `src/integration/infra_client.py`

#### API Endpoints Used:
- **Health Check**: `GET /health`
- **Evolution Control**:
  - `POST /evolution/start` - Start evolution cycle
  - `GET /evolution/status` - Get evolution status
  - `POST /evolution/stop` - Stop evolution
  - `POST /evolution/pause` - Pause evolution
  - `POST /evolution/resume` - Resume evolution
- **Pattern Management**:
  - `GET /patterns` - Get patterns with filtering
  - `POST /patterns/apply` - Apply patterns to population
- **Meta-Learning**:
  - `POST /metalearning/extract` - Extract strategies
  - `GET /metrics` - Get Prometheus metrics
- **Trial Management**:
  - `GET /trials/{trial_id}/history` - Get trial history
  - `GET /trials/{trial_id}/analysis` - Analyze performance

#### Port Confusion:
- Configuration references port 8083
- Code references port 8090 (default in client)
- unified_server_simple.py uses port 8084
- This inconsistency needs resolution

#### Used By:
- Evolution trial coordination
- Pattern extraction workflows
- CLI evolution commands

## Infrastructure Services

### 4. PostgreSQL (Port 5432)
- **Databases**:
  - `airflow` - Airflow metadata
  - `indexagent` - IndexAgent data
  - `market_analysis` - Market analysis data
  - `agent_evolution` - Evolution metrics and patterns
- **Connection pooling**: 2-10 connections per service

### 5. Redis (Port 6379)
- **Database 0**: General cache
- **Database 1**: Pub/sub messaging
- **Database 2**: Agent registry
- **Database 3**: Pattern store

### 6. HashiCorp Vault (Port 8200)
- **Namespace**: `dean`
- **Usage**: Secure credential storage
- **Authentication**: Token-based

## Service Interaction Patterns

### 1. Evolution Workflow
```
DEAN → IndexAgent: Initialize population
DEAN → Evolution API: Start evolution
DEAN → Airflow: Trigger evolution DAG
DEAN → Evolution API: Monitor status
DEAN → IndexAgent: Apply discovered patterns
```

### 2. Agent Creation
```
User → DEAN: Create agent request
DEAN → IndexAgent: POST /api/v1/agents
IndexAgent → DEAN: Agent details
DEAN → User: Success response
```

### 3. Service Health Monitoring
```
DEAN → All Services: GET /health
Services → DEAN: Health status
DEAN → User: Aggregated status
```

## Critical Dependencies

1. **DEAN Server Start**: Can start without external services but functionality limited
2. **Agent Operations**: Require IndexAgent to be running
3. **Workflow Execution**: Requires Airflow to be operational
4. **Evolution Trials**: Require all three services (IndexAgent, Airflow, Evolution API)

## Error Handling

- **Connection Failures**: Captured and reported via health endpoints
- **Timeout Settings**: 
  - IndexAgent: 30 seconds
  - Airflow: 60 seconds
  - Evolution API: 120 seconds
- **Retry Policy**: 3 retries with exponential backoff

## Configuration Files

- `configs/services/service_registry.yaml` - Central service configuration
- `configs/orchestration/deployment_config.yaml` - Deployment settings
- `~/.dean/config.yaml` - User-specific CLI configuration

## Known Issues

1. **Port Inconsistency**: Evolution API port varies between 8083, 8084, and 8090
2. **Service Discovery**: Currently static, plans for Consul/Kubernetes integration
3. **Authentication**: Mixed approaches (bearer tokens, basic auth)

## Recommendations

1. **Standardize Evolution API Port**: Choose single port and update all references
2. **Implement Service Discovery**: Move from static URLs to dynamic discovery
3. **Unified Authentication**: Implement consistent auth across all services
4. **Health Check Standardization**: Ensure all services implement consistent health endpoints
5. **Circuit Breaker Implementation**: Add circuit breakers for service calls
6. **Monitoring Integration**: Implement Prometheus metrics collection

## Testing External Dependencies

To test DEAN with mock services:
```bash
# Start mock services (needs implementation)
dean-cli test services --mock

# Verify service connectivity
dean-cli service health

# Run integration tests
pytest tests/integration/
```