"""Comprehensive test suite for ServiceRegistry."""

import asyncio
import pytest
import httpx
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
import json

from src.orchestration.service_registry import (
    ServiceRegistry, ServiceInfo, ServiceStatus, ServiceMetadata,
    ServiceEndpoint, ServiceNotFoundError
)
from src.orchestration.circuit_breaker import CircuitBreakerError, CircuitState


@pytest.fixture
async def registry():
    """Create a service registry without Redis persistence."""
    registry = ServiceRegistry(enable_persistence=False, health_check_interval=0.1)
    await registry.start()
    yield registry
    await registry.stop()


@pytest.fixture
async def mock_redis():
    """Mock Redis client."""
    redis_mock = AsyncMock()
    redis_mock.ping = AsyncMock()
    redis_mock.hset = AsyncMock()
    redis_mock.hgetall = AsyncMock(return_value={})
    redis_mock.hdel = AsyncMock()
    redis_mock.close = AsyncMock()
    return redis_mock


@pytest.fixture
def sample_service_metadata():
    """Sample service metadata."""
    return ServiceMetadata(
        service_type="api",
        api_version="v1",
        endpoints={
            "agents": "/api/v1/agents",
            "evolution": "/api/v1/evolution"
        },
        dependencies=["database", "redis"],
        capabilities=["agent-management", "evolution-control"],
        tags={"environment": "test", "team": "dean"}
    )


