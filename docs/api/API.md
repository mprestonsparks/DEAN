# DEAN API Reference

**Version**: 1.0.0  
**Base URL**: http://localhost:8082/api/v1  
**Last Updated**: 2025-06-16T14:35:00-08:00

## Overview

The DEAN Orchestration API provides RESTful endpoints for managing the Distributed Evolutionary Agent Network system. All endpoints require authentication unless otherwise specified.

## Authentication

All API requests require a Bearer token in the Authorization header:

```
Authorization: Bearer <token>
```

Obtain a token via the `/auth/login` endpoint.

## Endpoints

### Authentication

#### POST /auth/login
Authenticate and receive access tokens.

**Request Body:**
```json
{
  "username": "string",
  "password": "string"
}
```

**Response:**
```json
{
  "access_token": "string",
  "refresh_token": "string",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### Agent Management

#### POST /agents
Create a new evolutionary agent.

**Request Body:**
```json
{
  "name": "string",
  "type": "code_optimizer|pattern_extractor|security_analyzer",
  "config": {
    "token_limit": 4096,
    "temperature": 0.7,
    "optimization_target": "performance|readability|security"
  }
}
```

**Response:**
```json
{
  "id": "uuid",
  "name": "string",
  "type": "string",
  "status": "active",
  "created_at": "2025-06-16T14:00:00Z",
  "token_usage": {
    "used": 0,
    "limit": 4096
  }
}
```

#### GET /agents/{id}
Retrieve agent details.

**Response:**
```json
{
  "id": "uuid",
  "name": "string",
  "type": "string",
  "status": "active|idle|evolving",
  "fitness_score": 0.85,
  "generation": 5,
  "token_usage": {
    "used": 2048,
    "limit": 4096
  },
  "metrics": {
    "patterns_discovered": 12,
    "code_improvements": 8,
    "efficiency_score": 0.92
  }
}
```

#### POST /agents/{id}/evolve
Trigger agent evolution.

**Request Body:**
```json
{
  "mutation_rate": 0.1,
  "selection_pressure": 0.8,
  "target_fitness": 0.95
}
```

**Response:**
```json
{
  "evolution_id": "uuid",
  "status": "started",
  "estimated_duration": 300,
  "parent_generation": 5
}
```

### Evolution Trials

#### POST /evolution/trials
Start a new evolution trial.

**Request Body:**
```json
{
  "name": "string",
  "population_size": 20,
  "max_generations": 100,
  "diversity_threshold": 0.3,
  "target_metrics": {
    "code_quality": 0.9,
    "performance": 0.85,
    "maintainability": 0.88
  }
}
```

**Response:**
```json
{
  "trial_id": "uuid",
  "status": "running",
  "start_time": "2025-06-16T14:00:00Z",
  "current_generation": 0,
  "population_diversity": 1.0
}
```

#### GET /evolution/trials/{id}/status
Get evolution trial status.

**Response:**
```json
{
  "trial_id": "uuid",
  "status": "running|completed|failed",
  "current_generation": 42,
  "best_fitness": 0.89,
  "population_diversity": 0.45,
  "estimated_completion": "2025-06-16T15:00:00Z",
  "metrics": {
    "total_mutations": 840,
    "successful_mutations": 126,
    "patterns_discovered": 23
  }
}
```

### Pattern Management

#### GET /patterns/discovered
List discovered code patterns.

**Query Parameters:**
- `type`: Pattern type filter (optimization|security|refactoring)
- `min_confidence`: Minimum confidence score (0.0-1.0)
- `limit`: Number of results (default: 20)
- `offset`: Pagination offset

**Response:**
```json
{
  "patterns": [
    {
      "id": "uuid",
      "type": "optimization",
      "name": "Loop Vectorization Opportunity",
      "description": "Identified vectorizable loops in numerical computations",
      "confidence": 0.92,
      "impact": "high",
      "occurrences": 15,
      "first_discovered": "2025-06-16T12:00:00Z",
      "example_code": "string"
    }
  ],
  "total": 145,
  "offset": 0,
  "limit": 20
}
```

#### POST /patterns/classify
Classify a code pattern.

**Request Body:**
```json
{
  "code_snippet": "string",
  "context": {
    "language": "python",
    "file_type": "module",
    "performance_critical": true
  }
}
```

**Response:**
```json
{
  "classification": {
    "primary_type": "optimization",
    "subtypes": ["loop_optimization", "memory_efficiency"],
    "confidence": 0.87,
    "recommendations": [
      {
        "action": "vectorize_loop",
        "impact": "high",
        "description": "Convert to NumPy vectorized operations"
      }
    ]
  }
}
```

### Economic Metrics

#### GET /metrics/efficiency
Get system efficiency metrics.

**Response:**
```json
{
  "overall_efficiency": 0.82,
  "token_utilization": 0.75,
  "pattern_discovery_rate": 2.3,
  "code_improvement_rate": 1.8,
  "resource_usage": {
    "cpu_percent": 45.2,
    "memory_mb": 2048,
    "active_agents": 15
  },
  "economic_metrics": {
    "token_roi": 3.2,
    "cost_per_improvement": 125.5,
    "efficiency_trend": "improving"
  }
}
```

#### GET /budget/status
Check token budget status.

**Response:**
```json
{
  "total_budget": 1000000,
  "used": 450000,
  "remaining": 550000,
  "burn_rate": 1250,
  "estimated_depletion": "2025-06-20T14:00:00Z",
  "allocations": {
    "code_optimization": 200000,
    "pattern_extraction": 150000,
    "security_analysis": 100000
  }
}
```

### System Health

#### GET /health
Basic health check.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime": 86400
}
```

