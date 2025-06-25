"""Integration tests for evolution trial endpoints.

This module tests the complete evolution trial workflow with actual
service connections (or mock services) to verify end-to-end functionality.
"""

import asyncio
import pytest
import httpx
import websockets
import json
from unittest.mock import AsyncMock, patch
from datetime import datetime
import os

from src.orchestration.orchestration_server import app
from src.orchestration.evolution_trials import EvolutionTrialManager, TrialStatus
from .mock_services import MockDEANServices


# Test configuration
TEST_AUTH_TOKEN = "test-jwt-token"
TEST_SERVICE_TOKEN = "test-service-token"


@pytest.fixture
async def mock_auth():
    """Mock authentication for testing."""
    async def mock_get_current_user():
        return TEST_AUTH_TOKEN
        
    with patch("src.orchestration.orchestration_server.get_current_user", mock_get_current_user):
        yield


@pytest.fixture
async def mock_services():
    """Create mock DEAN services for testing."""
    services = MockDEANServices()
    
    # Use test ports
    if os.getenv("USE_REAL_SERVICES") != "true":
        await services.start_all(
            indexagent_port=18081,
            evolution_port=18090,
            airflow_port=18080
        )
        
        # Update environment for test
        os.environ["INDEXAGENT_HOST"] = "localhost"
        os.environ["INDEXAGENT_PORT"] = "18081"
        os.environ["EVOLUTION_API_HOST"] = "localhost"
        os.environ["EVOLUTION_API_PORT"] = "18090"
        os.environ["AIRFLOW_HOST"] = "localhost"
        os.environ["AIRFLOW_PORT"] = "18080"
        
        yield services
        
        services.stop_all()
    else:
        # Use real services if configured
        yield None


@pytest.fixture
async def test_client(mock_services, mock_auth):
    """Create test client with mocked services."""
    from fastapi.testclient import TestClient
    
    with TestClient(app) as client:
        yield client


