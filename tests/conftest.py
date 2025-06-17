"""Pytest configuration and fixtures for DEAN orchestration tests."""

import os
import asyncio
from typing import AsyncGenerator, Generator, Dict, Any
from unittest.mock import MagicMock, AsyncMock

import pytest
import pytest_asyncio
from aiohttp import web

# Configure test environment
os.environ['DEAN_TESTING'] = 'true'
os.environ['USE_MOCK_SERVICES'] = 'true'


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_config() -> Dict[str, Any]:
    """Test configuration fixture."""
    return {
        'service_endpoints': {
            'indexagent': 'http://localhost:18081',
            'airflow': 'http://localhost:18080',
            'evolution': 'http://localhost:18090',
        },
        'timeout': 5,
        'max_retries': 1,
    }


@pytest_asyncio.fixture
async def mock_indexagent_server():
    """Mock IndexAgent server for testing."""
    from tests.fixtures.mock_services import MockIndexAgentService
    
    mock_service = MockIndexAgentService(port=18081)
    app = mock_service.create_app()
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 18081)
    await site.start()
    
    yield mock_service
    
    await runner.cleanup()


@pytest_asyncio.fixture
async def mock_airflow_server():
    """Mock Airflow server for testing."""
    from tests.fixtures.mock_services import MockAirflowService
    
    mock_service = MockAirflowService(port=18080)
    app = mock_service.create_app()
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 18080)
    await site.start()
    
    yield mock_service
    
    await runner.cleanup()


@pytest_asyncio.fixture
async def mock_evolution_server():
    """Mock Evolution API server for testing."""
    from tests.fixtures.mock_services import MockEvolutionAPIService
    
    mock_service = MockEvolutionAPIService(port=18090)
    app = mock_service.create_app()
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 18090)
    await site.start()
    
    yield mock_service
    
    await runner.cleanup()


@pytest_asyncio.fixture
async def all_mock_services(
    mock_indexagent_server,
    mock_airflow_server,
    mock_evolution_server
):
    """Start all mock services."""
    yield {
        'indexagent': mock_indexagent_server,
        'airflow': mock_airflow_server,
        'evolution': mock_evolution_server,
    }


@pytest_asyncio.fixture
async def service_pool(test_config):
    """Create a service pool for testing."""
    from integration import ServicePool
    
    pool = ServicePool(**test_config['service_endpoints'])
    yield pool
    await pool.close()


@pytest.fixture
def mock_subprocess():
    """Mock subprocess for testing deployment."""
    import subprocess
    from unittest.mock import patch
    
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='',
            stderr=''
        )
        yield mock_run


@pytest.fixture
def temp_dir(tmp_path):
    """Temporary directory for test files."""
    return tmp_path


@pytest.fixture
def sample_agent_config():
    """Sample agent configuration for testing."""
    return {
        "name": "test_agent",
        "type": "optimization",
        "parameters": {
            "target": "performance",
            "constraints": {
                "max_tokens": 1000,
                "timeout": 300
            }
        }
    }


@pytest.fixture
def sample_evolution_config():
    """Sample evolution configuration for testing."""
    return {
        "population_size": 5,
        "generations": 3,
        "mutation_rate": 0.1,
        "crossover_rate": 0.7,
        "selection_method": "tournament",
        "token_budget": 1000,
        "optimization_goals": ["performance", "readability"]
    }


@pytest.fixture
def sample_dag_config():
    """Sample DAG configuration for testing."""
    return {
        "dag_id": "test_evolution_workflow",
        "conf": {
            "repository": "test_repo",
            "trial_id": "test_trial_001"
        }
    }


# Markers for test categorization
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: Unit tests that don't require external services"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests that may require services"
    )
    config.addinivalue_line(
        "markers", "slow: Tests that take more than 1 second"
    )
    config.addinivalue_line(
        "markers", "mock_services: Tests that use mock services"
    )


# Test database fixtures
@pytest.fixture
def test_db_url():
    """Test database URL."""
    return "sqlite:///:memory:"


@pytest_asyncio.fixture
async def test_database(test_db_url):
    """Create test database."""
    # Note: Database setup requires stakeholder input on schema
    yield test_db_url


# Utility functions for tests
class AsyncContextManagerMock:
    """Mock for async context managers."""
    
    def __init__(self, return_value=None):
        self.return_value = return_value
        self.aenter_called = False
        self.aexit_called = False
    
    async def __aenter__(self):
        self.aenter_called = True
        return self.return_value
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.aexit_called = True
        return False


# Security test fixtures
@pytest.fixture
def auth_headers():
    """Create standard auth headers for testing."""
    from src.auth.auth_utils import create_access_token
    from src.auth.auth_models import UserRole
    from datetime import timedelta
    
    token = create_access_token(
        user_id="test-user-id",
        username="testuser",
        roles=[UserRole.USER],
        expires_delta=timedelta(minutes=30),
        secret_key="test-secret-key",
        algorithm="HS256"
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_auth_headers():
    """Create admin auth headers for testing."""
    from src.auth.auth_utils import create_access_token
    from src.auth.auth_models import UserRole
    from datetime import timedelta
    
    token = create_access_token(
        user_id="admin-id",
        username="admin",
        roles=[UserRole.ADMIN],
        expires_delta=timedelta(minutes=30),
        secret_key="test-secret-key",
        algorithm="HS256"
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def service_auth_headers():
    """Create service auth headers for testing."""
    from src.auth.auth_utils import create_access_token
    from src.auth.auth_models import UserRole
    from datetime import timedelta
    
    token = create_access_token(
        user_id="service-id",
        username="orchestrator-service",
        roles=[UserRole.SERVICE],
        expires_delta=timedelta(minutes=30),
        secret_key="test-secret-key",
        algorithm="HS256"
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def mock_auth_manager():
    """Mock auth manager for testing."""
    from unittest.mock import Mock
    from src.auth.auth_models import User, UserRole, TokenResponse
    
    mock = Mock()
    mock.authenticate_user.return_value = User(
        id="test-user-id",
        username="testuser",
        email="test@example.com",
        full_name="Test User",
        roles=[UserRole.USER],
        is_active=True,
        created_at=None,
        last_login=None
    )
    mock.create_token_response.return_value = TokenResponse(
        access_token="test-access-token",
        refresh_token="test-refresh-token",
        token_type="bearer",
        expires_in=1800
    )
    return mock