#!/bin/bash
# Test GitHub Actions workflows locally using Act
# This helps catch issues before pushing to GitHub

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 GitHub Actions Local Testing with Act${NC}"
echo "========================================"

# Check if Act is installed
if ! command -v act &> /dev/null; then
    echo -e "${RED}❌ Act is not installed${NC}"
    echo ""
    echo "Please install Act first:"
    echo "  macOS:    brew install act"
    echo "  Linux:    curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash"
    echo "  Windows:  choco install act-cli"
    echo ""
    echo "Or download from: https://github.com/nektos/act/releases"
    exit 1
fi

echo -e "${GREEN}✓ Act is installed:${NC} $(act --version)"

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo -e "${RED}❌ Docker is not running${NC}"
    echo "Please start Docker Desktop or Docker daemon"
    exit 1
fi

echo -e "${GREEN}✓ Docker is running${NC}"

# Function to run specific workflow
run_workflow() {
    local workflow=$1
    local job=$2
    
    if [ -z "$job" ]; then
        echo -e "\n${YELLOW}Running workflow: $workflow${NC}"
        act -W ".github/workflows/$workflow"
    else
        echo -e "\n${YELLOW}Running job '$job' from workflow: $workflow${NC}"
        act -W ".github/workflows/$workflow" -j "$job"
    fi
}

# Function to run with specific event
run_event() {
    local event=$1
    echo -e "\n${YELLOW}Running workflows for event: $event${NC}"
    act "$event"
}

# Parse command line arguments
case "${1:-help}" in
    "all")
        echo -e "\n${YELLOW}Running all workflows...${NC}"
        act
        ;;
    
    "list")
        echo -e "\n${YELLOW}Available workflows and jobs:${NC}"
        act -l
        ;;
    
    "push")
        run_event "push"
        ;;
    
    "pr")
        run_event "pull_request"
        ;;
    
    "validate")
        run_workflow "configuration-validation.yml" "validate-config"
        ;;
    
    "workflow")
        if [ -z "$2" ]; then
            echo -e "${RED}Please specify workflow file${NC}"
            echo "Usage: $0 workflow <workflow-file> [job-name]"
            exit 1
        fi
        run_workflow "$2" "$3"
        ;;
    
    "dry-run")
        echo -e "\n${YELLOW}Dry run - showing what would be executed:${NC}"
        act -n
        ;;
    
    "graph")
        echo -e "\n${YELLOW}Workflow dependency graph:${NC}"
        act -g
        ;;
    
    "clean")
        echo -e "\n${YELLOW}Cleaning up Act artifacts and containers...${NC}"
        docker container prune -f
        rm -rf /tmp/act-artifacts
        echo -e "${GREEN}✓ Cleanup complete${NC}"
        ;;
    
    "shell")
        echo -e "\n${YELLOW}Starting interactive shell in Act container...${NC}"
        act -b
        ;;
    
    "help"|*)
        echo ""
        echo "Usage: $0 [command] [options]"
        echo ""
        echo "Commands:"
        echo "  all        - Run all workflows"
        echo "  list       - List all workflows and jobs"
        echo "  push       - Run workflows triggered by push event"
        echo "  pr         - Run workflows triggered by pull_request event"
        echo "  validate   - Run configuration validation workflow"
        echo "  workflow   - Run specific workflow file"
        echo "  dry-run    - Show what would be executed without running"
        echo "  graph      - Show workflow dependency graph"
        echo "  clean      - Clean up artifacts and containers"
        echo "  shell      - Start interactive shell in Act container"
        echo "  help       - Show this help message"
        echo ""
        echo "Examples:"
        echo "  $0 push                          # Test push event workflows"
        echo "  $0 validate                      # Test configuration validation"
        echo "  $0 workflow my-workflow.yml      # Run specific workflow"
        echo "  $0 workflow my-workflow.yml test # Run specific job in workflow"
        echo ""
        echo "Tips:"
        echo "  - Use 'act -l' to see all available workflows"
        echo "  - Add '--verbose' flag for detailed output"
        echo "  - Use '--reuse' to speed up repeated runs"
        echo "  - Check .actrc for default configuration"
        ;;
esac