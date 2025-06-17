#!/bin/bash

# DEAN Full Workflow Demonstration Script
# This script demonstrates the complete DEAN system workflow with explanatory output

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
ORCHESTRATOR_URL="http://localhost:8082"
EVOLUTION_URL="http://localhost:8083"
INDEXAGENT_URL="http://localhost:8081"

# Demo settings
DEMO_USER="admin"
DEMO_PASS="admin123"
PAUSE_TIME=2

# Function to print section headers
print_section() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

# Function to print explanations
explain() {
    echo -e "${CYAN}ℹ️  $1${NC}"
    sleep $PAUSE_TIME
}

# Function to print commands
show_command() {
    echo -e "${YELLOW}$ $1${NC}"
    sleep 1
}

# Function to extract JSON value
extract_json() {
    echo "$1" | grep -o "\"$2\":[^,}]*" | sed "s/\"$2\":\s*\"\([^\"]*\)\"/\1/"
}

# Start demonstration
clear
echo -e "${GREEN}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║          DEAN Orchestration System - Full Demo               ║"
echo "║                                                              ║"
echo "║  Distributed Evolutionary Agent Network in Action            ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"
sleep 3

print_section "STEP 1: System Health Check"
explain "First, let's verify all DEAN services are running properly."

show_command "curl -s http://localhost:8082/health | jq ."
HEALTH=$(curl -s $ORCHESTRATOR_URL/health)
echo "$HEALTH" | python3 -m json.tool
echo -e "${GREEN}✓ Orchestrator is healthy${NC}"

sleep $PAUSE_TIME

print_section "STEP 2: User Authentication"
explain "Now we'll authenticate as an admin user to get access tokens."
explain "DEAN uses JWT tokens for secure API access."

show_command "curl -X POST http://localhost:8082/auth/login -d '{\"username\": \"admin\", \"password\": \"admin123\"}'"

LOGIN_RESPONSE=$(curl -s -X POST $ORCHESTRATOR_URL/auth/login \
    -H "Content-Type: application/json" \
    -d "{\"username\": \"$DEMO_USER\", \"password\": \"$DEMO_PASS\"}")

echo "$LOGIN_RESPONSE" | python3 -m json.tool

ACCESS_TOKEN=$(extract_json "$LOGIN_RESPONSE" "access_token")
REFRESH_TOKEN=$(extract_json "$LOGIN_RESPONSE" "refresh_token")

echo -e "\n${GREEN}✓ Login successful!${NC}"
echo -e "Access token: ${ACCESS_TOKEN:0:30}..."
sleep $PAUSE_TIME

print_section "STEP 3: Create Evolution Agents"
explain "Let's create some agents that will participate in evolution."
explain "Each agent has specific capabilities and a fitness score."

show_command "curl -X POST http://localhost:8081/agents -H 'Authorization: Bearer \$TOKEN' -d '{...}'"

# Create first agent
AGENT1=$(curl -s -X POST $INDEXAGENT_URL/agents \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
        "name": "search-optimizer-v1",
        "language": "python",
        "capabilities": ["search", "optimize", "analyze"],
        "parameters": {"learning_rate": 0.01}
    }')

echo "Created Agent 1:"
echo "$AGENT1" | python3 -m json.tool
AGENT1_ID=$(extract_json "$AGENT1" "id")

sleep $PAUSE_TIME

# Create second agent
AGENT2=$(curl -s -X POST $INDEXAGENT_URL/agents \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
        "name": "pattern-detector-v1",
        "language": "python",
        "capabilities": ["pattern", "analyze", "evolve"],
        "parameters": {"sensitivity": 0.8}
    }')

echo -e "\nCreated Agent 2:"
echo "$AGENT2" | python3 -m json.tool
AGENT2_ID=$(extract_json "$AGENT2" "id")

echo -e "\n${GREEN}✓ Agents created successfully${NC}"
sleep $PAUSE_TIME

print_section "STEP 4: Start Evolution Trial"
explain "Now we'll start an evolution trial where agents compete and evolve."
explain "The system will run multiple generations, improving agent fitness."

show_command "curl -X POST http://localhost:8083/evolution/start -H 'Authorization: Bearer \$TOKEN' -d '{...}'"

TRIAL_RESPONSE=$(curl -s -X POST $EVOLUTION_URL/evolution/start \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
        "repository": "demo-repository",
        "generations": 5,
        "population_size": 10,
        "mutation_rate": 0.15,
        "crossover_rate": 0.7,
        "fitness_threshold": 0.95,
        "max_runtime_minutes": 10,
        "parameters": {
            "objective": "optimize_performance",
            "constraints": ["memory_limit", "execution_time"]
        }
    }')

echo "$TRIAL_RESPONSE" | python3 -m json.tool
TRIAL_ID=$(extract_json "$TRIAL_RESPONSE" "trial_id")

