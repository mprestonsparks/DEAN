# DEAN Orchestration Testing Strategy

**Version**: 1.0.0  
**Last Updated**: June 13, 2025

## Overview

This document describes the testing strategy for the DEAN orchestration layer, ensuring quality and reliability without modifying external repositories.

## Testing Philosophy

1. **Test in Isolation**: Use mock services to avoid dependencies on external systems
2. **Comprehensive Coverage**: Aim for minimum 80% code coverage
3. **Fast Feedback**: Tests should run quickly for rapid development
4. **Clear Failures**: Test failures should clearly indicate the problem
5. **No Side Effects**: Tests must not modify external systems or repositories

## Test Categories

### Unit Tests

Unit tests validate individual components in isolation.

**Location**: `tests/unit/`

**Scope**:
- Service client methods
- Configuration parsing
- Data models
- Utility functions
- Error handling

**Example**:
```python
@pytest.mark.unit
async def test_indexagent_create_agent(client, sample_agent_config):
    """Test agent creation through IndexAgent client."""
    with patch.object(client, 'post') as mock_post:
        mock_post.return_value = {"id": "agent_123"}
        result = await client.create_agent(sample_agent_config)
        assert result["id"] == "agent_123"
```

### Integration Tests

Integration tests validate interactions between components.

**Location**: `tests/integration/`

**Scope**:
- Service communication
- Workflow execution
- Cross-service operations
- Error propagation

**Example**:
```python
@pytest.mark.integration
@pytest.mark.mock_services
async def test_evolution_workflow(all_mock_services, service_pool):
    """Test complete evolution workflow across services."""
    result = await service_pool.workflow.execute_evolution_trial(
        population_size=5,
        generations=3
    )
    assert result['status'] == 'workflow_triggered'
```

### Contract Tests

Contract tests ensure API compatibility with external services.

**Location**: `tests/contracts/`

**Purpose**: Validate that our understanding of external APIs matches reality

**Note**: Contract test implementation requires stakeholder input on:
- API versioning strategy
- Contract validation approach
- Breaking change detection

### Performance Tests

Performance tests validate system performance requirements.

**Location**: `tests/performance/`

**Metrics**:
- Response time: < 500ms (95th percentile)
- Throughput: > 100 requests/second
- Memory usage: < 4GB under normal load

## Test Infrastructure

### Mock Services

Mock implementations of external services are provided in `tests/fixtures/mock_services.py`:

- **MockIndexAgentService**: Simulates IndexAgent API
- **MockAirflowService**: Simulates Airflow API
- **MockEvolutionAPIService**: Simulates Evolution API

### Fixtures

Common test fixtures are defined in `tests/conftest.py`:

- `test_config`: Test configuration
- `service_pool`: Configured service pool
- `sample_agent_config`: Example agent configuration
- `all_mock_services`: All mock services running

### Test Database

- Unit tests use SQLite in-memory database
- Integration tests use a temporary PostgreSQL database
- No production data is ever used in tests

## Running Tests

### Command Line

```bash
# Run all tests
./scripts/run_tests.sh

# Run unit tests only
./scripts/run_tests.sh --unit

# Run integration tests only
./scripts/run_tests.sh --integration

# Run without coverage
./scripts/run_tests.sh --no-coverage

# Run specific marker
./scripts/run_tests.sh -m "not slow"
```

### Using Make

```bash
# Run all tests
make test

# Run unit tests
make test-unit

# Run integration tests
make test-integration
```

### Direct pytest

```bash
# Run with coverage
pytest --cov=src --cov-report=html

# Run specific file
pytest tests/unit/test_service_clients.py

# Run with verbose output
pytest -vv

# Run tests matching pattern
pytest -k "test_health"
```

## Writing Tests

### Test Structure

