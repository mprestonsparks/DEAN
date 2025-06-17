#!/bin/bash

# DEAN Final Deployment Verification Script
# Comprehensive verification before production deployment

set -e

# Configuration
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DEAN_ROOT="$(dirname "$SCRIPT_DIR")"
REPORT_FILE="$DEAN_ROOT/deployment_verification_$(date +%Y%m%d_%H%M%S).txt"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Counters
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0
WARNING_CHECKS=0

# Start report
exec > >(tee -a "$REPORT_FILE")
exec 2>&1

echo "================================================"
echo "DEAN Final Deployment Verification"
echo "================================================"
echo "Date: $(date)"
echo "System: $(uname -a)"
echo "DEAN Root: $DEAN_ROOT"
echo ""

# Function to run a check
run_check() {
    local check_name="$1"
    local check_command="$2"
    local check_type="${3:-critical}"  # critical or warning
    
    ((TOTAL_CHECKS++))
    echo -n "Checking: $check_name... "
    
    if eval "$check_command" > /dev/null 2>&1; then
        echo -e "${GREEN}PASSED${NC}"
        ((PASSED_CHECKS++))
        return 0
    else
        if [ "$check_type" = "warning" ]; then
            echo -e "${YELLOW}WARNING${NC}"
            ((WARNING_CHECKS++))
            return 1
        else
            echo -e "${RED}FAILED${NC}"
            ((FAILED_CHECKS++))
            return 1
        fi
    fi
}

# Function to check file exists
check_file() {
    local file="$1"
    local type="${2:-critical}"
    run_check "File exists: $file" "[ -f '$DEAN_ROOT/$file' ]" "$type"
}

# Function to check directory exists
check_dir() {
    local dir="$1"
    local type="${2:-critical}"
    run_check "Directory exists: $dir" "[ -d '$DEAN_ROOT/$dir' ]" "$type"
}

# Function to check command exists
check_command() {
    local cmd="$1"
    run_check "Command available: $cmd" "command -v $cmd" "critical"
}

echo -e "${BLUE}1. File Structure Verification${NC}"
echo "=============================="

# Critical files
check_file "docker-compose.prod.yml"
check_file "docker-compose.dev.yml"
check_file ".env.production.template"
check_file "requirements.txt"
check_file "README.md"
check_file "Makefile"
check_file "install.sh"

# Critical directories
check_dir "src"
check_dir "scripts"
check_dir "configs"
check_dir "docs"
check_dir "tests"
check_dir "service_stubs"
check_dir "migrations"

# Documentation files
check_file "docs/QUICK_START.md"
check_file "docs/PRODUCTION_DEPLOYMENT.md"
check_file "docs/OPERATIONS_RUNBOOK.md"
check_file "docs/SECURITY_GUIDE.md"
check_file "docs/api/openapi.yaml"

echo ""
echo -e "${BLUE}2. Configuration Validity${NC}"
echo "========================"

# Check if .env exists (warning only as it needs to be created)
check_file ".env" "warning"

# Validate docker-compose syntax
run_check "Docker Compose syntax (prod)" "docker compose -f docker-compose.prod.yml config"
run_check "Docker Compose syntax (dev)" "docker compose -f docker-compose.dev.yml config"

# Check for sensitive data in tracked files
run_check "No passwords in tracked files" "! grep -r 'password.*=' --include='*.py' --include='*.yml' --include='*.yaml' --exclude-dir='.git' --exclude='*template*' . | grep -v -E '(example|template|dummy|test)'"

echo ""
echo -e "${BLUE}3. Script Verification${NC}"
echo "====================="

# Check script permissions
SCRIPTS=(
    "scripts/dev_environment.sh"
    "scripts/stop_dev_environment.sh"
    "scripts/health_check.sh"
    "scripts/deployment_commands.sh"
    "scripts/optimize_for_hardware.sh"
    "scripts/production_hardening.sh"
    "scripts/package_release.sh"
    "scripts/final_validation.sh"
)

for script in "${SCRIPTS[@]}"; do
    run_check "Script executable: $script" "[ -x '$DEAN_ROOT/$script' ]"
done

echo ""
echo -e "${BLUE}4. Security Configuration${NC}"
echo "========================"

# Check for default passwords in templates
run_check "No default passwords in templates" "! grep -E '(admin123|password123|changeme)' $DEAN_ROOT/.env.production.template 2>/dev/null"

# Check certificate directory
check_dir "certs"

# Check security scripts
check_file "scripts/security_audit.py"
check_file "scripts/production_hardening.sh"

echo ""
echo -e "${BLUE}5. Backup Configuration${NC}"
echo "======================="

check_file "scripts/utilities/backup_restore.sh" "warning"
check_dir "backups" "warning"

echo ""
echo -e "${BLUE}6. Hardware Configuration${NC}"
echo "========================"

check_file "configs/hardware/i7_rtx3080.yaml"
check_file "scripts/optimize_for_hardware.sh"

echo ""
echo -e "${BLUE}7. Dependencies Check${NC}"
echo "===================="

check_command "docker"
check_command "docker-compose"
check_command "python3"
check_command "pip3"
check_command "git"
check_command "make"
check_command "openssl"

echo ""
echo -e "${BLUE}8. Python Requirements${NC}"
echo "====================="

# Check if requirements files exist
check_file "requirements.txt"
check_file "requirements/base.txt" "warning"
check_file "requirements/production.txt" "warning"

