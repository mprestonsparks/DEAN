# DEAN Orchestration Test Specification

**Version**: 1.0.0  
**Last Updated**: June 13, 2025  
**Based On**: TESTING_PARADIGM.md and test files from dean-agent-workspace

## Overview

This document specifies the testing requirements and strategies for the DEAN orchestration layer, ensuring quality and reliability without modifying external repositories.

## Testing Philosophy

Based on the DEAN TESTING_PARADIGM.md:
1. **Comprehensive Coverage**: Every component must be tested
2. **Isolation**: Tests must not depend on external services being running
3. **Repeatability**: Tests must produce consistent results
4. **Performance**: Tests must complete quickly
5. **Clarity**: Test failures must clearly indicate the problem

## Test Categories

### Unit Tests

**Purpose**: Test individual components in isolation

**Scope**:
- Service client methods
- Orchestration logic
- Configuration parsing
- Utility functions

**Location**: `tests/unit/`

**Naming Convention**: `test_{component}_{functionality}.py`

**Example Structure**:
```python
class TestIndexAgentClient:
    def test_create_agent_success(self, mock_client):
        """Test successful agent creation."""
        
    def test_create_agent_timeout(self, mock_client):
        """Test agent creation with timeout."""
        
    def test_create_agent_invalid_config(self, mock_client):
        """Test agent creation with invalid configuration."""
```

### Integration Tests

**Purpose**: Test interaction between components and external services

**Scope**:
- Service client integration
- Workflow execution
- Database operations
- Cache operations

**Location**: `tests/integration/`

**Requirements**:
- Use mock services by default
- Optional real service testing with environment flag
- Transaction rollback for database tests

### End-to-End Tests

**Purpose**: Test complete user workflows

**Scope**:
- CLI command execution
- Web dashboard interactions
- Complete evolution trials
- Deployment procedures

**Location**: `tests/e2e/`

**Note**: E2E test requirements for distributed deployment have not been defined and require stakeholder input.

### Performance Tests

**Purpose**: Validate performance requirements

**Scope**:
- API response times
- Concurrent request handling
- Memory usage
- Database query performance

**Location**: `tests/performance/`

**Benchmarks** (from requirements):
- API response: 95th percentile < 500ms
- Concurrent requests: 100+
- Memory usage: < 4GB
- CPU usage: < 80%

### Contract Tests

**Purpose**: Ensure API compatibility with external services

**Scope**:
- Service API contracts
- Response format validation
- Error handling consistency

**Location**: `tests/contracts/`

## Test Implementation Standards

### Mock Service Specifications

**Mock IndexAgent Service**:
```python
class MockIndexAgentService:
    """Mock implementation of IndexAgent API."""
    
    def __init__(self, port=8081):
        self.agents = {}
        self.evolution_metrics = []
        
    async def create_agent(self, config):
        # Simulate agent creation
        
    async def get_agent(self, agent_id):
        # Return mock agent data
        
    async def search_code(self, query):
        # Return mock search results
```

**Mock Airflow Service**:
```python
class MockAirflowService:
    """Mock implementation of Airflow API."""
    
    def __init__(self, port=8080):
        self.dags = {}
        self.dag_runs = {}
        
    async def trigger_dag(self, dag_id, conf):
        # Simulate DAG trigger
        
    async def get_dag_run_status(self, dag_id, run_id):
        # Return mock status
```

**Mock Evolution API Service**:
```python
class MockEvolutionAPIService:
    """Mock implementation of Evolution API."""
    
    def __init__(self, port=8090):
        self.trials = {}
        self.patterns = []
        
    async def start_evolution(self, config):
        # Simulate evolution start
        
    async def get_patterns(self):
        # Return mock patterns
```

### Test Data Management

**Fixtures**:
```python
@pytest.fixture
def sample_agent_config():
    return {
        "name": "test_agent",
        "type": "optimization",
        "parameters": {
            "target": "performance",
            "constraints": {"max_tokens": 1000}
        }
    }

@pytest.fixture
def sample_evolution_config():
    return {
        "generations": 5,
        "population_size": 10,
        "mutation_rate": 0.1
    }
```

**Test Database**:
- Use SQLite for unit tests
- Use PostgreSQL for integration tests
- Automatic schema creation and teardown
- Seed data for predictable testing

### Error Testing Requirements

