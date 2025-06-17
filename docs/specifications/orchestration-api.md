# DEAN Orchestration API Specification

**Version**: 1.0.0  
**Last Updated**: June 13, 2025  
**Status**: Initial Draft

## Overview

This document specifies the API interfaces provided by the DEAN orchestration layer. The orchestration API serves as the coordination point between IndexAgent, Airflow, and infrastructure services.

## Base Configuration

- **Base URL**: `http://localhost:8093`
- **Protocol**: HTTP/1.1 with optional HTTP/2 support
- **Content Type**: `application/json`
- **Authentication**: Policy for API authentication has not been defined and requires stakeholder input

## API Endpoints

### Health and Status

#### GET /health
Returns the health status of the orchestration service.

**Response**:
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "timestamp": "2025-06-13T10:00:00Z",
  "services": {
    "indexagent": "healthy",
    "airflow": "healthy",
    "evolution": "healthy",
    "database": "healthy",
    "redis": "healthy"
  }
}
```

#### GET /status
Returns detailed status information about all connected services.

**Response**: Detailed service status including latency, last check time, and error counts.

### Evolution Orchestration

#### POST /evolution/start
Initiates a new evolution trial across all services.

**Request Body**:
```json
{
  "config": {
    "generations": 10,
    "population_size": 50,
    "mutation_rate": 0.1,
    "crossover_rate": 0.7,
    "selection_method": "tournament"
  },
  "constraints": {
    "max_tokens": 100000,
    "max_time_seconds": 3600
  }
}
```

**Response**: Evolution trial ID and initial status.

**Note**: Policy for evolution trial persistence and recovery has not been defined and requires stakeholder input.

#### GET /evolution/{trial_id}/status
Returns the current status of an evolution trial.

**Path Parameters**:
- `trial_id`: Unique identifier for the evolution trial

**Response**: Current generation, population metrics, and progress information.

#### POST /evolution/{trial_id}/stop
Stops a running evolution trial.

**Path Parameters**:
- `trial_id`: Unique identifier for the evolution trial

**Response**: Final trial status and summary metrics.

### Service Coordination

#### POST /workflow/execute
Executes a cross-service workflow.

**Request Body**:
```json
{
  "workflow_type": "agent_optimization",
  "parameters": {
    "target_repository": "https://github.com/example/repo",
    "optimization_goals": ["performance", "readability"]
  }
}
```

**Response**: Workflow execution ID and initial status.

**Note**: Policy for workflow definitions and custom workflow support has not been defined and requires stakeholder input.

#### GET /workflow/{execution_id}/status
Returns the status of a workflow execution.

### Monitoring and Metrics

#### GET /metrics
Returns aggregated metrics from all services.

**Query Parameters**:
- `start_time`: ISO 8601 timestamp
- `end_time`: ISO 8601 timestamp
- `service`: Filter by service name
- `metric_type`: Filter by metric type

**Response**: Time-series metrics data in Prometheus-compatible format.

#### GET /alerts
Returns active alerts from all services.

**Response**: List of active alerts with severity, service, and timestamp.

**Note**: Policy for alert thresholds and escalation has not been defined and requires stakeholder input.

### Configuration Management

#### GET /config
Returns the current orchestration configuration.

**Response**: Current configuration with sensitive values redacted.

#### PUT /config
Updates orchestration configuration.

**Request Body**: Partial configuration updates.

**Note**: Policy for configuration validation and rollback has not been defined and requires stakeholder input.

## Error Responses

All endpoints follow a consistent error response format:

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Evolution trial not found",
    "details": {
      "trial_id": "abc123",
      "suggestion": "Check trial ID or list active trials"
    }
  },
  "timestamp": "2025-06-13T10:00:00Z",
  "request_id": "req_123456"
}
```

### Error Codes

- `INVALID_REQUEST`: Request validation failed
- `RESOURCE_NOT_FOUND`: Requested resource does not exist
- `SERVICE_UNAVAILABLE`: Required service is not available
- `TIMEOUT`: Operation timed out
- `RATE_LIMITED`: Rate limit exceeded
- `INTERNAL_ERROR`: Internal server error

## Rate Limiting

**Note**: Policy for API rate limiting has not been defined and requires stakeholder input.

## Versioning

The API uses URL versioning. Future versions will be available at `/v2/`, `/v3/`, etc.

**Note**: Policy for API versioning and deprecation has not been defined and requires stakeholder input.

## WebSocket Endpoints

### WS /events
Real-time event stream for system events.

**Message Format**:
```json
{
  "event_type": "evolution.generation.complete",
  "timestamp": "2025-06-13T10:00:00Z",
  "data": {
    "trial_id": "abc123",
    "generation": 5,
    "best_fitness": 0.85
  }
}
```

## Security Considerations

**Note**: The following security policies have not been defined and require stakeholder input:
- Authentication mechanisms (API keys, JWT, OAuth)
- Authorization and role-based access control
- Encryption requirements for data in transit
- API key rotation policies
- Audit logging requirements

## Performance Requirements

- Response time: 95th percentile < 500ms for standard queries
- Throughput: Minimum 100 requests per second
- Availability: 99.9% uptime

**Note**: Policy for performance monitoring and SLA enforcement has not been defined and requires stakeholder input.

## Integration Points

This API integrates with:
- IndexAgent API (Port 8081)
- Airflow API (Port 8080)
- Evolution API (Port 8090)
- PostgreSQL Database (Port 5432)
- Redis Cache (Port 6379)

## Future Considerations

The following features are planned for future versions:
- GraphQL endpoint for flexible queries
- Batch operations for efficiency
- Webhook support for external integrations
- Advanced filtering and pagination

**Note**: Roadmap priorities require stakeholder input.