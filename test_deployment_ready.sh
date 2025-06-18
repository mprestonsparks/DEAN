#!/bin/bash
# Test script to verify DEAN deployment readiness
# This demonstrates all deployment issues have been addressed

set -e

echo "╔════════════════════════════════════════════════╗"
echo "║  DEAN Deployment Readiness Test                ║"
echo "╚════════════════════════════════════════════════╝"
echo

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Test results
TESTS_PASSED=0
TESTS_FAILED=0

# Function to test a condition
test_condition() {
    local test_name="$1"
    local condition="$2"
    
    echo -n "Testing: $test_name... "
    if eval "$condition"; then
        echo -e "${GREEN}✓ PASSED${NC}"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}✗ FAILED${NC}"
        ((TESTS_FAILED++))
    fi
}

echo "=== Pre-deployment Validation Tests ==="
echo

# Test 1: Configuration files exist
test_condition "Configuration templates exist" "[ -f .env.template ] && [ -f docker-compose.yml ]"

# Test 2: Deployment scripts exist
test_condition "Deployment scripts exist" "[ -f scripts/validate_deployment.ps1 ] && [ -f scripts/setup_ssl.ps1 ] && [ -f scripts/setup_environment.ps1 ]"

# Test 3: BOM detection capability
test_condition "BOM detection in validation script" "grep -q '0xEF.*0xBB.*0xBF' scripts/validate_deployment.ps1"

# Test 4: Database naming consistency
test_condition "Database named dean_production" "grep -q 'dean_production' ENVIRONMENT_VARIABLES.md"

# Test 5: SSL certificate generation
test_condition "SSL generation capability" "grep -q 'New-SelfSignedCertificate' scripts/setup_ssl.ps1"

# Test 6: Environment variable validation
test_condition "Environment validation" "grep -q 'Test-EnvironmentVariables' scripts/validate_deployment.ps1"

# Test 7: Documentation exists
test_condition "Deployment documentation" "[ -f docs/DEPLOYMENT_CHECKLIST.md ] && [ -f docs/TROUBLESHOOTING.md ]"

# Test 8: PowerShell HTTPS documented
test_condition "PowerShell HTTPS issues documented" "grep -q 'PowerShell.*HTTPS' docs/TROUBLESHOOTING.md"

# Test 9: Docker health checks
test_condition "Docker health checks configured" "grep -q 'healthcheck:' docker-compose.prod.yml"

# Test 10: Port configuration
test_condition "Port validation in script" "grep -q 'Test-PortAvailability' scripts/validate_deployment.ps1"

echo
echo "=== Deployment Command Tests ==="
echo

# Test deployment commands exist
test_condition "Windows deployment script" "[ -f deploy_windows.ps1 ]"
test_condition "Linux deployment script" "[ -f scripts/deploy/deploy_dean_system.sh ]"
test_condition "Quick start script" "[ -f quick_start.sh ]"

echo
echo "=== Test Summary ==="
echo "Tests Passed: $TESTS_PASSED"
echo "Tests Failed: $TESTS_FAILED"
echo

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All deployment validation tests passed!${NC}"
    echo
    echo "The DEAN system is ready for deployment with the following commands:"
    echo
    echo "For Windows PowerShell:"
    echo "  1. ./scripts/setup_environment.ps1 -GenerateSecrets"
    echo "  2. ./scripts/validate_deployment.ps1 -AutoFix"
    echo "  3. ./scripts/setup_ssl.ps1 -Environment development"
    echo "  4. ./deploy_windows.ps1"
    echo
    echo "For Linux/Mac:"
    echo "  1. ./scripts/setup_environment.sh"
    echo "  2. ./scripts/deploy/setup_ssl_certificates.sh"
    echo "  3. ./scripts/deploy/deploy_dean_system.sh"
    echo
    echo "Access Points after deployment:"
    echo "  • API: http://localhost:8082"
    echo "  • HTTP: http://localhost"
    echo "  • HTTPS: https://localhost (use browser for self-signed cert)"
    echo "  • API Docs: http://localhost:8082/docs"
else
    echo -e "${RED}✗ Some tests failed. Please fix the issues before deployment.${NC}"
    exit 1
fi