#### GET /health/detailed
Detailed system health.

**Response:**
```json
{
  "overall_status": "healthy",
  "components": {
    "orchestration": {
      "status": "healthy",
      "latency_ms": 12
    },
    "indexagent": {
      "status": "healthy",
      "latency_ms": 45,
      "endpoint": "http://indexagent:8081"
    },
    "airflow": {
      "status": "healthy",
      "latency_ms": 67,
      "endpoint": "http://airflow:8080"
    },
    "database": {
      "status": "healthy",
      "connections": 15,
      "latency_ms": 3
    },
    "redis": {
      "status": "healthy",
      "memory_used_mb": 128,
      "latency_ms": 1
    }
  },
  "metrics": {
    "request_rate": 125.3,
    "error_rate": 0.002,
    "avg_response_time_ms": 145
  }
}
```

## Error Responses

All endpoints follow a consistent error response format:

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Agent with ID 'xyz' not found",
    "details": {
      "resource_type": "agent",
      "resource_id": "xyz"
    },
    "timestamp": "2025-06-16T14:00:00Z",
    "request_id": "req_123456"
  }
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `UNAUTHORIZED` | 401 | Missing or invalid authentication |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `RESOURCE_NOT_FOUND` | 404 | Requested resource not found |
| `VALIDATION_ERROR` | 400 | Invalid request parameters |
| `RATE_LIMITED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Internal server error |

## Rate Limiting

API requests are rate-limited to ensure fair usage:

- **Default limit**: 1000 requests per hour
- **Burst limit**: 100 requests per minute
- **Evolution endpoints**: 10 requests per hour

Rate limit headers are included in all responses:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 950
X-RateLimit-Reset: 1629648000
```

## Webhooks

Configure webhooks to receive real-time updates:

```json
{
  "url": "https://your-server.com/webhook",
  "events": ["agent.evolved", "pattern.discovered", "trial.completed"],
  "secret": "your-webhook-secret"
}
```

## SDK Examples

### Python
```python
from dean_client import DEANClient

client = DEANClient(
    base_url="http://localhost:8082",
    api_key="your-api-key"
)

# Create agent
agent = client.agents.create(
    name="OptimizationAgent",
    type="code_optimizer",
    config={"token_limit": 4096}
)

# Start evolution
evolution = client.evolution.start_trial(
    population_size=20,
    max_generations=100
)
```

### JavaScript
```javascript
const { DEANClient } = require('@dean/client');

const client = new DEANClient({
  baseURL: 'http://localhost:8082',
  apiKey: 'your-api-key'
});

// Get agent status
const agent = await client.agents.get('agent-id');

// List patterns
const patterns = await client.patterns.list({
  type: 'optimization',
  minConfidence: 0.8
});
```

## Additional Resources

- [OpenAPI Specification](./openapi.yaml)
- [API Examples](./API_EXAMPLES.md)
- [Integration Guide](../development/API_CONTRACTS.md)
- [Authentication Guide](../security/SECURITY_GUIDE.md)