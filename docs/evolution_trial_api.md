# Evolution Trial API Documentation

This document describes the REST and WebSocket APIs for managing DEAN evolution trials through the orchestration layer.

## Overview

The Evolution Trial API provides endpoints for creating, monitoring, and managing agent evolution trials. Each trial executes a workflow that coordinates multiple services (IndexAgent, Airflow, Evolution API) to evolve a population of agents over multiple generations.

## Authentication

All endpoints require JWT authentication. Include the authentication token in the Authorization header:

```
Authorization: Bearer <jwt-token>
```

Service-to-service calls automatically propagate authentication tokens through the `X-DEAN-Service-Token` header.

## REST API Endpoints

### Start Evolution Trial

Start a new evolution trial with specified parameters.

**Endpoint**: `POST /api/v1/orchestration/evolution/start`

**Request Body**:
```json
{
  "population_size": 10,
  "generations": 50,
  "token_budget": 100000,
  "diversity_threshold": 0.3
}
```

**Parameters**:
- `population_size` (integer, required): Number of agents in the population (1-100)
- `generations` (integer, required): Number of evolution generations (1-1000)
- `token_budget` (integer, required): Total token budget for the trial
- `diversity_threshold` (float, required): Minimum diversity threshold (0.1-1.0)

**Response**:
```json
{
  "trial_id": "550e8400-e29b-41d4-a716-446655440000",
  "workflow_instance_id": "wf_123456789",
  "status": "initializing",
  "parameters": {
    "population_size": 10,
    "generations": 50,
    "token_budget": 100000,
    "diversity_threshold": 0.3
  },
  "message": "Evolution trial started successfully",
  "websocket_url": "/ws/evolution/550e8400-e29b-41d4-a716-446655440000"
}
```

**Status Codes**:
- 200: Trial started successfully
- 400: Invalid parameters
- 401: Unauthorized
- 500: Internal server error

### Get Evolution Trial Status

Get detailed status and metrics for a specific evolution trial.

**Endpoint**: `GET /api/v1/orchestration/evolution/{trial_id}/status`

**Response**:
```json
{
  "trial_id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Evolution Trial 2025-06-25 10:30:00",
  "status": "running",
  "workflow_instance_id": "wf_123456789",
  "parameters": {
    "population_size": 10,
    "generations": 50,
    "token_budget": 100000,
    "diversity_threshold": 0.3
  },
  "progress": {
    "current_generation": 25,
    "total_generations": 50,
    "percentage": 50.0
  },
  "resource_usage": {
    "tokens_used": 45000,
    "tokens_budget": 100000,
    "tokens_remaining": 55000,
    "usage_percentage": 45.0
  },
  "performance": {
    "best_fitness": 0.85,
    "diversity_index": 0.42,
    "patterns_discovered": 7,
    "active_agents": 10
  },
  "timing": {
    "started_at": "2025-06-25T10:30:00Z",
    "duration_seconds": 1800,
    "estimated_completion": "2025-06-25T11:00:00Z"
  },
  "generation_metrics": [
    {
      "generation": 25,
      "avg_fitness": 0.72,
      "max_fitness": 0.85,
      "min_fitness": 0.45,
      "diversity_index": 0.42,
      "total_tokens_used": 2000,
      "patterns_discovered": 2,
      "timestamp": "2025-06-25T10:45:00Z"
    }
  ],
  "agent_count": 10,
  "best_agent": {
    "id": "agent_123",
    "fitness": 0.85
  },
  "error": null
}
```

**Status Values**:
- `pending`: Trial created but not started
- `initializing`: Setting up agent population
- `running`: Evolution in progress
- `monitoring`: Final metrics collection
- `completed`: Trial finished successfully
- `failed`: Trial failed with error
- `cancelled`: Trial cancelled by user

### List Evolution Trials

List all evolution trials with optional status filtering.

**Endpoint**: `GET /api/v1/orchestration/evolution/list`

**Query Parameters**:
- `status` (string, optional): Filter by trial status
- `limit` (integer, optional): Maximum number of trials to return (default: 100)

**Response**:
```json
{
  "trials": [
    {
      "trial_id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Evolution Trial 2025-06-25 10:30:00",
      "status": "completed",
      "created_at": "2025-06-25T10:29:00Z",
      "started_at": "2025-06-25T10:30:00Z",
      "completed_at": "2025-06-25T11:00:00Z",
      "population_size": 10,
      "generations": 50,
      "current_generation": 50,
      "best_fitness": 0.92,
      "tokens_used": 95000,
      "patterns_discovered": 15
    }
  ],
  "total": 1
}
```

### Cancel Evolution Trial

Cancel a running evolution trial.

**Endpoint**: `POST /api/v1/orchestration/evolution/{trial_id}/cancel`

**Response**:
```json
{
  "trial_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "cancelled",
  "message": "Evolution trial cancelled successfully"
}
```

**Status Codes**:
- 200: Trial cancelled successfully
- 404: Trial not found or not cancellable
- 401: Unauthorized

## WebSocket API

### Real-time Evolution Monitoring

