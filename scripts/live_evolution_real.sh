#\!/bin/bash
# Live Evolution Cycle Test - Real Execution with Correct Endpoints

echo "=== DEAN Live Evolution Cycle Test ==="
echo "Date: $(date)"
echo ""

# Test configuration
TOKEN_BUDGET=5000

echo "Configuration:"
echo "- Token Budget: $TOKEN_BUDGET"
echo ""

# 1. Create initial agents
echo "1. Creating initial agents..."
AGENTS=()
for i in {1..3}; do
    AGENT_RESPONSE=$(curl -s -X POST http://localhost:8081/api/v1/agents \
      -H "Content-Type: application/json" \
      -d '{
        "agent_id": "test_agent_'$i'_'$(date +%s)'",
        "initial_prompt": "You are an autonomous agent focused on discovering optimization patterns.",
        "token_budget": 1000
      }')
    
    AGENT_ID=$(echo "$AGENT_RESPONSE" | jq -r '.agent_id' 2>/dev/null)
    if [ \! -z "$AGENT_ID" ] && [ "$AGENT_ID" \!= "null" ]; then
        AGENTS+=("$AGENT_ID")
        echo "Created agent: $AGENT_ID"
    else
        echo "Failed to create agent $i:"
        echo "$AGENT_RESPONSE" | jq '.'
    fi
done

if [ ${#AGENTS[@]} -eq 0 ]; then
    echo "Error: No agents were created"
    exit 1
fi

echo ""
echo "Created ${#AGENTS[@]} agents"

# 2. Check global budget
echo ""
echo "2. Checking global token budget..."
curl -s http://localhost:8081/api/v1/budget/global | jq '.'

# 3. Trigger evolution for each agent
echo ""
echo "3. Starting evolution cycles..."
for agent_id in "${AGENTS[@]}"; do
    echo ""
    echo "Evolving agent: $agent_id"
    
    EVOLUTION_RESPONSE=$(curl -s -X POST http://localhost:8081/api/v1/agents/$agent_id/evolve \
      -H "Content-Type: application/json" \
      -d '{
        "generations": 3,
        "mutation_rate": 0.1,
        "crossover_rate": 0.2,
        "ca_rules": [30, 90, 110]
      }')
    
    echo "Evolution response:"
    echo "$EVOLUTION_RESPONSE" | jq '.'
done

# 4. Check for discovered patterns
echo ""
echo "4. Checking discovered patterns..."
PATTERNS_RESPONSE=$(curl -s http://localhost:8081/api/v1/patterns/discovered)
echo "$PATTERNS_RESPONSE" | jq '.'

# 5. Analyze code efficiency
echo ""
echo "5. Testing code analysis..."
CODE_ANALYSIS=$(curl -s -X POST http://localhost:8081/api/v1/code/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "code": "def fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)",
    "language": "python"
  }')
echo "$CODE_ANALYSIS" | jq '.'

# 6. Get efficiency metrics
echo ""
echo "6. Getting system efficiency metrics..."
curl -s http://localhost:8081/api/v1/metrics/efficiency | jq '.'

# 7. Pattern detection test
echo ""
echo "7. Testing pattern detection..."
PATTERN_DETECT=$(curl -s -X POST http://localhost:8081/api/v1/patterns/detect \
  -H "Content-Type: application/json" \
  -d '{
    "agents": ["agent1", "agent2"],
    "behaviors": [
      {"agent_id": "agent1", "action": "optimize", "context": "recursion"},
      {"agent_id": "agent2", "action": "optimize", "context": "memoization"}
    ]
  }')
echo "$PATTERN_DETECT" | jq '.'

# 8. Get final agent states
echo ""
echo "8. Getting final agent states..."
for agent_id in "${AGENTS[@]}"; do
    echo ""
    echo "Agent: $agent_id"
    curl -s http://localhost:8081/api/v1/agents/$agent_id | jq '.'
done

echo ""
echo "=== Evolution cycle test completed ==="
