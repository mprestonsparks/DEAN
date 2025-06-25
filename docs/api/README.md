# DEAN System API Reference

## Overview

The DEAN (Distributed Evolutionary Agent Network) system exposes its functionality through three main REST APIs. Each service has its own OpenAPI specification that can be used to generate client libraries, documentation, and interactive API explorers.

## API Services

### 1. DEAN Orchestrator API
- **Port**: 8082
- **Purpose**: Central orchestration, authentication, and system coordination
- **Specification**: [dean-orchestrator-openapi.yaml](./dean-orchestrator-openapi.yaml)
- **Base URL**: `http://localhost:8082/api/v1`

**Key Endpoints**:
- `/agents` - Agent management
- `/evolution` - Evolution cycle control
- `/patterns` - Pattern discovery and propagation
- `/workflows` - Airflow integration
- `/metrics` - System metrics

### 2. IndexAgent API
- **Port**: 8081
- **Purpose**: Core agent logic, evolution algorithms, and pattern detection
- **Specification**: [indexagent-openapi.yaml](./indexagent-openapi.yaml)
- **Base URL**: `http://localhost:8081/api/v1`

**Key Endpoints**:
- `/agents` - Direct agent operations
- `/evolution/genetic-algorithm` - Genetic algorithm operations
- `/evolution/cellular-automata` - Cellular automata rules
- `/patterns/detect` - Pattern detection
- `/diversity` - Population diversity management

### 3. Evolution API (Economic Governor)
- **Port**: 8090/8091
- **Purpose**: Token economy management and evolution constraints
- **Specification**: [evolution-api-openapi.yaml](./evolution-api-openapi.yaml)
- **Base URL**: `http://localhost:8090/api/v1`

**Key Endpoints**:
- `/economy/budget` - Global budget management
- `/economy/allocate` - Token allocation
- `/evolution/constraints` - Evolution constraints
- `/governance/rules` - Economic governance
- `/patterns` - Pattern effectiveness tracking

## Authentication

All APIs (except health endpoints) require JWT authentication:

```bash
curl -X GET http://localhost:8082/api/v1/agents \
  -H "Authorization: Bearer <your-jwt-token>"
```

To obtain a JWT token, use the DEAN Orchestrator authentication endpoint:

```bash
curl -X POST http://localhost:8082/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "your-username",
    "password": "your-password"
  }'
```

## Using the OpenAPI Specifications

### Interactive Documentation (Swagger UI)

Each service can expose Swagger UI for interactive API documentation:

1. **DEAN Orchestrator**: http://localhost:8082/docs
2. **IndexAgent**: http://localhost:8081/docs
3. **Evolution API**: http://localhost:8090/docs

### Generate Client Libraries

Use OpenAPI Generator to create client libraries in your preferred language:

```bash
# Generate Python client for DEAN Orchestrator
openapi-generator generate \
  -i dean-orchestrator-openapi.yaml \
  -g python \
  -o dean-orchestrator-python-client

# Generate JavaScript client for IndexAgent
openapi-generator generate \
  -i indexagent-openapi.yaml \
  -g javascript \
  -o indexagent-js-client
```

### Import to Postman

1. Open Postman
2. Click "Import" → "File"
3. Select the desired OpenAPI YAML file
4. Postman will create a collection with all endpoints

## Common Workflows

### 1. Create and Evolve Agents

```bash
# Step 1: Create agent population (via DEAN Orchestrator)
curl -X POST http://localhost:8082/api/v1/agents/spawn \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "genome_template": "default",
    "population_size": 5,
    "token_budget": 10000
  }'

# Step 2: Start evolution cycle
curl -X POST http://localhost:8082/api/v1/evolution/start \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "population_ids": ["agent_001", "agent_002"],
    "generations": 10,
    "token_budget": 5000
  }'

# Step 3: Monitor evolution status
curl -X GET http://localhost:8082/api/v1/evolution/{cycle_id}/status \
  -H "Authorization: Bearer $TOKEN"
```

### 2. Pattern Discovery and Propagation

```bash
# Detect patterns in agent behavior
curl -X POST http://localhost:8081/api/v1/patterns/detect \
  -H "Content-Type: application/json" \
  -d '{
    "agent_ids": ["agent_001", "agent_002"],
    "detection_depth": 5
  }'

# Propagate successful pattern
curl -X POST http://localhost:8082/api/v1/patterns/{pattern_id}/propagate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "target_agents": ["agent_003", "agent_004"]
  }'
```

### 3. Token Economy Management

```bash
# Check global budget
curl -X GET http://localhost:8090/api/v1/economy/budget

# Allocate tokens to agent
curl -X POST http://localhost:8090/api/v1/economy/allocate \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "agent_001",
    "requested_tokens": 1000,
    "priority": "high"
  }'

# Get efficiency metrics
curl -X GET http://localhost:8090/api/v1/economy/efficiency
```

## Error Handling

All APIs follow consistent error response format:

```json
{
  "error": "ErrorType",
  "message": "Human-readable error message",
  "details": {
    "field": "Additional context"
  },
  "timestamp": "2024-01-25T10:30:00Z",
  "request_id": "req_12345"
}
```

Common HTTP status codes:
- `200` - Success
- `201` - Created
- `202` - Accepted (async operation)
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `409` - Conflict
- `429` - Rate Limited
- `500` - Internal Server Error

## Rate Limiting

APIs implement rate limiting to prevent abuse:
- **Default**: 100 requests per minute per IP
- **Authenticated**: 1000 requests per minute per user
- **Evolution endpoints**: 10 requests per minute

Rate limit headers:
- `X-RateLimit-Limit`: Maximum requests allowed
- `X-RateLimit-Remaining`: Requests remaining
- `X-RateLimit-Reset`: Unix timestamp for limit reset

## Versioning

All APIs are versioned using URL path versioning:
- Current version: `v1`
- Version in URL: `/api/v1/...`

When new versions are released:
- Old versions supported for 6 months
- Deprecation notices in headers
- Migration guides provided

## Health Monitoring

Each service exposes health endpoints:

```bash
# Check all service health
curl http://localhost:8082/health  # DEAN Orchestrator
curl http://localhost:8081/health  # IndexAgent
curl http://localhost:8090/health  # Evolution API
```

Health response includes:
- Service status
- Dependency health
- Version information
- Response time metrics

## Support

For API support:
- Documentation: This directory
- Issues: GitHub repository
- Email: dean-api-support@example.com

## Next Steps

1. Review individual OpenAPI specifications
2. Set up authentication
3. Try example workflows
4. Integrate with your application
5. Monitor API metrics