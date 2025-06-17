# DEAN API Examples

This document provides practical examples for using the DEAN Orchestration API. All examples include both curl commands and Python/JavaScript code snippets.

## Table of Contents

1. [Authentication](#authentication)
2. [Agent Management](#agent-management)
3. [Evolution Trials](#evolution-trials)
4. [Pattern Discovery](#pattern-discovery)
5. [WebSocket Integration](#websocket-integration)
6. [Error Handling](#error-handling)

---

## Authentication

### Login

**curl:**
```bash
curl -X POST https://api.dean-orchestration.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "your-secure-password"
  }'
```

**Python:**
```python
import requests

response = requests.post(
    "https://api.dean-orchestration.com/auth/login",
    json={
        "username": "admin",
        "password": "your-secure-password"
    }
)

tokens = response.json()
access_token = tokens["access_token"]
refresh_token = tokens["refresh_token"]
```

**JavaScript:**
```javascript
const response = await fetch('https://api.dean-orchestration.com/auth/login', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    username: 'admin',
    password: 'your-secure-password'
  })
});

const tokens = await response.json();
const { access_token, refresh_token } = tokens;
```

### Refresh Token

**curl:**
```bash
curl -X POST https://api.dean-orchestration.com/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "your-refresh-token"
  }'
```

**Python:**
```python
response = requests.post(
    "https://api.dean-orchestration.com/auth/refresh",
    json={"refresh_token": refresh_token}
)

new_tokens = response.json()
```

---

## Agent Management

### Create Agent

**curl:**
```bash
curl -X POST https://api.dean-orchestration.com/api/agents \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "performance-optimizer",
    "language": "python",
    "capabilities": ["optimize", "profile", "analyze"],
    "initial_fitness": 0.6
  }'
```

**Python:**
```python
headers = {"Authorization": f"Bearer {access_token}"}

agent_data = {
    "name": "performance-optimizer",
    "language": "python",
    "capabilities": ["optimize", "profile", "analyze"],
    "initial_fitness": 0.6
}

response = requests.post(
    "https://api.dean-orchestration.com/api/agents",
    headers=headers,
    json=agent_data
)

agent = response.json()
print(f"Created agent: {agent['id']}")
```

### List Agents with Filtering

**curl:**
```bash
curl -X GET "https://api.dean-orchestration.com/api/agents?status=active&language=python&limit=50" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

**JavaScript:**
```javascript
const params = new URLSearchParams({
  status: 'active',
  language: 'python',
  limit: 50
});

const response = await fetch(`https://api.dean-orchestration.com/api/agents?${params}`, {
  headers: {
    'Authorization': `Bearer ${access_token}`
  }
});

const { agents, total } = await response.json();
console.log(`Found ${total} agents, showing ${agents.length}`);
```

### Update Agent

**Python:**
```python
agent_id = "123e4567-e89b-12d3-a456-426614174000"

update_data = {
    "status": "inactive",
    "capabilities": ["optimize", "profile", "analyze", "refactor"]
}

response = requests.put(
    f"https://api.dean-orchestration.com/api/agents/{agent_id}",
    headers=headers,
    json=update_data
)
```

---

## Evolution Trials

### Start Evolution Trial

**curl:**
```bash
curl -X POST https://api.dean-orchestration.com/api/evolution/start \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "repository": "github.com/myorg/optimization-target",
    "generations": 20,
    "population_size": 100,
    "mutation_rate": 0.15,
    "crossover_rate": 0.7,
    "fitness_threshold": 0.95,
    "selection_method": "tournament"
  }'
```

**Python with Progress Monitoring:**
```python
import json
import asyncio
import websockets

# Start evolution trial
response = requests.post(
    "https://api.dean-orchestration.com/api/evolution/start",
    headers=headers,
    json={
        "repository": "github.com/myorg/optimization-target",
        "generations": 20,
        "population_size": 100,
        "mutation_rate": 0.15,
        "crossover_rate": 0.7,
        "fitness_threshold": 0.95,
        "selection_method": "tournament"
    }
)

trial = response.json()
trial_id = trial["id"]

# Monitor progress via WebSocket
async def monitor_progress():
    uri = f"wss://api.dean-orchestration.com/ws"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    async with websockets.connect(uri, extra_headers=headers) as websocket:
        # Subscribe to trial updates
        await websocket.send(json.dumps({
            "action": "subscribe",
            "events": [f"evolution.progress.{trial_id}"]
        }))
        
        # Listen for updates
        async for message in websocket:
            data = json.loads(message)
            if data["event"] == "evolution.progress":
                print(f"Generation {data['generation']}/{data['total_generations']}")
                print(f"Best fitness: {data['best_fitness']}")
                print(f"Patterns found: {data['patterns_discovered']}")

# Run the monitor
asyncio.run(monitor_progress())
```

### Get Trial Status

**JavaScript:**
```javascript
const trialId = '456e7890-e89b-12d3-a456-426614174000';

const response = await fetch(`https://api.dean-orchestration.com/api/evolution/trials/${trialId}`, {
  headers: {
    'Authorization': `Bearer ${access_token}`
  }
});

const trial = await response.json();

// Display trial progress
console.log(`Status: ${trial.status}`);
console.log(`Progress: ${trial.current_generation}/${trial.total_generations}`);
console.log(`Best fitness: ${trial.best_fitness}`);
console.log(`Patterns discovered: ${trial.patterns_discovered}`);
```

### Stop Running Trial

**curl:**
```bash
curl -X POST "https://api.dean-orchestration.com/api/evolution/trials/$TRIAL_ID/stop" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

---

## Pattern Discovery

### Search Patterns

**curl:**
```bash
curl -X GET "https://api.dean-orchestration.com/api/patterns?min_confidence=0.8&category=performance&language=python" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

**Python with Filtering:**
```python
params = {
    "min_confidence": 0.8,
    "category": "performance",
    "language": "python"
}

response = requests.get(
    "https://api.dean-orchestration.com/api/patterns",
    headers=headers,
    params=params
)

patterns = response.json()["patterns"]

# Display high-impact patterns
for pattern in patterns:
    if pattern["impact_score"] > 0.8:
        print(f"\nPattern: {pattern['name']}")
        print(f"Confidence: {pattern['confidence']:.2f}")
        print(f"Impact: {pattern['impact_score']:.2f}")
        print(f"Description: {pattern['description']}")
```

### Apply Pattern

**JavaScript:**
```javascript
const patternId = '789a1234-e89b-12d3-a456-426614174000';

// First, preview changes (dry run)
const dryRunResponse = await fetch(
  `https://api.dean-orchestration.com/api/patterns/${patternId}/apply`,
  {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${access_token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      target_file: 'src/handlers/search.py',
      target_function: 'search_database',
      dry_run: true
    })
  }
);

const preview = await dryRunResponse.json();
console.log('Preview of changes:');
console.log(preview.diff);
console.log(`Estimated performance improvement: ${preview.estimated_improvement.performance}`);

// If satisfied, apply the pattern
if (confirm('Apply these changes?')) {
  const applyResponse = await fetch(
    `https://api.dean-orchestration.com/api/patterns/${patternId}/apply`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${access_token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        target_file: 'src/handlers/search.py',
        target_function: 'search_database',
        dry_run: false
      })
    }
  );
  
  const result = await applyResponse.json();
  console.log(`Applied ${result.changes_made} changes successfully`);
}
```

---

## WebSocket Integration

### Real-time Monitoring

**JavaScript:**
```javascript
class DEANWebSocket {
  constructor(accessToken) {
    this.accessToken = accessToken;
    this.ws = null;
    this.reconnectAttempts = 0;
  }

  connect() {
    this.ws = new WebSocket('wss://api.dean-orchestration.com/ws');
    
    this.ws.onopen = () => {
      console.log('WebSocket connected');
      this.reconnectAttempts = 0;
      
      // Send authentication
      this.send({
        action: 'auth',
        token: this.accessToken
      });
      
      // Subscribe to events
      this.subscribe(['evolution.progress', 'pattern.discovered', 'system.metrics']);
    };
    
    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.handleMessage(data);
    };
    
    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
    
    this.ws.onclose = () => {
      console.log('WebSocket closed');
      this.reconnect();
    };
  }
  
  reconnect() {
    if (this.reconnectAttempts < 5) {
      this.reconnectAttempts++;
      setTimeout(() => this.connect(), 5000 * this.reconnectAttempts);
    }
  }
  
  send(data) {
    if (this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }
  
  subscribe(events) {
    this.send({
      action: 'subscribe',
      events: events
    });
  }
  
  handleMessage(data) {
    switch (data.event) {
      case 'evolution.progress':
        console.log(`Evolution progress: Generation ${data.generation}/${data.total}`);
        console.log(`Best fitness: ${data.best_fitness}`);
        break;
        
      case 'pattern.discovered':
        console.log(`New pattern discovered: ${data.pattern_name}`);
        console.log(`Confidence: ${data.confidence}`);
        break;
        
      case 'system.metrics':
        console.log(`CPU: ${data.cpu_usage}%, Memory: ${data.memory_usage}%`);
        break;
    }
  }
}

// Usage
const ws = new DEANWebSocket(access_token);
ws.connect();
```

**Python WebSocket Client:**
```python
import asyncio
import json
import websockets

class DEANWebSocketClient:
    def __init__(self, access_token):
        self.access_token = access_token
        self.uri = "wss://api.dean-orchestration.com/ws"
    
    async def connect(self):
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        async with websockets.connect(self.uri, extra_headers=headers) as websocket:
            # Subscribe to events
            await websocket.send(json.dumps({
                "action": "subscribe",
                "events": ["evolution.progress", "pattern.discovered", "agent.status"]
            }))
            
            # Handle incoming messages
            async for message in websocket:
                data = json.loads(message)
                await self.handle_message(data)
    
    async def handle_message(self, data):
        event_type = data.get("event")
        
        if event_type == "evolution.progress":
            print(f"Generation {data['generation']}: "
                  f"Best fitness = {data['best_fitness']:.3f}")
        
        elif event_type == "pattern.discovered":
            print(f"New pattern: {data['pattern_name']} "
                  f"(confidence: {data['confidence']:.2f})")
        
        elif event_type == "agent.status":
            print(f"Agent {data['agent_id']} is now {data['status']}")

# Run the client
client = DEANWebSocketClient(access_token)
asyncio.run(client.connect())
```

---

## Error Handling

### Python Error Handler

```python
class DEANAPIClient:
    def __init__(self, base_url, access_token):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {access_token}"}
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def make_request(self, method, endpoint, **kwargs):
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.HTTPError as e:
            error_data = e.response.json()
            error_code = error_data.get("code")
            
            if e.response.status_code == 401:
                # Handle authentication errors
                if error_code == "AUTH_001":
                    # Token expired, try to refresh
                    self.refresh_token()
                    # Retry the request
                    return self.make_request(method, endpoint, **kwargs)
            
            elif e.response.status_code == 429:
                # Handle rate limiting
                retry_after = error_data.get("details", {}).get("retry_after", 60)
                print(f"Rate limited. Retrying after {retry_after} seconds...")
                time.sleep(retry_after)
                return self.make_request(method, endpoint, **kwargs)
            
            elif e.response.status_code == 400:
                # Handle validation errors
                print(f"Validation error: {error_data}")
                raise
            
            else:
                print(f"API Error: {error_data}")
                raise
        
        except requests.exceptions.ConnectionError:
            print("Connection error. Please check your network.")
            raise
        
        except requests.exceptions.Timeout:
            print("Request timed out. Please try again.")
            raise
    
    def create_agent(self, agent_data):
        return self.make_request("POST", "/api/agents", json=agent_data)
    
    def get_patterns(self, **filters):
        return self.make_request("GET", "/api/patterns", params=filters)

# Usage with error handling
client = DEANAPIClient("https://api.dean-orchestration.com", access_token)

try:
    # Create an agent
    agent = client.create_agent({
        "name": "test-agent",
        "language": "python",
        "capabilities": ["optimize"]
    })
    print(f"Created agent: {agent['id']}")
    
    # Get patterns
    patterns = client.get_patterns(min_confidence=0.8)
    print(f"Found {len(patterns['patterns'])} patterns")
    
except Exception as e:
    print(f"Operation failed: {e}")
```

### JavaScript Error Handler

```javascript
class DEANAPIClient {
  constructor(baseURL, accessToken) {
    this.baseURL = baseURL;
    this.accessToken = accessToken;
  }
  
  async makeRequest(method, endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const config = {
      method,
      headers: {
        'Authorization': `Bearer ${this.accessToken}`,
        'Content-Type': 'application/json',
        ...options.headers
      },
      ...options
    };
    
    try {
      const response = await fetch(url, config);
      
      if (!response.ok) {
        const errorData = await response.json();
        
        switch (response.status) {
          case 401:
            // Handle authentication error
            if (errorData.code === 'AUTH_001') {
              await this.refreshToken();
              // Retry the request
              return this.makeRequest(method, endpoint, options);
            }
            break;
            
          case 429:
            // Handle rate limiting
            const retryAfter = errorData.details?.retry_after || 60;
            console.log(`Rate limited. Retrying after ${retryAfter}s...`);
            await new Promise(resolve => setTimeout(resolve, retryAfter * 1000));
            return this.makeRequest(method, endpoint, options);
            
          case 400:
            // Handle validation errors
            console.error('Validation error:', errorData);
            throw new Error(`Validation failed: ${errorData.details?.message}`);
            
          default:
            throw new Error(`API Error: ${errorData.error}`);
        }
      }
      
      return await response.json();
      
    } catch (error) {
      if (error.name === 'TypeError' && error.message === 'Failed to fetch') {
        console.error('Network error. Please check your connection.');
      }
      throw error;
    }
  }
  
  async createAgent(agentData) {
    return this.makeRequest('POST', '/api/agents', {
      body: JSON.stringify(agentData)
    });
  }
  
  async getPatterns(filters = {}) {
    const params = new URLSearchParams(filters);
    return this.makeRequest('GET', `/api/patterns?${params}`);
  }
}

// Usage with async/await error handling
(async () => {
  const client = new DEANAPIClient('https://api.dean-orchestration.com', accessToken);
  
  try {
    // Create agent
    const agent = await client.createAgent({
      name: 'test-agent',
      language: 'javascript',
      capabilities: ['optimize', 'analyze']
    });
    console.log(`Created agent: ${agent.id}`);
    
    // Get patterns
    const patterns = await client.getPatterns({ min_confidence: 0.8 });
    console.log(`Found ${patterns.patterns.length} patterns`);
    
  } catch (error) {
    console.error('Operation failed:', error.message);
  }
})();
```

---

## SDK Examples

### Python SDK Usage

```python
# Install: pip install dean-sdk

from dean_sdk import DEANClient
from dean_sdk.models import Agent, EvolutionConfig

# Initialize client
client = DEANClient(
    api_key="your-api-key",
    base_url="https://api.dean-orchestration.com"
)

# Create and manage agents
agent = client.agents.create(
    name="ml-optimizer",
    language="python",
    capabilities=["optimize", "ml", "profile"]
)

# Start evolution with builder pattern
evolution = client.evolution.start(
    EvolutionConfig()
    .repository("github.com/myorg/ml-project")
    .generations(30)
    .population_size(200)
    .mutation_rate(0.2)
    .fitness_threshold(0.95)
    .build()
)

# Monitor progress with callbacks
def on_progress(generation, fitness, patterns):
    print(f"Gen {generation}: fitness={fitness:.3f}, patterns={patterns}")

def on_pattern_discovered(pattern):
    print(f"New pattern: {pattern.name} (impact: {pattern.impact_score})")

evolution.monitor(
    on_progress=on_progress,
    on_pattern_discovered=on_pattern_discovered
)

# Apply patterns automatically
patterns = client.patterns.search(
    min_confidence=0.9,
    category="performance",
    auto_apply=True
)
```

### JavaScript/TypeScript SDK Usage

```typescript
// Install: npm install @dean/sdk

import { DEANClient, AgentConfig, EvolutionBuilder } from '@dean/sdk';

// Initialize client
const client = new DEANClient({
  apiKey: 'your-api-key',
  baseURL: 'https://api.dean-orchestration.com'
});

// Create agent with TypeScript types
const agent = await client.agents.create({
  name: 'ts-optimizer',
  language: 'javascript',
  capabilities: ['optimize', 'refactor', 'test']
} as AgentConfig);

// Start evolution with fluent API
const evolution = await client.evolution
  .configure()
  .repository('github.com/myorg/ts-project')
  .generations(25)
  .populationSize(150)
  .mutationRate(0.18)
  .fitnessThreshold(0.92)
  .start();

// Real-time monitoring with event emitters
evolution.on('progress', ({ generation, fitness, patterns }) => {
  console.log(`Gen ${generation}: fitness=${fitness.toFixed(3)}, patterns=${patterns}`);
});

evolution.on('pattern', (pattern) => {
  console.log(`New pattern: ${pattern.name} (confidence: ${pattern.confidence})`);
});

evolution.on('complete', (results) => {
  console.log('Evolution complete!');
  console.log(`Total patterns discovered: ${results.patternsDiscovered}`);
  console.log(`Final best fitness: ${results.bestFitness}`);
});

// Apply patterns with preview
const patterns = await client.patterns.search({
  minConfidence: 0.85,
  language: 'javascript'
});

for (const pattern of patterns) {
  const preview = await pattern.preview('src/handlers/api.ts');
  
  if (preview.estimatedImprovement.performance > 30) {
    await pattern.apply('src/handlers/api.ts');
    console.log(`Applied pattern: ${pattern.name}`);
  }
}
```

---

## Rate Limiting and Best Practices

### Rate Limits

- Authentication endpoints: 5 requests per minute
- API endpoints: 10 requests per second
- WebSocket connections: 1 per user
- Evolution trials: 5 concurrent per account

### Best Practices

1. **Use WebSockets for real-time updates** instead of polling
2. **Batch operations** when possible (e.g., creating multiple agents)
3. **Implement exponential backoff** for retries
4. **Cache pattern results** to avoid repeated queries
5. **Use pagination** for large result sets
6. **Set appropriate timeouts** for long-running operations

### Example: Batch Operations

```python
# Instead of creating agents one by one
agents_data = [
    {"name": f"agent-{i}", "language": "python", "capabilities": ["optimize"]}
    for i in range(10)
]

# Use batch creation
response = requests.post(
    "https://api.dean-orchestration.com/api/agents/batch",
    headers=headers,
    json={"agents": agents_data}
)

created_agents = response.json()["agents"]
print(f"Created {len(created_agents)} agents in one request")
```

---

## Additional Resources

- [OpenAPI Specification](./openapi.yaml)
- [SDK Documentation](https://github.com/dean/sdk-docs)
- [WebSocket Protocol](./WEBSOCKET_PROTOCOL.md)
- [Authentication Guide](../SECURITY_GUIDE.md)
- [Rate Limiting Guide](./RATE_LIMITS.md)

For more examples and advanced usage, visit our [GitHub repository](https://github.com/dean/examples).