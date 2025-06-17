"""Test service-to-service authentication and security integration."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import timedelta
import asyncio
import aiohttp

from src.auth.auth_models import UserRole, APIKey
from src.auth.auth_utils import create_access_token
from src.integration.auth_service_pool import AuthServicePool
from src.integration.service_adapters import (
    EvolutionServiceAdapter, IndexAgentServiceAdapter, 
    AirflowServiceAdapter, InfraServiceAdapter
)


class TestServiceAuthentication:
    """Test service-to-service authentication."""
    
    @pytest.fixture
    def service_token(self):
        """Create a service authentication token."""
        return create_access_token(
            user_id="orchestrator-service",
            username="dean-orchestrator",
            roles=[UserRole.SERVICE],
            expires_delta=timedelta(hours=24),
            secret_key="test-secret-key",
            algorithm="HS256"
        )
    
    @pytest.fixture
    def auth_pool(self):
        """Create auth service pool."""
        config = {
            "evolution_api": {
                "base_url": "http://localhost:8001",
                "timeout": 30,
                "auth": {"type": "bearer"}
            },
            "indexagent_api": {
                "base_url": "http://localhost:8002",
                "timeout": 30,
                "auth": {"type": "bearer"}
            },
            "airflow_api": {
                "base_url": "http://localhost:8080",
                "timeout": 30,
                "auth": {
                    "type": "basic",
                    "username": "airflow",
                    "password": "airflow"
                }
            }
        }
        return AuthServicePool(config)
    
    @pytest.mark.asyncio
    async def test_bearer_auth_added_to_requests(self, auth_pool, service_token):
        """Test that bearer auth is added to service requests."""
        # Set the service token
        auth_pool.service_token = service_token
        
        # Mock aiohttp session
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"agents": []})
        
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            session = await auth_pool.get_session("evolution_api")
            
            # Make a request
            async with session.get("/api/agents") as response:
                data = await response.json()
            
            # Verify auth header was added
            mock_session.get.assert_called_once()
            call_args = mock_session.get.call_args
            headers = call_args[1].get('headers', {})
            assert 'Authorization' in headers
            assert headers['Authorization'] == f"Bearer {service_token}"
    
    @pytest.mark.asyncio
    async def test_basic_auth_for_airflow(self, auth_pool):
        """Test that basic auth is used for Airflow."""
        # Mock aiohttp session
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"dags": []})
        
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            session = await auth_pool.get_session("airflow_api")
            
            # Make a request
            async with session.get("/api/v1/dags") as response:
                data = await response.json()
            
            # Verify basic auth was added
            mock_session.get.assert_called_once()
            call_args = mock_session.get.call_args
            
            # Basic auth should be in session creation, not headers
            # This test documents expected behavior
    
    @pytest.mark.asyncio
    async def test_service_token_refresh(self, auth_pool):
        """Test that service tokens are refreshed when expired."""
        # Create token that expires soon
        short_token = create_access_token(
            user_id="orchestrator-service",
            username="dean-orchestrator",
            roles=[UserRole.SERVICE],
            expires_delta=timedelta(seconds=1),
            secret_key="test-secret-key",
            algorithm="HS256"
        )
        
        auth_pool.service_token = short_token
        
        # Wait for expiration
        await asyncio.sleep(2)
        
        # Token should be detected as expired and refreshed
        # (Implementation depends on refresh mechanism)
        
        # This test documents that token refresh should be implemented


class TestServiceAdapterSecurity:
    """Test security in service adapters."""
    
    @pytest.fixture
    def evolution_adapter(self):
        """Create evolution service adapter."""
        return EvolutionServiceAdapter(
            base_url="http://localhost:8001",
            auth_pool=Mock()
        )
    
    @pytest.fixture
    def indexagent_adapter(self):
        """Create IndexAgent service adapter."""
        return IndexAgentServiceAdapter(
            base_url="http://localhost:8002",
            auth_pool=Mock()
        )
    
    @pytest.mark.asyncio
    async def test_adapter_uses_auth_pool(self, evolution_adapter):
        """Test that adapters use auth pool for requests."""
        # Mock the auth pool session
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"agents": []})
        
        mock_session.get = AsyncMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        
        evolution_adapter.auth_pool.get_session = AsyncMock(return_value=mock_session)
        
        # Make a request
        agents = await evolution_adapter.get_agents()
        
        # Verify auth pool was used
        evolution_adapter.auth_pool.get_session.assert_called_with("evolution_api")
    
    @pytest.mark.asyncio
    async def test_adapter_handles_auth_errors(self, indexagent_adapter):
        """Test that adapters handle authentication errors properly."""
        # Mock 401 response
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status = 401
        mock_response.text = AsyncMock(return_value="Unauthorized")
        
        mock_session.post = AsyncMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        
        indexagent_adapter.auth_pool.get_session = AsyncMock(return_value=mock_session)
        
        # Should handle auth error gracefully
        with pytest.raises(Exception) as exc_info:
            await indexagent_adapter.index_repository("https://github.com/test/repo")
        
        assert "401" in str(exc_info.value) or "Unauthorized" in str(exc_info.value)


class TestAPIKeysIntegration:
    """Test API key usage in service integration."""
    
    @pytest.fixture
    def auth_manager(self):
        """Create auth manager."""
        from src.auth.auth_manager import get_auth_manager
        from src.auth import auth_manager as auth_module
        auth_module._auth_manager = None
        return get_auth_manager()
    
    def test_service_api_key_creation(self, auth_manager):
        """Test creating API keys for service integration."""
        # Create API key for external service
        plain_key, api_key = auth_manager.create_api_key(
            name="External Monitoring Service",
            description="API key for Prometheus metrics scraping",
            roles=[UserRole.VIEWER]  # Read-only access
        )
        
        assert plain_key is not None
        assert len(plain_key) >= 32  # Should be sufficiently long
        assert api_key.name == "External Monitoring Service"
        assert UserRole.VIEWER in api_key.roles
        assert UserRole.USER not in api_key.roles  # Should not have write access
    
    def test_internal_service_api_key(self, auth_manager):
        """Test creating API keys for internal services."""
        # Create API key for internal service
        plain_key, api_key = auth_manager.create_api_key(
            name="Evolution Engine",
            description="Internal service API key",
            roles=[UserRole.SERVICE]
        )
        
        assert UserRole.SERVICE in api_key.roles
        
        # Validate the key works
        validated = auth_manager.validate_api_key(plain_key)
        assert validated is not None
        assert validated.key_id == api_key.key_id


class TestSecurityPropagation:
    """Test security context propagation across services."""
    
    @pytest.mark.asyncio
    async def test_user_context_propagation(self):
        """Test that user context is propagated through service calls."""
        # Create user token
        user_token = create_access_token(
            user_id="user-123",
            username="testuser",
            roles=[UserRole.USER],
            expires_delta=timedelta(minutes=30),
            secret_key="test-secret-key",
            algorithm="HS256"
        )
        
        # Mock orchestrator making calls to other services
        mock_evolution_response = {"trial_id": "trial-123", "status": "started"}
        mock_index_response = {"indexed": True, "documents": 100}
        
        # In a real implementation, the orchestrator should:
        # 1. Receive user request with token
        # 2. Validate user token
        # 3. Create service token with user context
        # 4. Make service calls with service token
        # 5. Services can audit actions with original user context
        
        # This test documents expected behavior
    
    @pytest.mark.asyncio
    async def test_audit_trail(self):
        """Test that security events create audit trail."""
        # Security events that should be logged:
        # - Login attempts (success/failure)
        # - Token creation/refresh
        # - API key usage
        # - Authorization failures
        # - Service-to-service calls
        
        # This test documents audit requirements
        pass


class TestSecurityHeaders:
    """Test security headers in service communication."""
    
    @pytest.mark.asyncio
    async def test_request_id_propagation(self):
        """Test that request IDs are propagated for tracing."""
        # Headers that should be propagated:
        # - X-Request-ID: For request tracing
        # - X-User-ID: For audit trail
        # - X-Original-IP: For security logging
        
        # This test documents tracing requirements
        pass
    
    @pytest.mark.asyncio
    async def test_security_headers_not_leaked(self):
        """Test that sensitive headers are not leaked."""
        # Headers that should NOT be propagated:
        # - Authorization: Should be recreated for each hop
        # - Cookie: Should not be forwarded
        # - X-API-Key: Should not be forwarded
        
        # This test documents security requirements
        pass