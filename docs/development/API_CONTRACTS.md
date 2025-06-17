# API Contracts

This document defines the exact API contracts that the DEAN orchestration layer expects from each external service. These contracts serve as the specification for both stub implementations and real services.

## IndexAgent API (Port 8081)

### Base URL
```
http://localhost:8081
```

### Authentication
No authentication required (in stubs). Real service may implement API keys.

### Endpoints

#### Health Check
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "indexagent-stub",
  "timestamp": "2024-12-14T10:30:00Z",
  "uptime_seconds": 3600
}
```

#### Agent Management

##### List Agents
```http
GET /agents?limit=100&offset=0
```

**Response:**
```json
{
  "agents": [
    {
      "id": "agent-abc123",
      "name": "search-agent-1",
      "config": {
        "name": "search-agent-1",
        "language": "python",
        "capabilities": ["search", "analyze", "evolve"],
        "parameters": {}
      },
      "fitness_score": 0.75,
      "generation": 0,
      "created_at": "2024-12-14T10:00:00Z",
      "status": "active"
    }
  ],
  "total": 150,
  "limit": 100,
  "offset": 0
}
```

##### Create Agent
```http
POST /agents
Content-Type: application/json

{
  "name": "my-agent",
  "language": "python",
  "capabilities": ["search", "analyze"],
  "parameters": {
    "custom_param": "value"
  }
}
```

**Response:**
```json
{
  "id": "agent-xyz789",
  "name": "my-agent",
  "config": {...},
  "fitness_score": 0.5,
  "generation": 0,
  "created_at": "2024-12-14T10:30:00Z",
  "status": "active"
}
```

##### Get Agent
```http
GET /agents/{agent_id}
```

**Response:** Same as single agent in list response

**Error Response (404):**
```json
{
  "detail": "Agent not found"
}
```

##### Delete Agent
```http
DELETE /agents/{agent_id}
```

**Response:**
```json
{
  "status": "deleted",
  "agent_id": "agent-xyz789"
}
```

#### Evolution Operations

##### Create Population
```http
POST /evolution/population
Content-Type: application/json

{
  "size": 10,
  "mutation_rate": 0.1,
  "crossover_rate": 0.7,
  "selection_method": "tournament"
}
```

**Response:**
```json
{
  "population_id": "pop-abc123",
  "config": {...},
  "agents": [...],
  "generation": 0,
  "best_fitness": 0.7,
  "avg_fitness": 0.5,
  "created_at": "2024-12-14T10:30:00Z"
}
```

##### Evolve Generation
```http
POST /evolution/generation
Content-Type: application/json

{
  "population_id": "pop-abc123"
}
```

**Response:**
```json
{
  "generation": 1,
  "best_agent": {...},
  "population": [...],
  "stats": {
    "best_fitness": 0.85,
    "avg_fitness": 0.65,
    "improvement": 0.15
  }
}
```

##### Get Evolution Metrics
```http
GET /evolution/metrics
```

**Response:**
```json
{
  "total_agents": 150,
  "active_populations": 3,
  "patterns_discovered": 42,
  "average_fitness": 0.72,
  "metrics": {
    "agents_created": 150,
    "patterns_extracted": 42,
    "search_queries": 1250,
    "avg_query_time_ms": 85
  }
}
```

#### Search Operations

##### Code Search
```http
POST /search
Content-Type: application/json