echo ""
echo -e "${BLUE}9. Service Stubs${NC}"
echo "==============="

check_file "service_stubs/docker-compose.stubs.yml"
check_dir "service_stubs/evolution"
check_dir "service_stubs/indexagent"
check_dir "service_stubs/airflow"

echo ""
echo -e "${BLUE}10. Deployment Support Files${NC}"
echo "==========================="

check_file "DEPLOYMENT_READINESS_CHECKLIST.md"
check_file "HANDOVER_DOCUMENT.md"
check_file "DEPLOYMENT_SUCCESS_CRITERIA.md" "warning"
check_file "PROJECT_SUMMARY.md"

echo ""
echo -e "${BLUE}11. Release Package${NC}"
echo "=================="

# Check if release directory exists and contains packages
if [ -d "$DEAN_ROOT/releases" ]; then
    RELEASE_COUNT=$(ls -1 "$DEAN_ROOT/releases"/*.tar.gz 2>/dev/null | wc -l)
    if [ $RELEASE_COUNT -gt 0 ]; then
        echo -e "${GREEN}✓ Found $RELEASE_COUNT release package(s)${NC}"
        ls -la "$DEAN_ROOT/releases"/*.tar.gz | tail -5
        ((PASSED_CHECKS++))
        ((TOTAL_CHECKS++))
    else
        echo -e "${YELLOW}⚠ No release packages found${NC}"
        ((WARNING_CHECKS++))
        ((TOTAL_CHECKS++))
    fi
else
    echo -e "${YELLOW}⚠ Release directory not found${NC}"
    ((WARNING_CHECKS++))
    ((TOTAL_CHECKS++))
fi

echo ""
echo -e "${BLUE}12. API Documentation${NC}"
echo "===================="

check_file "docs/api/openapi.yaml"
check_file "docs/api/API_EXAMPLES.md"

echo ""
echo "================================================"
echo "Verification Summary"
echo "================================================"
echo -e "Total Checks: $TOTAL_CHECKS"
echo -e "Passed: ${GREEN}$PASSED_CHECKS${NC}"
echo -e "Warnings: ${YELLOW}$WARNING_CHECKS${NC}"
echo -e "Failed: ${RED}$FAILED_CHECKS${NC}"
echo ""

# Calculate readiness percentage
READINESS=$((PASSED_CHECKS * 100 / TOTAL_CHECKS))
echo "Deployment Readiness: ${READINESS}%"
echo ""

# Generate deployment package list
echo -e "${BLUE}Deployment Package Contents${NC}"
echo "=========================="
echo "The following should be included in deployment:"
echo ""
echo "Core System:"
echo "  - src/           (Application source code)"
echo "  - configs/       (Configuration files)"
echo "  - scripts/       (Operational scripts)"
echo "  - migrations/    (Database migrations)"
echo "  - requirements/  (Python dependencies)"
echo ""
echo "Docker Configuration:"
echo "  - docker-compose.prod.yml"
echo "  - service_stubs/"
echo "  - Dockerfile files"
echo ""
echo "Documentation:"
echo "  - docs/          (All documentation)"
echo "  - README.md"
echo "  - HANDOVER_DOCUMENT.md"
echo ""
echo "Deployment Support:"
echo "  - install.sh"
echo "  - .env.production.template"
echo "  - configs/hardware/"
echo ""

# Final verdict
echo "================================================"
echo "Final Verdict"
echo "================================================"

if [ $FAILED_CHECKS -eq 0 ] && [ $READINESS -ge 95 ]; then
    echo -e "${GREEN}✅ SYSTEM IS READY FOR DEPLOYMENT${NC}"
    echo ""
    echo "All critical checks passed. The system can be deployed to production."
    echo "Address any warnings before or shortly after deployment."
    EXIT_CODE=0
elif [ $FAILED_CHECKS -eq 0 ] && [ $READINESS -ge 90 ]; then
    echo -e "${YELLOW}⚠️  SYSTEM IS READY WITH WARNINGS${NC}"
    echo ""
    echo "No critical failures, but several warnings should be addressed."
    echo "Review warnings and ensure they won't impact production."
    EXIT_CODE=0
else
    echo -e "${RED}❌ SYSTEM NOT READY FOR DEPLOYMENT${NC}"
    echo ""
    echo "Critical checks failed. Address all failures before deployment."
    echo "Review the detailed report above for specific issues."
    EXIT_CODE=1
fi

echo ""
echo "Detailed report saved to: $REPORT_FILE"
echo ""

# Generate quick fix commands for common issues
if [ $FAILED_CHECKS -gt 0 ] || [ $WARNING_CHECKS -gt 0 ]; then
    echo -e "${BLUE}Quick Fixes${NC}"
    echo "==========="
    
    if ! [ -f "$DEAN_ROOT/.env" ]; then
        echo "Create .env file:"
        echo "  cp .env.production.template .env"
        echo "  # Edit .env with your configuration"
    fi
    
    if ! [ -d "$DEAN_ROOT/backups" ]; then
        echo "Create backup directory:"
        echo "  mkdir -p $DEAN_ROOT/backups"
    fi
    
    if ! [ -d "$DEAN_ROOT/certs" ]; then
        echo "Create certificate directory:"
        echo "  mkdir -p $DEAN_ROOT/certs"
    fi
    
    echo ""
fi

exit $EXIT_CODE