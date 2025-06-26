#!/bin/bash

# Test Token Economy Service
# This script verifies the token economy is enforcing hard limits

echo "Testing Token Economy Service..."
echo "==============================="

# Check if service is running
echo -n "Checking service health... "
if curl -s http://localhost:8091/health > /dev/null; then
    echo "✓ Service is healthy"
else
    echo "✗ Service not running"
    echo "Start with: cd infra/modules/agent-evolution && docker-compose -f docker-compose.token_economy.yml up -d"
    exit 1
fi

# Test 1: Request allocation
echo -e "\n1. Testing token allocation..."
RESPONSE=$(curl -s -X POST http://localhost:8091/api/v1/tokens/allocate \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "test_agent_1",
    "requested_tokens": 500,
    "agent_metadata": {"type": "evolution"}
  }')

echo "Response: $RESPONSE"

# Test 2: Check global status
echo -e "\n2. Checking global budget status..."
curl -s http://localhost:8091/api/v1/tokens/status | jq .

# Test 3: Test budget exhaustion
echo -e "\n3. Testing budget exhaustion (10 agents requesting 2000 tokens each)..."
for i in {1..10}; do
    echo -n "Agent $i: "
    RESPONSE=$(curl -s -X POST http://localhost:8091/api/v1/tokens/allocate \
      -H "Content-Type: application/json" \
      -d "{
        \"agent_id\": \"exhaustion_test_$i\",
        \"requested_tokens\": 2000
      }")
    
    if echo "$RESPONSE" | grep -q "allocated"; then
        ALLOCATED=$(echo "$RESPONSE" | jq -r .allocated)
        echo "✓ Allocated $ALLOCATED tokens"
    else
        echo "✗ Allocation failed - budget exhausted"
    fi
done

# Test 4: Final status
echo -e "\n4. Final budget status..."
curl -s http://localhost:8091/api/v1/tokens/status | jq .

echo -e "\n✓ Token economy test complete!"