```python
import pytest
from unittest.mock import patch, AsyncMock

@pytest.mark.unit  # Mark test category
class TestComponentName:
    """Test suite for ComponentName."""
    
    @pytest.fixture
    def component(self):
        """Create component instance."""
        return ComponentName()
    
    @pytest.mark.asyncio  # For async tests
    async def test_feature_success(self, component):
        """Test successful feature execution."""
        # Arrange
        expected = "expected_result"
        
        # Act
        result = await component.do_something()
        
        # Assert
        assert result == expected
    
    async def test_feature_error(self, component):
        """Test error handling."""
        with pytest.raises(ExpectedError):
            await component.do_something_invalid()
```

### Mocking Guidelines

1. **Mock External Dependencies**: Always mock external service calls
2. **Use AsyncMock**: For async methods, use `AsyncMock` instead of `Mock`
3. **Patch at the Right Level**: Patch where the object is used, not where it's defined
4. **Verify Calls**: Check that mocks were called with expected arguments

### Test Data

1. **Use Fixtures**: Define reusable test data as fixtures
2. **Avoid Hard-Coding**: Use factory functions or builders
3. **Keep It Minimal**: Only include data necessary for the test
4. **Be Explicit**: Clear test data makes tests easier to understand

## Coverage Requirements

### Overall Coverage

- **Minimum**: 80% overall coverage
- **Target**: 90% for critical paths
- **New Code**: 100% coverage for new features

### Coverage by Component

| Component | Required Coverage |
|-----------|------------------|
| Service Clients | 90% |
| Orchestration Core | 95% |
| User Interfaces | 80% |
| Utilities | 85% |

### Exclusions

The following are excluded from coverage:
- Test files themselves
- Type definitions
- Abstract base classes
- Main entry points

## Continuous Integration

### GitHub Actions

Tests run automatically on:
- Pull requests
- Pushes to main branch
- Nightly scheduled runs

### Test Matrix

Tests run against:
- Python 3.10, 3.11
- Ubuntu, macOS, Windows
- With and without optional dependencies

## Best Practices

### DO

1. **Write Tests First**: Follow TDD when possible
2. **Test One Thing**: Each test should verify one behavior
3. **Use Descriptive Names**: Test names should describe what they test
4. **Keep Tests Simple**: Complex tests are hard to maintain
5. **Test Edge Cases**: Don't just test the happy path

### DON'T

1. **Don't Use Sleep**: Use proper wait conditions instead
2. **Don't Test Implementation**: Test behavior, not internals
3. **Don't Share State**: Tests should be independent
4. **Don't Ignore Failures**: Fix flaky tests immediately
5. **Don't Over-Mock**: Too much mocking makes tests brittle

## Debugging Tests

### Verbose Output

```bash
pytest -vv tests/failing_test.py
```

### Print Debugging

```python
pytest -s  # Don't capture stdout
```

### Debugger

```python
import pdb; pdb.set_trace()  # Breakpoint
```

### Failed Test Analysis

1. Check test output for error details
2. Verify mock expectations
3. Check fixture setup
4. Validate test data
5. Review recent changes

## Test Maintenance

### Regular Review

- Monthly review of test suite health
- Remove obsolete tests
- Update tests for API changes
- Improve test performance

### Flaky Test Policy

1. Identify flaky tests through CI metrics
2. Fix within one week or disable
3. Track patterns in flaky tests
4. Address root causes

### Test Refactoring

- Apply DRY principles to tests
- Extract common patterns to fixtures
- Update tests when refactoring code
- Keep tests synchronized with code

## Future Enhancements

1. **Mutation Testing**: Validate test effectiveness
2. **Property-Based Testing**: Use Hypothesis for edge cases
3. **Load Testing**: Validate performance under load
4. **Security Testing**: Automated security scans
5. **Visual Testing**: For dashboard components

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [Testing Best Practices](https://testdriven.io/blog/testing-best-practices/)
- [AsyncIO Testing](https://pytest-asyncio.readthedocs.io/)