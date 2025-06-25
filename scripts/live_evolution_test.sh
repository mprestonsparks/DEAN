#\!/bin/bash
# Live Evolution Cycle Test - Real Execution

echo "=== DEAN Live Evolution Cycle Test ==="
echo "Date: $(date)"
echo ""

# Test configuration
POPULATION_SIZE=3
GENERATIONS=5
TOKEN_BUDGET=5000

echo "Configuration:"
echo "- Population Size: $POPULATION_SIZE"
echo "- Generations: $GENERATIONS"  
echo "- Token Budget: $TOKEN_BUDGET"
echo ""

# 1. Create initial agent population
echo "1. Creating initial agent population..."
SPAWN_RESPONSE=$(curl -s -X POST http://localhost:8081/api/v1/agents/spawn \
  -H "Content-Type: application/json" \
  -d '{
    "genome_template": "default",
    "population_size": '$POPULATION_SIZE',
    "token_budget": 1000
  }')

echo "Spawn Response:"
echo "$SPAWN_RESPONSE" | jq '.'

# Extract agent IDs
AGENT_IDS=$(echo "$SPAWN_RESPONSE" | jq -r '.agent_ids[]' 2>/dev/null)
if [ -z "$AGENT_IDS" ]; then
    echo "Error: Failed to create agents"
    exit 1
fi

echo ""
echo "Created agents:"
echo "$AGENT_IDS"

# 2. Check population diversity
echo ""
echo "2. Checking initial population diversity..."
DIVERSITY_RESPONSE=$(curl -s -X POST http://localhost:8081/api/v1/diversity/population \
  -H "Content-Type: application/json" \
  -d "{\"population_ids\": $(echo "$AGENT_IDS" | jq -R . | jq -s .)}")

echo "Diversity Response:"
echo "$DIVERSITY_RESPONSE" | jq '.'

# 3. Start evolution cycle via DEAN Orchestrator
echo ""
echo "3. Starting evolution cycle..."
EVOLUTION_RESPONSE=$(curl -s -X POST http://localhost:8082/api/v1/evolution/start \
  -H "Content-Type: application/json" \
  -d '{
    "population_ids": '"$(echo "$AGENT_IDS" | jq -R . | jq -s .)"',
    "generations": '$GENERATIONS',
    "token_budget": '$TOKEN_BUDGET'
  }')

echo "Evolution Start Response:"
echo "$EVOLUTION_RESPONSE" | jq '.'

CYCLE_ID=$(echo "$EVOLUTION_RESPONSE" | jq -r '.cycle_id' 2>/dev/null)
if [ -z "$CYCLE_ID" ]; then
    echo "Error: Failed to start evolution cycle"
    exit 1
fi

# 4. Monitor evolution progress
echo ""
echo "4. Monitoring evolution progress..."
for i in {1..30}; do
    sleep 2
    STATUS_RESPONSE=$(curl -s http://localhost:8082/api/v1/evolution/$CYCLE_ID/status)
    STATUS=$(echo "$STATUS_RESPONSE" | jq -r '.status' 2>/dev/null)
    
    echo "Generation $(echo "$STATUS_RESPONSE" | jq -r '.current_generation' 2>/dev/null)/$GENERATIONS - Status: $STATUS"
    
    if [ "$STATUS" == "completed" ] || [ "$STATUS" == "failed" ]; then
        echo "Final Status:"
        echo "$STATUS_RESPONSE" | jq '.'
        break
    fi
done

# 5. Get discovered patterns
echo ""
echo "5. Retrieving discovered patterns..."
PATTERNS_RESPONSE=$(curl -s http://localhost:8081/api/v1/patterns)
echo "Patterns Response:"
echo "$PATTERNS_RESPONSE" | jq '.'

# 6. Get token usage metrics
echo ""
echo "6. Getting token usage metrics..."
METRICS_RESPONSE=$(curl -s http://localhost:8082/api/v1/metrics/tokens)
echo "Token Metrics:"
echo "$METRICS_RESPONSE" | jq '.'

# 7. Get agent stats
echo ""
echo "7. Getting final agent statistics..."
for agent_id in $AGENT_IDS; do
    echo "Agent: $agent_id"
    curl -s http://localhost:8081/api/v1/agents/$agent_id | jq '.'
done

echo ""
echo "=== Evolution cycle test completed ==="
