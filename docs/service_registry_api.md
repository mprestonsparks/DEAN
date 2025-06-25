# Service Registry API Documentation

## Overview

The DEAN Service Registry provides dynamic service discovery, health monitoring, and circuit breaker integration for the distributed DEAN system. It enables services to register themselves, discover other services, and ensures fault tolerance through automatic health checks and circuit breakers.

## Core Concepts

### Service Registration
Services register themselves with the registry, providing:
- Basic information (name, host, port, version)
- Service metadata (type, capabilities, endpoints)
- Health check endpoint configuration

### Health Monitoring
The registry performs periodic health checks (every 30 seconds by default) on all registered services to maintain accurate status information.

### Circuit Breaker
Each service has an associated circuit breaker that:
- Opens after 3 consecutive failures
- Attempts reset after 60 seconds
- Prevents cascading failures

### Redis Persistence
Service registrations are persisted to Redis, allowing the registry to survive restarts while gracefully degrading if Redis is unavailable.

## API Endpoints

### Service Registration

#### Register Service
```http
POST /api/v1/registry/register
Content-Type: application/json

{
  "name": "my-service",
  "host": "localhost",
  "port": 8080,
  "version": "1.0.0",
  "metadata": {
    "service_type": "api",
    "api_version": "v1",
    "capabilities": ["feature-1", "feature-2"],
    "endpoints": {
      "users": "/api/v1/users",
      "health": "/health"
    },
    "dependencies": ["database", "cache"],
    "tags": {
      "team": "backend",
      "environment": "production"
    }
  },
  "health_endpoint": {
    "protocol": "http",
    "path": "/health",
    "timeout": 5.0,
    "method": "GET"
  }
}
```

**Response:**
```json
{
  "name": "my-service",
  "host": "localhost",
  "port": 8080,
  "version": "1.0.0",
  "status": "unknown",
  "last_health_check": null,
  "last_error": null,
  "metadata": {...}
}
```

#### Deregister Service
```http
DELETE /api/v1/registry/services/{service_name}
```

**Response:**
```json
{
  "message": "Service 'my-service' deregistered successfully"
}
```

### Service Discovery

#### List All Services
```http
GET /api/v1/registry/services
```

**Query Parameters:**
- `service_type`: Filter by service type
- `capability`: Filter by capability

**Response:**
```json
[
  {
    "name": "IndexAgent",
    "host": "indexagent",
    "port": 8081,
    "version": "1.0.0",
    "status": "healthy",
    "last_health_check": "2024-01-20T10:30:00Z",
    "last_error": null,
    "metadata": {...}
  }
]
```

#### Get Service Details
```http
GET /api/v1/registry/services/{service_name}
```

**Response:**
```json
{
  "name": "IndexAgent",
  "host": "indexagent",
  "port": 8081,
  "version": "1.0.0",
  "status": "healthy",
  "last_health_check": "2024-01-20T10:30:00Z",
  "last_error": null,
  "metadata": {
    "service_type": "agent-management",
    "api_version": "v1",
    "capabilities": ["agent-creation", "agent-evolution"],
    "endpoints": {
      "agents": "/api/v1/agents"
    }
  }
}
```

### Health Management

#### Service Heartbeat
```http
POST /api/v1/registry/services/{service_name}/heartbeat
```

**Response:**
```json
{
  "message": "Heartbeat received"
}
```

#### Update Service Metadata
```http
PATCH /api/v1/registry/services/{service_name}/metadata
Content-Type: application/json

{
  "service_type": "api",
  "api_version": "v2",
  "capabilities": ["feature-1", "feature-2", "feature-3"]
}
```

**Response:**
```json
{
  "message": "Metadata updated for service 'my-service'"
}
```

## Client Usage

### Python Client Example

```python
from src.integration.registry_client import create_registry_client

# Create registry client
client = create_registry_client(
    service_name="my-service",
    service_port=8080,
    service_version="1.0.0",
    metadata={
        "service_type": "worker",
        "api_version": "v1",
        "capabilities": ["data-processing"]
    }
)

# Start client (registers with DEAN)
await client.start()

# Discover another service
indexagent = await client.discover_service("IndexAgent")
if indexagent:
    print(f"Found IndexAgent at {indexagent['host']}:{indexagent['port']}")

# Call another service
response = await client.call_service(
    "IndexAgent",
    "/api/v1/agents",
    method="GET"
)

# Stop client (deregisters from DEAN)
await client.stop()
```

