#!/bin/bash
# Validate DEAN System Evolution Cycle
# This script starts all services and executes an end-to-end evolution test

set -e

echo "=== DEAN System Evolution Cycle Validation ==="
echo "Starting at: $(date)"

# Change to infra directory
cd ../infra

# Step 1: Start all services
echo -e "\n1. Starting all DEAN services..."
docker-compose -f docker-compose.dean-complete.yml up -d

# Wait for services to be healthy
echo -e "\n2. Waiting for services to be healthy..."
sleep 30  # Initial wait

# Check service health
for service in postgres redis dean-orchestrator indexagent dean-api airflow-webserver airflow-scheduler; do
    echo -n "Checking $service... "
    if docker-compose -f docker-compose.dean-complete.yml ps | grep -q "$service.*healthy"; then
        echo "✅ Healthy"
    else
        echo "❌ Not healthy"
        docker-compose -f docker-compose.dean-complete.yml ps
        exit 1
    fi
done

# Step 3: Initialize Airflow
echo -e "\n3. Initializing Airflow..."
docker-compose -f docker-compose.dean-complete.yml run --rm airflow-init

# Step 4: Create initial agent population
echo -e "\n4. Creating initial agent population..."
curl -X POST http://localhost:8082/api/v1/agents/spawn \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test-token" \
  -d '{
    "genome_template": "default",
    "population_size": 3,
    "token_budget": 1000
  }'

# Step 5: Trigger evolution DAG
echo -e "\n5. Triggering evolution DAG..."
curl -X POST http://localhost:8080/api/v1/dags/dean_agent_evolution/dagRuns \
  -H "Content-Type: application/json" \
  --user admin:admin \
  -d '{
    "conf": {
      "population_size": 3,
      "generations": 5,
      "token_budget": 5000
    }
  }'

# Step 6: Monitor evolution progress
echo -e "\n6. Monitoring evolution progress..."
for i in {1..10}; do
    echo -n "Check $i/10: "
    
    # Check agent count
    agent_count=$(curl -s http://localhost:8081/api/v1/agents | jq '.total_agents // 0')
    echo -n "Agents: $agent_count | "
    
    # Check patterns
    pattern_count=$(curl -s http://localhost:8091/api/v1/patterns | jq '.total_patterns // 0')
    echo "Patterns: $pattern_count"
    
    sleep 10
done

# Step 7: Verify results
echo -e "\n7. Verifying evolution results..."

# Check final agent population
echo "Final agent population:"
curl -s http://localhost:8081/api/v1/agents | jq '.'

# Check discovered patterns
echo -e "\nDiscovered patterns:"
curl -s http://localhost:8091/api/v1/patterns | jq '.'

# Check token usage
echo -e "\nToken usage statistics:"
curl -s http://localhost:8082/api/v1/metrics/tokens | jq '.'

# Step 8: Check logs for errors
echo -e "\n8. Checking logs for errors..."
docker-compose -f docker-compose.dean-complete.yml logs --tail=50 | grep -i error || echo "No errors found in recent logs"

echo -e "\n=== Evolution Cycle Validation Complete ==="
echo "Completed at: $(date)"

# Optional: Stop services
read -p "Stop all services? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker-compose -f docker-compose.dean-complete.yml down
fi