#!/bin/bash
# DEAN Orchestration Test Runner Script
# Executes different test suites with appropriate configurations

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Change to project root
cd "$PROJECT_ROOT"

# Default values
TEST_TYPE="all"
COVERAGE=true
VERBOSE=false
MARKERS=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --unit)
            TEST_TYPE="unit"
            shift
            ;;
        --integration)
            TEST_TYPE="integration"
            shift
            ;;
        --no-coverage)
            COVERAGE=false
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --marker|-m)
            MARKERS="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --unit              Run unit tests only"
            echo "  --integration       Run integration tests only"
            echo "  --no-coverage       Skip coverage report"
            echo "  --verbose, -v       Verbose output"
            echo "  --marker, -m MARKER Run tests with specific marker"
            echo "  --help, -h          Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                  # Run all tests with coverage"
            echo "  $0 --unit           # Run unit tests only"
            echo "  $0 --integration    # Run integration tests only"
            echo "  $0 -m slow          # Run tests marked as slow"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Function to print colored output
print_status() {
    echo -e "${GREEN}==>${NC} $1"
}

print_error() {
    echo -e "${RED}ERROR:${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}WARNING:${NC} $1"
}

# Check if virtual environment is activated
if [[ -z "$VIRTUAL_ENV" ]]; then
    print_warning "Virtual environment not activated. Activating if available..."
    if [[ -f "venv/bin/activate" ]]; then
        source venv/bin/activate
    else
        print_error "Virtual environment not found. Please create one with 'python -m venv venv'"
        exit 1
    fi
fi

# Install test dependencies if needed
print_status "Checking test dependencies..."
pip install -q -e ".[test]" || {
    print_error "Failed to install test dependencies"
    exit 1
}

# Set test environment variables
export DEAN_TESTING=true
export USE_MOCK_SERVICES=true
export TEST_DATABASE_URL=sqlite:///:memory:

# Build pytest command
PYTEST_CMD="python -m pytest"

# Add verbose flag
if [[ "$VERBOSE" == true ]]; then
    PYTEST_CMD="$PYTEST_CMD -vv"
else
    PYTEST_CMD="$PYTEST_CMD -v"
fi

# Add coverage flags
if [[ "$COVERAGE" == true ]]; then
    PYTEST_CMD="$PYTEST_CMD --cov=src --cov-report=term-missing --cov-report=html"
fi

# Add test selection
case $TEST_TYPE in
    unit)
        print_status "Running unit tests..."
        PYTEST_CMD="$PYTEST_CMD tests/unit"
        if [[ -z "$MARKERS" ]]; then
            MARKERS="unit"
        fi
        ;;
    integration)
        print_status "Running integration tests..."
        PYTEST_CMD="$PYTEST_CMD tests/integration"
        if [[ -z "$MARKERS" ]]; then
            MARKERS="integration"
        fi
        ;;
    all)
        print_status "Running all tests..."
        PYTEST_CMD="$PYTEST_CMD tests"
        ;;
esac

# Add markers
if [[ -n "$MARKERS" ]]; then
    PYTEST_CMD="$PYTEST_CMD -m '$MARKERS'"
fi

# Create test results directory
mkdir -p test-results

# Run tests
print_status "Executing: $PYTEST_CMD"
echo ""

# Execute tests and capture exit code
if eval $PYTEST_CMD; then
    echo ""
    print_status "All tests passed! ✅"
    
    if [[ "$COVERAGE" == true ]]; then
        print_status "Coverage report generated at: htmlcov/index.html"
    fi
else
    EXIT_CODE=$?
    echo ""
    print_error "Some tests failed! ❌"
    exit $EXIT_CODE
fi

# Run type checking if unit tests passed
if [[ "$TEST_TYPE" == "unit" ]] || [[ "$TEST_TYPE" == "all" ]]; then
    print_status "Running type checking..."
    if python -m mypy src --ignore-missing-imports; then
        print_status "Type checking passed! ✅"
    else
        print_warning "Type checking failed - non-critical"
    fi
fi

echo ""
print_status "Test run completed successfully!"