#!/bin/bash

# Quick Authentication Test Script
# Tests basic authentication flow with the DEAN orchestrator

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
ORCHESTRATOR_URL="${ORCHESTRATOR_URL:-http://localhost:8082}"
USERNAME="${1:-admin}"
PASSWORD="${2:-admin123}"

echo -e "${BLUE}DEAN Quick Authentication Test${NC}"
echo "================================"
echo "Testing with user: $USERNAME"
echo ""

# Function to extract JSON value
extract_json() {
    echo "$1" | grep -o "\"$2\":[^,}]*" | sed "s/\"$2\":\s*\"\([^\"]*\)\"/\1/"
}

# Step 1: Test login
echo -e "${YELLOW}1. Testing login...${NC}"
LOGIN_RESPONSE=$(curl -s -X POST "$ORCHESTRATOR_URL/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"username\": \"$USERNAME\", \"password\": \"$PASSWORD\"}" 2>/dev/null || echo "FAILED")

if [[ "$LOGIN_RESPONSE" == *"access_token"* ]]; then
    echo -e "${GREEN}✓ Login successful${NC}"
    
    # Extract tokens
    ACCESS_TOKEN=$(extract_json "$LOGIN_RESPONSE" "access_token")
    REFRESH_TOKEN=$(extract_json "$LOGIN_RESPONSE" "refresh_token")
    TOKEN_TYPE=$(extract_json "$LOGIN_RESPONSE" "token_type")
    EXPIRES_IN=$(extract_json "$LOGIN_RESPONSE" "expires_in")
    
    echo "  Token type: $TOKEN_TYPE"
    echo "  Expires in: $EXPIRES_IN seconds"
    echo "  Access token: ${ACCESS_TOKEN:0:20}..."
else
    echo -e "${RED}✗ Login failed${NC}"
    echo "Response: $LOGIN_RESPONSE"
    exit 1
fi

# Step 2: Test authenticated request
echo -e "\n${YELLOW}2. Testing authenticated API call...${NC}"
API_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    "$ORCHESTRATOR_URL/api/agents")

if [ "$API_RESPONSE" == "200" ]; then
    echo -e "${GREEN}✓ API call successful${NC}"
else
    echo -e "${RED}✗ API call failed (HTTP $API_RESPONSE)${NC}"
fi

# Step 3: Test unauthenticated request
echo -e "\n${YELLOW}3. Testing unauthenticated API call...${NC}"
UNAUTH_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$ORCHESTRATOR_URL/api/agents")

if [ "$UNAUTH_RESPONSE" == "401" ]; then
    echo -e "${GREEN}✓ Unauthenticated request correctly rejected${NC}"
else
    echo -e "${RED}✗ Security issue: Expected 401, got $UNAUTH_RESPONSE${NC}"
fi

# Step 4: Test token refresh
echo -e "\n${YELLOW}4. Testing token refresh...${NC}"
REFRESH_RESPONSE=$(curl -s -X POST "$ORCHESTRATOR_URL/auth/refresh" \
    -H "Content-Type: application/json" \
    -d "{\"refresh_token\": \"$REFRESH_TOKEN\"}" 2>/dev/null || echo "FAILED")

if [[ "$REFRESH_RESPONSE" == *"access_token"* ]]; then
    echo -e "${GREEN}✓ Token refresh successful${NC}"
    NEW_ACCESS_TOKEN=$(extract_json "$REFRESH_RESPONSE" "access_token")
    
    # Test new token
    NEW_TOKEN_TEST=$(curl -s -o /dev/null -w "%{http_code}" \
        -H "Authorization: Bearer $NEW_ACCESS_TOKEN" \
        "$ORCHESTRATOR_URL/api/agents")
    
    if [ "$NEW_TOKEN_TEST" == "200" ]; then
        echo -e "${GREEN}✓ New token is valid${NC}"
    else
        echo -e "${RED}✗ New token validation failed${NC}"
    fi
else
    echo -e "${RED}✗ Token refresh failed${NC}"
fi

# Step 5: Test service endpoints
echo -e "\n${YELLOW}5. Testing service authentication...${NC}"

# Test Evolution API
EVOLUTION_TEST=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    "http://localhost:8083/evolution/trials")

if [ "$EVOLUTION_TEST" == "200" ]; then
    echo -e "${GREEN}✓ Evolution API authentication working${NC}"
else
    echo -e "${YELLOW}⚠ Evolution API returned $EVOLUTION_TEST${NC}"
fi

# Test IndexAgent API
INDEXAGENT_TEST=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    "http://localhost:8081/agents")

if [ "$INDEXAGENT_TEST" == "200" ]; then
    echo -e "${GREEN}✓ IndexAgent API authentication working${NC}"
else
    echo -e "${YELLOW}⚠ IndexAgent API returned $INDEXAGENT_TEST${NC}"
fi

echo -e "\n${GREEN}Authentication test complete!${NC}"

# Output useful commands
echo -e "\n${BLUE}Useful commands:${NC}"
echo "# Test with different user:"
echo "  $0 user user123"
echo ""
echo "# Use token in curl:"
echo "  curl -H \"Authorization: Bearer $ACCESS_TOKEN\" $ORCHESTRATOR_URL/api/agents"
echo ""
echo "# Create API key:"
echo "  curl -X POST $ORCHESTRATOR_URL/api/keys \\"
echo "    -H \"Authorization: Bearer $ACCESS_TOKEN\" \\"
echo "    -H \"Content-Type: application/json\" \\"
echo "    -d '{\"name\": \"My API Key\", \"roles\": [\"user\"]}'"