class TestServiceRegistry:
    """Test ServiceRegistry core functionality."""
    
    @pytest.mark.asyncio
    async def test_register_service(self, registry, sample_service_metadata):
        """Test service registration."""
        # Register a service
        service = await registry.register_service(
            name="test-service",
            host="localhost",
            port=8080,
            version="1.0.0",
            metadata=sample_service_metadata
        )
        
        assert service.name == "test-service"
        assert service.host == "localhost"
        assert service.port == 8080
        assert service.version == "1.0.0"
        assert service.metadata == sample_service_metadata
        assert service.status == ServiceStatus.UNKNOWN
        
        # Verify service is in registry
        discovered = await registry.discover_service("test-service")
        assert discovered is not None
        assert discovered.name == "test-service"
        
    @pytest.mark.asyncio
    async def test_deregister_service(self, registry):
        """Test service deregistration."""
        # Register a service
        await registry.register_service(
            name="test-service",
            host="localhost",
            port=8080,
            version="1.0.0"
        )
        
        # Deregister it
        removed = await registry.deregister_service("test-service")
        assert removed is True
        
        # Verify it's gone
        service = await registry.discover_service("test-service")
        assert service is None
        
        # Try to deregister non-existent service
        removed = await registry.deregister_service("non-existent")
        assert removed is False
        
    @pytest.mark.asyncio
    async def test_discover_services_by_type(self, registry, sample_service_metadata):
        """Test discovering services by type."""
        # Register multiple services
        metadata1 = ServiceMetadata(service_type="api", api_version="v1")
        metadata2 = ServiceMetadata(service_type="worker", api_version="v1")
        
        await registry.register_service(
            name="api-service-1",
            host="localhost",
            port=8081,
            version="1.0.0",
            metadata=metadata1
        )
        
        await registry.register_service(
            name="api-service-2",
            host="localhost",
            port=8082,
            version="1.0.0",
            metadata=metadata1
        )
        
        await registry.register_service(
            name="worker-service",
            host="localhost",
            port=8083,
            version="1.0.0",
            metadata=metadata2
        )
        
        # Discover by type
        api_services = await registry.discover_services_by_type("api")
        assert len(api_services) == 2
        assert all(s.metadata.service_type == "api" for s in api_services)
        
        worker_services = await registry.discover_services_by_type("worker")
        assert len(worker_services) == 1
        assert worker_services[0].name == "worker-service"
        
    @pytest.mark.asyncio
    async def test_discover_services_by_capability(self, registry):
        """Test discovering services by capability."""
        metadata1 = ServiceMetadata(
            service_type="api",
            api_version="v1",
            capabilities=["auth", "user-management"]
        )
        metadata2 = ServiceMetadata(
            service_type="api",
            api_version="v1",
            capabilities=["data-processing", "analytics"]
        )
        
        await registry.register_service(
            name="auth-service",
            host="localhost",
            port=8081,
            version="1.0.0",
            metadata=metadata1
        )
        
        await registry.register_service(
            name="data-service",
            host="localhost",
            port=8082,
            version="1.0.0",
            metadata=metadata2
        )
        
        # Discover by capability
        auth_services = await registry.discover_services_by_capability("auth")
        assert len(auth_services) == 1
        assert auth_services[0].name == "auth-service"
        
        data_services = await registry.discover_services_by_capability("data-processing")
        assert len(data_services) == 1
        assert data_services[0].name == "data-service"
        
    @pytest.mark.asyncio
    async def test_health_check_healthy_service(self, registry):
        """Test health check for healthy service."""
        # Mock HTTP client
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "healthy", "version": "1.0.0"}
        
        with patch.object(registry._http_client, 'request', return_value=mock_response):
            # Register service
            service = await registry.register_service(
                name="healthy-service",
                host="localhost",
                port=8080,
                version="1.0.0"
            )
            
            # Wait for health check
            await asyncio.sleep(0.2)
            
            # Check status
            status = await registry.get_service_status("healthy-service")
            assert status == ServiceStatus.HEALTHY
            
    @pytest.mark.asyncio
    async def test_health_check_unhealthy_service(self, registry):
        """Test health check for unhealthy service."""
        # Mock HTTP client to return error
        mock_response = Mock()
        mock_response.status_code = 503
        
        with patch.object(registry._http_client, 'request', return_value=mock_response):
            # Register service
            service = await registry.register_service(
                name="unhealthy-service",
                host="localhost",
                port=8080,
                version="1.0.0"
            )
            
            # Wait for health check
            await asyncio.sleep(0.2)
            
            # Check status
            status = await registry.get_service_status("unhealthy-service")
            assert status == ServiceStatus.UNHEALTHY
            
    @pytest.mark.asyncio
    async def test_health_check_timeout(self, registry):
        """Test health check timeout handling."""
        # Mock HTTP client to raise timeout
        with patch.object(
            registry._http_client,
            'request',
            side_effect=httpx.TimeoutException("Timeout")
        ):
            # Register service
            service = await registry.register_service(
                name="timeout-service",
                host="localhost",
                port=8080,
                version="1.0.0"
            )
            
            # Wait for health check
            await asyncio.sleep(0.2)
            
            # Check status
            status = await registry.get_service_status("timeout-service")
            assert status == ServiceStatus.UNHEALTHY
            
            # Check error message
            service = await registry.discover_service("timeout-service")
            assert service.last_error == "Health check timeout"
            
    @pytest.mark.asyncio
    async def test_get_healthy_services(self, registry):
        """Test getting all healthy services."""
        # Register services with different statuses
        services = [
            ("healthy-1", ServiceStatus.HEALTHY),
            ("healthy-2", ServiceStatus.HEALTHY),
            ("unhealthy-1", ServiceStatus.UNHEALTHY),
            ("unknown-1", ServiceStatus.UNKNOWN),
        ]
        
        for name, status in services:
            service = await registry.register_service(
                name=name,
                host="localhost",
                port=8080,
                version="1.0.0"
            )
            # Manually set status for testing
            service.status = status
            
        # Get healthy services
        healthy = await registry.get_healthy_services()
        assert len(healthy) == 2
        assert all(s.status == ServiceStatus.HEALTHY for s in healthy)
        assert set(s.name for s in healthy) == {"healthy-1", "healthy-2"}
        
    @pytest.mark.asyncio
    async def test_call_service_success(self, registry):
        """Test calling a service successfully."""
        # Register service
        await registry.register_service(
            name="test-service",
            host="localhost",
            port=8080,
            version="1.0.0"
        )
        
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": "success"}
        
        with patch.object(registry._http_client, 'request', return_value=mock_response):
            response = await registry.call_service(
                "test-service",
                "/api/test",
                method="GET"
            )
            
            assert response.status_code == 200
            assert response.json() == {"result": "success"}
            
    @pytest.mark.asyncio
    async def test_call_service_not_found(self, registry):
        """Test calling non-existent service."""
        with pytest.raises(ServiceNotFoundError):
            await registry.call_service("non-existent", "/api/test")
            
    @pytest.mark.asyncio
    async def test_circuit_breaker_integration(self, registry):
        """Test circuit breaker opens after failures."""
        # Register service
        await registry.register_service(
            name="flaky-service",
            host="localhost",
            port=8080,
            version="1.0.0"
        )
        
        # Mock failures
        with patch.object(
            registry._http_client,
            'request',
            side_effect=Exception("Connection error")
        ):
            # Make calls until circuit opens
            for i in range(3):
                try:
                    await registry.call_service("flaky-service", "/api/test")
                except Exception:
                    pass
                    
            # Circuit should be open now
            with pytest.raises(CircuitBreakerError):
                await registry.call_service("flaky-service", "/api/test")
                
    @pytest.mark.asyncio
    async def test_metrics(self, registry):
        """Test metrics collection."""
        # Register some services
        await registry.register_service(
            name="service-1",
            host="localhost",
            port=8081,
            version="1.0.0"
        )
        
        await registry.register_service(
            name="service-2",
            host="localhost",
            port=8082,
            version="1.0.0"
        )
        
        # Get metrics
        metrics = registry.get_metrics()
        
        assert metrics["total_services"] == 2
        assert "healthy_services" in metrics
        assert "unhealthy_services" in metrics
        assert "circuit_breakers" in metrics
        