{
  "query": "async handler",
  "repositories": ["repo1", "repo2"],
  "limit": 10,
  "filters": {
    "language": "python",
    "min_score": 0.7
  }
}
```

**Response:**
```json
{
  "query": "async handler",
  "results": [
    {
      "id": "result-123",
      "score": 0.92,
      "repository": "repo1",
      "file_path": "src/handlers/async.py",
      "line_number": 42,
      "snippet": "async def handle_request(...):",
      "context": "Async request handler implementation"
    }
  ],
  "total_results": 25,
  "execution_time_ms": 127
}
```

#### Pattern Management

##### Get Patterns
```http
GET /patterns?pattern_type=optimization&min_confidence=0.7&limit=100
```

**Response:**
```json
{
  "patterns": [
    {
      "id": "pattern-123",
      "type": "optimization",
      "confidence": 0.85,
      "description": "Async operation optimization",
      "occurrences": 25,
      "repositories": ["repo1", "repo2"],
      "created_at": "2024-12-14T10:00:00Z"
    }
  ],
  "total": 42,
  "filters": {
    "pattern_type": "optimization",
    "min_confidence": 0.7
  }
}
```

## Airflow API (Port 8080)

### Base URL
```
http://localhost:8080
```

### Authentication
HTTP Basic Authentication
- Username: `airflow`
- Password: `airflow`

### Endpoints

#### Health Check
```http
GET /health
```

No authentication required.

**Response:**
```json
{
  "status": "healthy",
  "service": "airflow-stub",
  "timestamp": "2024-12-14T10:30:00Z",
  "uptime_seconds": 3600
}
```

#### DAG Management

##### List DAGs
```http
GET /api/v1/dags?limit=100&offset=0&tags=evolution&only_active=true
Authorization: Basic YWlyZmxvdzphaXJmbG93
```

**Response:**
```json
{
  "dags": [
    {
      "dag_id": "evolution_workflow",
      "description": "DEAN Evolution Trial Workflow",
      "file_token": "evolution_workflow.py",
      "fileloc": "/opt/airflow/dags/evolution_workflow.py",
      "is_paused": false,
      "is_active": true,
      "is_subdag": false,
      "owners": ["dean"],
      "schedule_interval": null,
      "tags": ["evolution", "dean"]
    }
  ],
  "total_entries": 3
}
```

##### Get DAG
```http
GET /api/v1/dags/{dag_id}
Authorization: Basic YWlyZmxvdzphaXJmbG93
```

**Response:** Same as single DAG in list

##### Update DAG (Pause/Unpause)
```http
PATCH /api/v1/dags/{dag_id}
Authorization: Basic YWlyZmxvdzphaXJmbG93
Content-Type: application/json

{
  "is_paused": true
}
```

**Response:** Updated DAG object

#### DAG Run Management

##### Trigger DAG Run
```http
POST /api/v1/dags/{dag_id}/dagRuns
Authorization: Basic YWlyZmxvdzphaXJmbG93
Content-Type: application/json

{
  "conf": {
    "repository": "test-repo",
    "trial_id": "trial-123"
  },
  "execution_date": "2024-12-14T10:30:00Z",
  "logical_date": "2024-12-14T10:30:00Z",
  "note": "Triggered by DEAN orchestration"
}
```

**Response:**
```json
{
  "dag_run_id": "manual__2024-12-14T10:30:00.000000__1",
  "dag_id": "evolution_workflow",
  "logical_date": "2024-12-14T10:30:00Z",
  "execution_date": "2024-12-14T10:30:00Z",
  "start_date": "2024-12-14T10:30:00Z",
  "end_date": null,
  "state": "running",
  "external_trigger": true,
  "conf": {...},
  "note": "Triggered by DEAN orchestration"
}
```

**Error Response (409 - DAG is paused):**
```json
{
  "detail": "DAG is paused"
}
```

##### List DAG Runs
```http
GET /api/v1/dags/{dag_id}/dagRuns?limit=100&offset=0&state=running,success
Authorization: Basic YWlyZmxvdzphaXJmbG93
```

**Response:**
```json
{
  "dag_runs": [...],
  "total_entries": 25
}
```

##### Get DAG Run
```http
GET /api/v1/dags/{dag_id}/dagRuns/{dag_run_id}
Authorization: Basic YWlyZmxvdzphaXJmbG93
```

**Response:** Same as single DAG run

#### Task Instance Management

##### List Task Instances
```http
GET /api/v1/dags/{dag_id}/dagRuns/{dag_run_id}/taskInstances
Authorization: Basic YWlyZmxvdzphaXJmbG93
```

**Response:**
```json
{
  "task_instances": [
    {
      "task_id": "initialize_population",
      "dag_id": "evolution_workflow",
      "dag_run_id": "manual__2024-12-14T10:30:00.000000__1",
      "execution_date": "2024-12-14T10:30:00Z",
      "start_date": "2024-12-14T10:30:05Z",
      "end_date": "2024-12-14T10:30:15Z",
      "duration": 10.5,
      "state": "success",
      "try_number": 1,
      "max_tries": 3,
      "operator": "PythonOperator",
      "pool": "default_pool",
      "queue": "default"
    }
  ],
  "total_entries": 4
}
```

## Evolution API (Port 8083)

### Base URL
```
http://localhost:8083
```

### Authentication
No authentication required.

### Endpoints

#### Health Check
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "evolution-stub",
  "timestamp": "2024-12-14T10:30:00Z",
  "uptime_seconds": 3600,
  "active_trials": 2
}
```

#### Evolution Trial Management

##### Start Evolution Trial
```http
POST /evolution/start
Content-Type: application/json

{
  "repository": "my-repo",
  "generations": 10,
  "population_size": 20,
  "mutation_rate": 0.1,
  "crossover_rate": 0.7,
  "fitness_threshold": 0.9,
  "max_runtime_minutes": 30,
  "parameters": {
    "custom_param": "value"
  }
}
```