### Using Context Manager

```python
from src.integration.registry_client import ServiceRegistryContextManager

async with ServiceRegistryContextManager(
    registry_url="http://dean-orchestration:8082",
    service_name="my-service",
    service_port=8080,
    service_version="1.0.0"
) as client:
    # Service is automatically registered
    
    # Use the client
    services = await client.discover_services_by_type("api")
    
    # Service is automatically deregistered on exit
```

## Health Check Protocol

Services must implement a health endpoint that returns:

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "details": {
    "database": "connected",
    "cache": "connected"
  }
}
```

**Status Values:**
- `healthy`: Service is fully operational
- `degraded`: Service is operational but with reduced functionality
- `unhealthy`: Service is not operational

## Circuit Breaker Behavior

### States
1. **Closed**: Normal operation, requests pass through
2. **Open**: Service failures detected, requests blocked
3. **Half-Open**: Testing if service has recovered

### Configuration
- **Failure Threshold**: 3 consecutive failures
- **Success Threshold**: 2 consecutive successes in half-open state
- **Timeout**: 60 seconds before attempting reset

### Metrics

The circuit breaker exposes metrics via Prometheus:

```
dean_circuit_breaker_state{service_name="IndexAgent"} 0  # 0=closed, 1=open, 2=half-open
dean_service_health{service_name="IndexAgent"} 1  # 1=healthy, 0=unhealthy
```

## Error Handling

### Common Error Responses

#### Service Not Found
```json
{
  "detail": "Service 'unknown-service' not found"
}
```
**Status Code:** 404

#### Circuit Breaker Open
```json
{
  "detail": "Service temporarily unavailable: Circuit breaker 'IndexAgent' is open. Service unavailable."
}
```
**Status Code:** 503

#### Registration Failed
```json
{
  "detail": "Service registration failed: Invalid metadata format"
}
```
**Status Code:** 400

## Best Practices

1. **Service Naming**: Use consistent, descriptive names (e.g., `indexagent-prod`, `airflow-staging`)

2. **Metadata Standards**: Include all relevant information:
   - `service_type`: Category of service (api, worker, database, etc.)
   - `api_version`: Version of the API contract
   - `capabilities`: List of features the service provides
   - `endpoints`: Key API endpoints
   - `dependencies`: Other services this service depends on

3. **Health Checks**: Implement comprehensive health checks that verify:
   - Database connectivity
   - External service dependencies
   - Resource availability

4. **Heartbeats**: Services should send heartbeats every 25 seconds (less than the 30-second health check interval)

5. **Error Recovery**: Implement exponential backoff when registry connection fails

## Example: Complete Service Integration

```python
import asyncio
from fastapi import FastAPI
from src.integration.registry_client import create_registry_client

app = FastAPI()

# Registry client
registry_client = None

@app.on_event("startup")
async def startup():
    global registry_client
    
    # Create and start registry client
    registry_client = create_registry_client(
        service_name="my-api-service",
        service_port=8080,
        service_version="1.0.0",
        metadata={
            "service_type": "api",
            "api_version": "v1",
            "capabilities": ["user-management", "authentication"],
            "endpoints": {
                "users": "/api/v1/users",
                "auth": "/api/v1/auth"
            }
        }
    )
    
    await registry_client.start()

@app.on_event("shutdown")
async def shutdown():
    if registry_client:
        await registry_client.stop()

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "version": "1.0.0",
        "service": "my-api-service"
    }

# Use registry for service-to-service calls
@app.get("/api/v1/agents")
async def get_agents():
    response = await registry_client.call_service(
        "IndexAgent",
        "/api/v1/agents",
        method="GET"
    )
    return response.json()
```

## Monitoring and Observability

### Prometheus Metrics

The service registry exposes the following metrics:

- `dean_service_health`: Service health status (1=healthy, 0=unhealthy)
- `dean_circuit_breaker_state`: Circuit breaker state
- `dean_health_check_duration_seconds`: Duration of health checks
- `dean_service_registration_total`: Total service registrations

### Logging

The registry logs important events:
- Service registration/deregistration
- Health check results
- Circuit breaker state changes
- Redis connection status

### Dashboard Integration

The DEAN web dashboard (port 8083) provides visual monitoring of:
- Service status overview
- Circuit breaker states
- Health check history
- Service dependencies graph