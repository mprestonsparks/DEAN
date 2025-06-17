"""Unit tests for service client implementations."""

import pytest
from unittest.mock import AsyncMock, patch

from integration import (
    IndexAgentClient,
    AirflowClient,
    EvolutionAPIClient,
    ServiceError,
    ServiceTimeout,
    ServiceConnectionError
)


@pytest.mark.unit
class TestIndexAgentClient:
    """Test IndexAgent client functionality."""
    
    @pytest.fixture
    def client(self):
        """Create IndexAgent client."""
        return IndexAgentClient("http://localhost:8081")
    
    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """Test health check method."""
        with patch.object(client, 'get') as mock_get:
            mock_get.return_value = {"status": "healthy"}
            
            result = await client.health_check()
            
            assert result["status"] == "healthy"
            mock_get.assert_called_once_with("/health")
    
    @pytest.mark.asyncio
    async def test_create_agent(self, client, sample_agent_config):
        """Test agent creation."""
        expected_response = {
            "id": "agent_123",
            **sample_agent_config
        }
        
        with patch.object(client, 'post') as mock_post:
            mock_post.return_value = expected_response
            
            result = await client.create_agent(sample_agent_config)
            
            assert result["id"] == "agent_123"
            mock_post.assert_called_once_with("/agents", json=sample_agent_config)
    
    @pytest.mark.asyncio
    async def test_list_agents(self, client):
        """Test listing agents."""
        expected_agents = [
            {"id": "agent_1", "name": "Agent 1"},
            {"id": "agent_2", "name": "Agent 2"}
        ]
        
        with patch.object(client, 'get') as mock_get:
            mock_get.return_value = expected_agents
            
            result = await client.list_agents(limit=10, offset=0)
            
            assert len(result) == 2
            mock_get.assert_called_once_with(
                "/agents",
                params={"limit": 10, "offset": 0}
            )
    
    @pytest.mark.asyncio
    async def test_error_handling(self, client):
        """Test error handling."""
        with patch.object(client, '_request') as mock_request:
            mock_request.side_effect = ServiceTimeout(
                "Request timeout",
                "IndexAgent",
                {"url": "/test"}
            )
            
            with pytest.raises(ServiceTimeout):
                await client.get("/test")


@pytest.mark.unit
class TestAirflowClient:
    """Test Airflow client functionality."""
    
    @pytest.fixture
    def client(self):
        """Create Airflow client."""
        return AirflowClient(
            "http://localhost:8080",
            username="test",
            password="test"
        )
    
    @pytest.mark.asyncio
    async def test_trigger_dag(self, client, sample_dag_config):
        """Test DAG triggering."""
        expected_response = {
            "dag_run_id": "manual__2025-01-01T00:00:00",
            "state": "queued"
        }
        
        with patch.object(client, 'post') as mock_post:
            mock_post.return_value = expected_response
            
            result = await client.trigger_dag(
                sample_dag_config["dag_id"],
                conf=sample_dag_config["conf"]
            )
            
            assert result["dag_run_id"].startswith("manual__")
            assert result["state"] == "queued"
    
    @pytest.mark.asyncio
    async def test_get_dag_run_status(self, client):
        """Test getting DAG run status."""
        expected_status = {
            "dag_run_id": "test_run",
            "state": "success",
            "execution_date": "2025-01-01T00:00:00"
        }
        
        with patch.object(client, 'get') as mock_get:
            mock_get.return_value = expected_status
            
            result = await client.get_dag_run("test_dag", "test_run")
            
            assert result["state"] == "success"
            mock_get.assert_called_once_with(
                "/api/v1/dags/test_dag/dagRuns/test_run"
            )
    
    @pytest.mark.asyncio
    async def test_basic_auth_header(self, client):
        """Test basic auth header is set."""
        import base64
        
        auth_header = client._session.headers.get('Authorization')
        assert auth_header is not None
        assert auth_header.startswith('Basic ')
        
        # Decode and verify
        encoded = auth_header.split(' ')[1]
        decoded = base64.b64decode(encoded).decode()
        assert decoded == "test:test"


@pytest.mark.unit
class TestEvolutionAPIClient:
    """Test Evolution API client functionality."""
    
    @pytest.fixture
    def client(self):
        """Create Evolution API client."""
        return EvolutionAPIClient("http://localhost:8090")
    
    @pytest.mark.asyncio
    async def test_start_evolution(self, client, sample_evolution_config):
        """Test starting evolution."""
        expected_response = {
            "trial_id": "trial_123",
            "status": "started"
        }
        
        with patch.object(client, 'post') as mock_post:
            mock_post.return_value = expected_response
            
            result = await client.start_evolution(
                population_size=sample_evolution_config["population_size"],
                generations=sample_evolution_config["generations"]
            )
            
            assert result["trial_id"] == "trial_123"
            assert result["status"] == "started"
    
    @pytest.mark.asyncio
    async def test_get_patterns(self, client):
        """Test getting patterns."""
        expected_patterns = [
            {
                "id": "pattern_1",
                "type": "optimization",
                "effectiveness": 0.85
            }
        ]
        
        with patch.object(client, 'get') as mock_get:
            mock_get.return_value = expected_patterns
            
            result = await client.get_patterns(min_effectiveness=0.8)
            
            assert len(result) == 1
            assert result[0]["effectiveness"] >= 0.8
            mock_get.assert_called_once_with(
                "/patterns",
                params={"min_effectiveness": 0.8}
            )
    
    @pytest.mark.asyncio
    async def test_get_metrics_prometheus(self, client):
        """Test getting metrics in Prometheus format."""
        prometheus_metrics = "evolution_fitness_best 0.92\n"
        
        with patch.object(client, '_request') as mock_request:
            mock_request.return_value = prometheus_metrics
            
            result = await client.get_metrics(format="prometheus")
            
            assert "evolution_fitness_best" in result
            mock_request.assert_called_once()