echo -e "\n${GREEN}✓ Evolution trial started!${NC}"
echo -e "Trial ID: $TRIAL_ID"
sleep $PAUSE_TIME

print_section "STEP 5: Monitor Evolution Progress"
explain "Let's monitor the evolution trial in real-time."
explain "Watch as the fitness improves over generations!"

echo -e "\n${YELLOW}Monitoring evolution progress...${NC}\n"

# Monitor for 20 seconds
for i in {1..10}; do
    STATUS=$(curl -s -X GET $EVOLUTION_URL/evolution/$TRIAL_ID/status \
        -H "Authorization: Bearer $ACCESS_TOKEN")
    
    CURRENT_GEN=$(extract_json "$STATUS" "current_generation")
    BEST_FITNESS=$(extract_json "$STATUS" "best_fitness")
    PATTERNS=$(extract_json "$STATUS" "patterns_discovered")
    STATUS_VAL=$(extract_json "$STATUS" "status")
    
    # Create progress bar
    PROGRESS=$((CURRENT_GEN * 20))
    printf "\r["
    printf "%0.s█" $(seq 1 $((PROGRESS / 5)))
    printf "%0.s " $(seq 1 $((20 - PROGRESS / 5)))
    printf "] Generation %d/5 | Fitness: %.3f | Patterns: %d" \
        "$CURRENT_GEN" "$BEST_FITNESS" "$PATTERNS"
    
    if [ "$STATUS_VAL" = "completed" ]; then
        echo -e "\n\n${GREEN}✓ Evolution completed!${NC}"
        break
    fi
    
    sleep 2
done

sleep $PAUSE_TIME

print_section "STEP 6: Discover Patterns"
explain "Evolution trials discover patterns that can improve agent performance."
explain "Let's see what patterns were discovered."

show_command "curl -X GET 'http://localhost:8083/patterns?min_confidence=0.8' -H 'Authorization: Bearer \$TOKEN'"

PATTERNS=$(curl -s -X GET "$EVOLUTION_URL/patterns?min_confidence=0.8&limit=5" \
    -H "Authorization: Bearer $ACCESS_TOKEN")

echo "$PATTERNS" | python3 -m json.tool

PATTERN_COUNT=$(echo "$PATTERNS" | python3 -c "import sys, json; print(len(json.load(sys.stdin)['patterns']))")
echo -e "\n${GREEN}✓ Found $PATTERN_COUNT high-confidence patterns${NC}"
sleep $PAUSE_TIME

print_section "STEP 7: View System Metrics"
explain "Finally, let's check the overall system metrics."

show_command "curl -X GET http://localhost:8083/evolution/metrics -H 'Authorization: Bearer \$TOKEN'"

METRICS=$(curl -s -X GET $EVOLUTION_URL/evolution/metrics \
    -H "Authorization: Bearer $ACCESS_TOKEN")

echo "$METRICS" | python3 -m json.tool

echo -e "\n${GREEN}✓ System metrics retrieved${NC}"
sleep $PAUSE_TIME

print_section "DEMO COMPLETE!"

echo -e "${GREEN}"
echo "What we accomplished:"
echo "  ✅ Authenticated with the DEAN system"
echo "  ✅ Created intelligent agents with specific capabilities"
echo "  ✅ Started an evolution trial to improve agent performance"
echo "  ✅ Monitored real-time evolution progress"
echo "  ✅ Discovered optimization patterns"
echo "  ✅ Retrieved system metrics"
echo -e "${NC}"

echo -e "\n${CYAN}The DEAN system successfully demonstrated:"
echo "  • Secure authentication with JWT tokens"
echo "  • Agent creation and management"
echo "  • Evolutionary optimization processes"
echo "  • Pattern discovery and learning"
echo "  • Real-time monitoring capabilities"
echo -e "${NC}"

echo -e "\n${YELLOW}Next steps:"
echo "  1. View the dashboard at http://localhost:8082"
echo "  2. Try creating your own agents and evolution trials"
echo "  3. Explore the discovered patterns"
echo "  4. Monitor system performance"
echo -e "${NC}"

echo -e "\n${BLUE}Thank you for exploring DEAN!${NC}"
echo ""

# Save demo results
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DEMO_RESULTS="demo_results_${TIMESTAMP}.json"

cat > "$DEMO_RESULTS" << EOF
{
  "demo_timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "authentication": {
    "user": "$DEMO_USER",
    "token_obtained": true
  },
  "agents_created": ["$AGENT1_ID", "$AGENT2_ID"],
  "evolution_trial": {
    "trial_id": "$TRIAL_ID",
    "generations": 5,
    "final_status": "$STATUS_VAL"
  },
  "patterns_discovered": $PATTERN_COUNT,
  "demo_duration_seconds": $SECONDS
}
EOF

echo -e "${CYAN}Demo results saved to: $DEMO_RESULTS${NC}"