Each component must test:
1. **Success cases**: Normal operation
2. **Failure cases**: Expected errors
3. **Edge cases**: Boundary conditions
4. **Timeout cases**: Network delays
5. **Invalid input**: Malformed data
6. **Resource exhaustion**: Memory/connection limits

### Async Testing

**Patterns for async code**:
```python
@pytest.mark.asyncio
async def test_async_operation():
    client = ServiceClient()
    result = await client.async_method()
    assert result is not None

@pytest.mark.asyncio
async def test_concurrent_operations():
    tasks = [client.async_method() for _ in range(10)]
    results = await asyncio.gather(*tasks)
    assert len(results) == 10
```

## Test Execution

### Local Development

```bash
# Run all tests
make test

# Run unit tests only
make test-unit

# Run integration tests
make test-integration

# Run with coverage
pytest --cov=dean_orchestration --cov-report=html

# Run specific test file
pytest tests/unit/test_indexagent_client.py

# Run with verbose output
pytest -vv

# Run with specific marker
pytest -m "not slow"
```

### Continuous Integration

**GitHub Actions Workflow**:
```yaml
test:
  runs-on: ubuntu-latest
  strategy:
    matrix:
      python-version: [3.10, 3.11]
  steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
    - name: Install dependencies
      run: make install-dev
    - name: Run tests
      run: make test
    - name: Upload coverage
      uses: codecov/codecov-action@v3
```

### Test Environment Configuration

**Environment Variables**:
```bash
# Test configuration
TEST_ENV=true
TEST_DATABASE_URL=sqlite:///:memory:
TEST_REDIS_URL=redis://localhost:6379/15

# Service mocking
USE_MOCK_SERVICES=true
MOCK_SERVICE_DELAY=0

# Performance testing
PERF_TEST_ITERATIONS=1000
PERF_TEST_CONCURRENCY=50
```

## Test Coverage Requirements

Based on pyproject.toml configuration:
- **Minimum Coverage**: 80%
- **Critical Path Coverage**: 95%
- **Branch Coverage**: Required
- **Exclusions**: Test files, migrations

**Coverage by Component**:
- Service Clients: 90%
- Orchestration Core: 95%
- User Interfaces: 80%
- Utilities: 85%

## Test Data Security

1. **No Production Data**: Never use real production data
2. **Sanitized Data**: Use anonymized test data
3. **Credentials**: Use test-specific credentials
4. **Cleanup**: Ensure all test data is cleaned up

## Test Reporting

### Local Reports
- Console output with pytest
- HTML coverage reports
- Performance benchmark results

### CI/CD Reports
- JUnit XML for test results
- Coverage reports to Codecov
- Performance regression detection

## Testing Anti-Patterns to Avoid

Based on lessons from dean-agent-workspace:

1. **No Sleep Statements**: Use proper wait conditions
2. **No Hard-Coded Ports**: Use dynamic port allocation
3. **No External Dependencies**: Mock all external services
4. **No Shared State**: Each test must be independent
5. **No Real API Calls**: Use mocks or test environments

## Regression Testing

**Automated Regression Suite**:
1. All previously found bugs must have tests
2. Performance benchmarks tracked over time
3. API compatibility tests for each version
4. Integration tests for critical workflows

## Load Testing

**Tools**: locust, pytest-benchmark

**Scenarios**:
1. Normal load: 10 concurrent users
2. Peak load: 100 concurrent users
3. Stress test: 500 concurrent users
4. Endurance test: 24 hours continuous

**Note**: Specific load testing requirements have not been defined and require stakeholder input.

## Security Testing

**Note**: Security testing requirements have not been defined and require stakeholder input.

**Planned Security Tests**:
1. Authentication bypass attempts
2. SQL injection testing
3. API rate limiting validation
4. Input validation testing

## Test Maintenance

1. **Regular Review**: Monthly test review
2. **Flaky Test Policy**: Fix or remove within 1 week
3. **Test Refactoring**: Keep tests DRY
4. **Documentation**: Update test docs with code

## Future Testing Considerations

1. **Mutation Testing**: Validate test effectiveness
2. **Property-Based Testing**: Hypothesis framework
3. **Chaos Engineering**: Failure injection
4. **Visual Regression**: Dashboard testing
5. **Accessibility Testing**: WCAG compliance