class TestServiceRegistryWithRedis:
    """Test ServiceRegistry with Redis persistence."""
    
    @pytest.mark.asyncio
    async def test_redis_persistence(self, mock_redis):
        """Test service persistence to Redis."""
        with patch('redis.asyncio.from_url', return_value=mock_redis):
            registry = ServiceRegistry(
                redis_url="redis://localhost",
                enable_persistence=True,
                health_check_interval=1.0
            )
            await registry.start()
            
            # Register a service
            await registry.register_service(
                name="persistent-service",
                host="localhost",
                port=8080,
                version="1.0.0"
            )
            
            # Verify Redis was called
            mock_redis.hset.assert_called()
            call_args = mock_redis.hset.call_args
            assert call_args[0][0] == "dean:services"
            assert call_args[0][1] == "persistent-service"
            
            await registry.stop()
            
    @pytest.mark.asyncio
    async def test_load_from_redis(self, mock_redis):
        """Test loading services from Redis on startup."""
        # Mock existing service data in Redis
        service_data = {
            "name": "existing-service",
            "host": "localhost",
            "port": 8080,
            "version": "1.0.0",
            "status": "healthy",
            "registration_time": datetime.utcnow().isoformat()
        }
        
        mock_redis.hgetall.return_value = {
            b"existing-service": json.dumps(service_data).encode()
        }
        
        with patch('redis.asyncio.from_url', return_value=mock_redis):
            registry = ServiceRegistry(
                redis_url="redis://localhost",
                enable_persistence=True,
                health_check_interval=1.0
            )
            await registry.start()
            
            # Check service was loaded
            service = await registry.discover_service("existing-service")
            assert service is not None
            assert service.name == "existing-service"
            assert service.host == "localhost"
            
            await registry.stop()
            
    @pytest.mark.asyncio
    async def test_redis_graceful_degradation(self):
        """Test registry works without Redis when it's unavailable."""
        # Mock Redis connection failure
        mock_redis = AsyncMock()
        mock_redis.ping.side_effect = Exception("Redis unavailable")
        
        with patch('redis.asyncio.from_url', return_value=mock_redis):
            registry = ServiceRegistry(
                redis_url="redis://localhost",
                enable_persistence=True,
                health_check_interval=1.0
            )
            await registry.start()
            
            # Registry should still work
            service = await registry.register_service(
                name="test-service",
                host="localhost",
                port=8080,
                version="1.0.0"
            )
            
            assert service is not None
            discovered = await registry.discover_service("test-service")
            assert discovered is not None
            
            await registry.stop()
            

class TestServiceInfo:
    """Test ServiceInfo data model."""
    
    def test_service_info_base_url(self):
        """Test base URL generation."""
        service = ServiceInfo(
            name="test",
            host="example.com",
            port=8080,
            version="1.0.0"
        )
        assert service.base_url == "http://example.com:8080"
        
        # With HTTPS endpoint
        service.health_endpoint = ServiceEndpoint(protocol="https")
        assert service.base_url == "https://example.com:8080"
        
    def test_service_info_serialization(self):
        """Test ServiceInfo serialization/deserialization."""
        metadata = ServiceMetadata(
            service_type="api",
            api_version="v1",
            capabilities=["test"]
        )
        
        service = ServiceInfo(
            name="test",
            host="localhost",
            port=8080,
            version="1.0.0",
            status=ServiceStatus.HEALTHY,
            metadata=metadata,
            last_error="Test error"
        )
        
        # Serialize
        data = service.to_dict()
        assert data["name"] == "test"
        assert data["status"] == "healthy"
        assert data["metadata"]["service_type"] == "api"
        
        # Deserialize
        restored = ServiceInfo.from_dict(data)
        assert restored.name == "test"
        assert restored.status == ServiceStatus.HEALTHY
        assert restored.metadata.service_type == "api"
        assert restored.last_error == "Test error"