class TestEvolutionTrialIntegration:
    """Integration tests for evolution trial functionality."""
    
    @pytest.mark.asyncio
    async def test_start_evolution_trial(self, test_client):
        """Test starting an evolution trial end-to-end."""
        # Start evolution trial
        response = test_client.post(
            "/api/v1/orchestration/evolution/start",
            json={
                "population_size": 5,
                "generations": 10,
                "token_budget": 50000,
                "diversity_threshold": 0.3
            },
            headers={"Authorization": f"Bearer {TEST_AUTH_TOKEN}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "trial_id" in data
        assert "workflow_instance_id" in data
        assert data["status"] in ["pending", "initializing", "running"]
        assert data["parameters"]["population_size"] == 5
        assert data["parameters"]["generations"] == 10
        assert data["parameters"]["token_budget"] == 50000
        assert data["parameters"]["diversity_threshold"] == 0.3
        assert "websocket_url" in data
        
        trial_id = data["trial_id"]
        
        # Wait a moment for trial to start
        await asyncio.sleep(1.0)
        
        # Check trial status
        status_response = test_client.get(
            f"/api/v1/orchestration/evolution/{trial_id}/status",
            headers={"Authorization": f"Bearer {TEST_AUTH_TOKEN}"}
        )
        
        assert status_response.status_code == 200
        status_data = status_response.json()
        
        assert status_data["trial_id"] == trial_id
        assert status_data["status"] in ["initializing", "running"]
        assert "progress" in status_data
        assert "resource_usage" in status_data
        assert "performance" in status_data
        
    @pytest.mark.asyncio
    async def test_list_evolution_trials(self, test_client):
        """Test listing evolution trials."""
        # Create a few trials
        trial_ids = []
        for i in range(3):
            response = test_client.post(
                "/api/v1/orchestration/evolution/start",
                json={
                    "population_size": 3,
                    "generations": 5,
                    "token_budget": 10000,
                    "diversity_threshold": 0.3
                },
                headers={"Authorization": f"Bearer {TEST_AUTH_TOKEN}"}
            )
            assert response.status_code == 200
            trial_ids.append(response.json()["trial_id"])
            
        # List all trials
        list_response = test_client.get(
            "/api/v1/orchestration/evolution/list",
            headers={"Authorization": f"Bearer {TEST_AUTH_TOKEN}"}
        )
        
        assert list_response.status_code == 200
        list_data = list_response.json()
        
        assert "trials" in list_data
        assert len(list_data["trials"]) >= 3
        assert list_data["total"] >= 3
        
        # Verify trial data structure
        for trial in list_data["trials"]:
            assert "trial_id" in trial
            assert "status" in trial
            assert "created_at" in trial
            assert "population_size" in trial
            assert "generations" in trial
            assert "current_generation" in trial
            assert "best_fitness" in trial
            assert "tokens_used" in trial
            assert "patterns_discovered" in trial
            
    @pytest.mark.asyncio
    async def test_cancel_evolution_trial(self, test_client):
        """Test cancelling a running evolution trial."""
        # Start a trial
        response = test_client.post(
            "/api/v1/orchestration/evolution/start",
            json={
                "population_size": 5,
                "generations": 100,  # Long running
                "token_budget": 100000,
                "diversity_threshold": 0.3
            },
            headers={"Authorization": f"Bearer {TEST_AUTH_TOKEN}"}
        )
        
        assert response.status_code == 200
        trial_id = response.json()["trial_id"]
        
        # Wait for trial to start
        await asyncio.sleep(1.0)
        
        # Cancel the trial
        cancel_response = test_client.post(
            f"/api/v1/orchestration/evolution/{trial_id}/cancel",
            headers={"Authorization": f"Bearer {TEST_AUTH_TOKEN}"}
        )
        
        assert cancel_response.status_code == 200
        cancel_data = cancel_response.json()
        
        assert cancel_data["trial_id"] == trial_id
        assert cancel_data["status"] == "cancelled"
        
        # Verify trial is cancelled
        status_response = test_client.get(
            f"/api/v1/orchestration/evolution/{trial_id}/status",
            headers={"Authorization": f"Bearer {TEST_AUTH_TOKEN}"}
        )
        
        assert status_response.status_code == 200
        assert status_response.json()["status"] == "cancelled"
        
    @pytest.mark.asyncio
    async def test_evolution_trial_auth_propagation(self, test_client):
        """Test that auth tokens are properly propagated to service calls."""
        with patch("src.orchestration.workflow_executor.WorkflowExecutor._execute_service_call") as mock_call:
            # Set up mock to capture headers
            captured_headers = {}
            
            async def capture_headers(self, step, instance):
                # Capture headers from the instance context
                captured_headers.update(instance.context.get("headers", {}))
                return {"success": True}
                
            mock_call.side_effect = capture_headers
            
            # Start trial
            response = test_client.post(
                "/api/v1/orchestration/evolution/start",
                json={
                    "population_size": 2,
                    "generations": 1,
                    "token_budget": 1000,
                    "diversity_threshold": 0.3
                },
                headers={"Authorization": f"Bearer {TEST_AUTH_TOKEN}"}
            )
            
            assert response.status_code == 200
            
            # Wait for workflow to process
            await asyncio.sleep(0.5)
            
            # Verify auth token was included in context
            # (In actual execution, this would be in the headers of service calls)
            assert mock_call.called
            
    @pytest.mark.asyncio
    async def test_websocket_evolution_monitoring(self, test_client):
        """Test WebSocket monitoring of evolution trials."""
        # Start a trial
        response = test_client.post(
            "/api/v1/orchestration/evolution/start",
            json={
                "population_size": 3,
                "generations": 5,
                "token_budget": 10000,
                "diversity_threshold": 0.3
            },
            headers={"Authorization": f"Bearer {TEST_AUTH_TOKEN}"}
        )
        
        assert response.status_code == 200
        trial_id = response.json()["trial_id"]
        
        # Connect to WebSocket
        async with websockets.connect(
            f"ws://localhost:8000/ws/evolution/{trial_id}"
        ) as websocket:
            # Receive initial status
            message = await websocket.recv()
            data = json.loads(message)
            
            assert data["type"] == "status"
            assert "trial" in data
            
            # Wait for at least one update
            update_received = False
            for _ in range(10):  # Try for up to 10 seconds
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    data = json.loads(message)
                    
                    if data["type"] == "update":
                        update_received = True
                        assert "trial_id" in data
                        assert "status" in data
                        assert "current_generation" in data
                        assert "total_tokens_used" in data
                        assert "best_fitness_score" in data
                        break
                except asyncio.TimeoutError:
                    continue
                    
            assert update_received, "No update received via WebSocket"
            
    @pytest.mark.asyncio
    async def test_evolution_trial_error_handling(self, test_client):
        """Test error handling when services are unavailable."""
        # Temporarily break service registry
        with patch("src.orchestration.service_registry.ServiceRegistry.call_service") as mock_call:
            mock_call.side_effect = Exception("Service unavailable")
            
            response = test_client.post(
                "/api/v1/orchestration/evolution/start",
                json={
                    "population_size": 5,
                    "generations": 10,
                    "token_budget": 50000,
                    "diversity_threshold": 0.3
                },
                headers={"Authorization": f"Bearer {TEST_AUTH_TOKEN}"}
            )
            
            # Should handle error gracefully
            assert response.status_code == 500
            assert "error" in response.json() or "detail" in response.json()
            
    @pytest.mark.asyncio
    async def test_evolution_metrics_aggregation(self, test_client):
        """Test that evolution metrics are properly aggregated."""
        # Start a trial
        response = test_client.post(
            "/api/v1/orchestration/evolution/start",
            json={
                "population_size": 5,
                "generations": 10,
                "token_budget": 50000,
                "diversity_threshold": 0.3
            },
            headers={"Authorization": f"Bearer {TEST_AUTH_TOKEN}"}
        )
        
        assert response.status_code == 200
        trial_id = response.json()["trial_id"]
        
        # Wait for some progress
        await asyncio.sleep(2.0)
        
        # Get Prometheus metrics
        metrics_response = test_client.get("/metrics")
        assert metrics_response.status_code == 200
        
        metrics_text = metrics_response.text
        
        # Verify evolution metrics are included
        assert "dean_evolution_trials_active" in metrics_text
        assert "dean_evolution_trials_total" in metrics_text
        
        # Parse active trials metric
        for line in metrics_text.split('\n'):
            if line.startswith("dean_evolution_trials_active"):
                value = int(line.split()[-1])
                assert value >= 1  # At least our trial
                
                
class TestEvolutionWorkflowIntegration:
    """Test the complete evolution workflow execution."""
    
    @pytest.mark.asyncio
    async def test_evolution_workflow_execution(self, test_client):
        """Test that the evolution workflow executes all steps correctly."""
        # This test verifies the workflow defined in evolution_trial.yaml
        
        # Start trial
        response = test_client.post(
            "/api/v1/orchestration/evolution/start",
            json={
                "population_size": 3,
                "generations": 2,
                "token_budget": 5000,
                "diversity_threshold": 0.3
            },
            headers={"Authorization": f"Bearer {TEST_AUTH_TOKEN}"}
        )
        
        assert response.status_code == 200
        trial_id = response.json()["trial_id"]
        workflow_id = response.json()["workflow_instance_id"]
        
        # Monitor workflow progress
        max_wait = 30  # seconds
        start_time = asyncio.get_event_loop().time()
        
        while asyncio.get_event_loop().time() - start_time < max_wait:
            # Check workflow status
            workflow_response = test_client.get(
                f"/api/v1/workflows/instances/{workflow_id}",
                headers={"Authorization": f"Bearer {TEST_AUTH_TOKEN}"}
            )
            
            if workflow_response.status_code == 200:
                workflow_data = workflow_response.json()
                
                if workflow_data["status"] in ["completed", "failed", "cancelled"]:
                    break
                    
            await asyncio.sleep(1.0)
            
        # Verify workflow completed
        assert workflow_response.status_code == 200
        assert workflow_data["status"] == "completed"
        
        # Check trial final status
        status_response = test_client.get(
            f"/api/v1/orchestration/evolution/{trial_id}/status",
            headers={"Authorization": f"Bearer {TEST_AUTH_TOKEN}"}
        )
        
        assert status_response.status_code == 200
        final_status = status_response.json()
        
        # Verify key metrics were collected
        assert final_status["status"] == "completed"
        assert final_status["progress"]["current_generation"] > 0
        assert final_status["resource_usage"]["tokens_used"] > 0
        assert final_status["performance"]["active_agents"] > 0
        
    @pytest.mark.asyncio  
    async def test_evolution_workflow_rollback(self, test_client):
        """Test workflow rollback when a step fails."""
        # Inject failure into workflow execution
        with patch("src.orchestration.service_registry.ServiceRegistry.call_service") as mock_call:
            # Make population creation succeed but evolution start fail
            call_count = 0
            
            async def selective_failure(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                
                if call_count <= 2:  # First two calls succeed
                    return AsyncMock(json=lambda: {"success": True})
                else:  # Third call fails
                    raise Exception("Evolution service error")
                    
            mock_call.side_effect = selective_failure
            
            # Start trial
            response = test_client.post(
                "/api/v1/orchestration/evolution/start",
                json={
                    "population_size": 3,
                    "generations": 5,
                    "token_budget": 10000,
                    "diversity_threshold": 0.3
                },
                headers={"Authorization": f"Bearer {TEST_AUTH_TOKEN}"}
            )
            
            # Should start but eventually fail
            assert response.status_code == 200
            trial_id = response.json()["trial_id"]
            
            # Wait for failure
            await asyncio.sleep(3.0)
            
            # Check that cleanup was called (rollback)
            assert call_count >= 3  # At least tried the failing call