Connect to the WebSocket endpoint to receive real-time updates during trial execution.

**Endpoint**: `ws://localhost:8082/ws/evolution/{trial_id}`

**Connection Example**:
```javascript
const ws = new WebSocket('ws://localhost:8082/ws/evolution/550e8400-e29b-41d4-a716-446655440000');

ws.onmessage = (event) => {
  const update = JSON.parse(event.data);
  console.log('Evolution update:', update);
};
```

**Message Types**:

#### Status Message
Sent immediately upon connection:
```json
{
  "type": "status",
  "trial": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "running",
    "current_generation": 10,
    "total_tokens_used": 20000
  }
}
```

#### Update Message
Sent periodically during trial execution:
```json
{
  "type": "update",
  "trial_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "running",
  "current_generation": 15,
  "total_tokens_used": 30000,
  "best_fitness_score": 0.75,
  "agent_count": 10,
  "patterns_discovered": 5,
  "generation_metrics": [
    {
      "generation": 15,
      "avg_fitness": 0.68,
      "max_fitness": 0.75,
      "min_fitness": 0.52,
      "diversity_index": 0.38,
      "total_tokens_used": 1800,
      "patterns_discovered": 1,
      "timestamp": "2025-06-25T10:40:00Z"
    }
  ]
}
```

#### Completion Message
Sent when trial completes:
```json
{
  "type": "complete",
  "trial_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "message": "Trial completed"
}
```

## Evolution Trial Workflow

Each evolution trial executes the following workflow steps:

1. **Validate Token Budget**: Ensure sufficient tokens for trial
2. **Create Agent Population**: Initialize agents with diversity
3. **Start Evolution Process**: Begin genetic algorithm execution
4. **Trigger Airflow DAG**: Start monitoring and orchestration
5. **Monitor Progress**: Track diversity, efficiency, and fitness
6. **Inject Mutations**: Maintain diversity if needed
7. **Collect Patterns**: Gather discovered optimization patterns
8. **Store Patterns**: Save successful patterns for reuse
9. **Update Allocations**: Adjust token allocations based on performance
10. **Generate Report**: Create final trial summary

## Error Handling

The API implements comprehensive error handling:

- **Service Unavailable**: Returns 503 when required services are down
- **Circuit Breaker**: Prevents cascading failures with automatic recovery
- **Retry Logic**: Automatic retries with exponential backoff
- **Graceful Degradation**: Continues operation when non-critical services fail

## Usage Examples

### Python Client Example

```python
import httpx
import asyncio
import websockets
import json

async def run_evolution_trial():
    # Start trial
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8082/api/v1/orchestration/evolution/start",
            json={
                "population_size": 10,
                "generations": 50,
                "token_budget": 100000,
                "diversity_threshold": 0.3
            },
            headers={"Authorization": "Bearer <your-token>"}
        )
        
        trial_data = response.json()
        trial_id = trial_data["trial_id"]
        
    # Monitor via WebSocket
    async with websockets.connect(
        f"ws://localhost:8082/ws/evolution/{trial_id}"
    ) as websocket:
        async for message in websocket:
            update = json.loads(message)
            print(f"Generation {update.get('current_generation')}: "
                  f"Best fitness = {update.get('best_fitness_score')}")
            
            if update.get("type") == "complete":
                break
                
    # Get final results
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"http://localhost:8082/api/v1/orchestration/evolution/{trial_id}/status",
            headers={"Authorization": "Bearer <your-token>"}
        )
        
        final_results = response.json()
        print(f"Trial completed: {final_results['performance']}")

# Run the example
asyncio.run(run_evolution_trial())
```

### JavaScript Client Example

```javascript
async function runEvolutionTrial() {
  // Start trial
  const response = await fetch('http://localhost:8082/api/v1/orchestration/evolution/start', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer <your-token>'
    },
    body: JSON.stringify({
      population_size: 10,
      generations: 50,
      token_budget: 100000,
      diversity_threshold: 0.3
    })
  });
  
  const trial = await response.json();
  console.log('Trial started:', trial.trial_id);
  
  // Monitor via WebSocket
  const ws = new WebSocket(`ws://localhost:8082/ws/evolution/${trial.trial_id}`);
  
  ws.onmessage = (event) => {
    const update = JSON.parse(event.data);
    
    if (update.type === 'update') {
      console.log(`Generation ${update.current_generation}: ` +
                  `Best fitness = ${update.best_fitness_score}`);
    } else if (update.type === 'complete') {
      console.log('Trial completed:', update.status);
      ws.close();
    }
  };
  
  ws.onerror = (error) => {
    console.error('WebSocket error:', error);
  };
}
```

## Best Practices

1. **Token Budget Planning**: Set realistic token budgets based on population size and generations
2. **Diversity Monitoring**: Use WebSocket updates to monitor diversity in real-time
3. **Pattern Analysis**: Review discovered patterns after each trial for insights
4. **Resource Management**: Cancel long-running trials if they exceed expected duration
5. **Error Recovery**: Implement retry logic for transient failures
6. **Batch Processing**: Use the list endpoint to analyze multiple trials together