**Response:**
```json
{
  "trial_id": "trial-abc123",
  "repository": "my-repo",
  "config": {...},
  "status": "initializing",
  "started_at": "2024-12-14T10:30:00Z",
  "completed_at": null,
  "current_generation": 0,
  "best_fitness": 0.0,
  "improvements": [],
  "patterns_discovered": 0,
  "error": null
}
```

##### Get Trial Status
```http
GET /evolution/{trial_id}/status
```

**Response:** Same as start response with updated fields

##### Cancel Trial
```http
POST /evolution/{trial_id}/cancel
```

**Response:**
```json
{
  "status": "cancelled",
  "trial_id": "trial-abc123"
}
```

**Error Response (400 - Cannot cancel):**
```json
{
  "detail": "Trial cannot be cancelled"
}
```

##### List Trials
```http
GET /evolution/trials?repository=my-repo&status=completed&limit=100&offset=0
```

**Response:**
```json
{
  "trials": [...],
  "total": 50,
  "limit": 100,
  "offset": 0
}
```

#### Results and Metrics

##### Get Results
```http
GET /evolution/results?repository=my-repo&min_fitness=0.8&limit=100
```

**Response:**
```json
{
  "results": [
    {
      "trial_id": "trial-abc123",
      "repository": "my-repo",
      "status": "completed",
      "generations_completed": 10,
      "final_fitness": 0.92,
      "total_improvements": 0.42,
      "patterns_discovered": [...],
      "execution_time_seconds": 180.5,
      "metadata": {
        "initial_fitness": 0.5,
        "improvement_rate": 0.042
      }
    }
  ],
  "total": 15
}
```

##### Get Patterns
```http
GET /patterns?pattern_type=optimization&min_confidence=0.7&limit=100
```

**Response:**
```json
{
  "patterns": [
    {
      "id": "pattern-xyz",
      "trial_id": "trial-abc123",
      "name": "Async handler optimization",
      "type": "optimization",
      "description": "Pattern discovered in generation 5",
      "confidence": 0.85,
      "occurrences": 12,
      "impact_score": 0.78,
      "discovered_at": "2024-12-14T10:35:00Z",
      "generation": 5,
      "repositories": ["my-repo"]
    }
  ],
  "total": 25,
  "types": {
    "optimization": 10,
    "refactoring": 8,
    "bug_fix": 5,
    "feature": 2
  }
}
```

##### Get Evolution Metrics
```http
GET /evolution/metrics
```

**Response:**
```json
{
  "total_trials": 150,
  "active_trials": 3,
  "completed_trials": 140,
  "failed_trials": 7,
  "total_patterns": 425,
  "average_fitness": 0.847,
  "average_generations": 8.5,
  "average_patterns_per_trial": 3.2
}
```

#### WebSocket Connection

##### Connect
```
ws://localhost:8083/ws
```

**Connection Message:**
```json
{
  "type": "connection",
  "message": "Connected to Evolution API WebSocket",
  "timestamp": "2024-12-14T10:30:00Z"
}
```

**Trial Update Message:**
```json
{
  "type": "trial_update",
  "trial_id": "trial-abc123",
  "message": "Generation 5 completed",
  "timestamp": "2024-12-14T10:35:00Z",
  "data": {
    "generation": 5,
    "fitness": 0.75,
    "improvement": 0.05
  }
}
```

**Pattern Discovery Message:**
```json
{
  "type": "trial_update",
  "trial_id": "trial-abc123",
  "message": "Pattern discovered in generation 5",
  "timestamp": "2024-12-14T10:35:30Z",
  "data": {
    "pattern": {
      "id": "pattern-xyz",
      "type": "optimization",
      "confidence": 0.85
    }
  }
}
```

## Error Responses

All services use standard HTTP status codes and return errors in this format:

```json
{
  "detail": "Error message here"
}
```

Common status codes:
- `200`: Success
- `201`: Created
- `400`: Bad Request
- `401`: Unauthorized (Airflow only)
- `404`: Not Found
- `409`: Conflict
- `500`: Internal Server Error

## Rate Limiting

Stubs do not implement rate limiting. Real services may enforce:
- 1000 requests per minute per IP
- 100 concurrent connections per service
- WebSocket connections limited to 10 per client

## Versioning

Current API version: v1

Future versions will be available at:
- `/api/v2/...` for breaking changes
- Version negotiation via headers for minor updates

## Notes for Implementation

1. **Consistency**: All timestamp fields use ISO 8601 format
2. **Pagination**: All list endpoints support `limit` and `offset`
3. **Filtering**: Query parameters for filtering are additive (AND logic)
4. **Async Operations**: Long-running operations return immediately with status tracking
5. **WebSocket**: Optional but recommended for real-time updates