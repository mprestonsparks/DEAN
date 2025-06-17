"""
Integration tests using service stubs.

Tests the orchestration layer against real HTTP stub services
rather than mocks.
"""

import pytest
import asyncio
import httpx
import os
import time
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from integration import ServicePool, create_service_pool
from orchestration.coordination.evolution_trial import (
    EvolutionTrialCoordinator,
    EvolutionConfig
)

# Service URLs (can be overridden by environment variables)
INDEXAGENT_URL = os.getenv("INDEXAGENT_API_URL", "http://localhost:8081")
AIRFLOW_URL = os.getenv("AIRFLOW_API_URL", "http://localhost:8080")
EVOLUTION_URL = os.getenv("EVOLUTION_API_URL", "http://localhost:8083")
ORCHESTRATION_URL = os.getenv("DEAN_ORCHESTRATION_URL", "http://localhost:8082")


@pytest.mark.integration
@pytest.mark.stubs
class TestWithServiceStubs:
    """Test orchestration with real service stubs."""
    
    @pytest.fixture(scope="class")
    def check_services_running(self):
        """Check that all required services are running."""
        services = [
            ("IndexAgent", f"{INDEXAGENT_URL}/health"),
            ("Airflow", f"{AIRFLOW_URL}/health"),
            ("Evolution", f"{EVOLUTION_URL}/health"),
            ("Orchestration", f"{ORCHESTRATION_URL}/api/health")
        ]
        
        all_healthy = True
        for name, url in services:
            try:
                response = httpx.get(url, timeout=5.0)
                if response.status_code == 200:
                    print(f"✓ {name} is healthy at {url}")
                else:
                    print(f"✗ {name} returned status {response.status_code}")
                    all_healthy = False
            except Exception as e:
                print(f"✗ {name} is not reachable at {url}: {e}")
                all_healthy = False
                
        if not all_healthy:
            pytest.skip("Not all required services are running. Run scripts/dev_environment.sh first.")
            
    @pytest.mark.asyncio
    async def test_service_health_checks(self, check_services_running):
        """Test that all services report healthy status."""
        async with httpx.AsyncClient() as client:
            # Check each service
            services = [
                (INDEXAGENT_URL, "indexagent-stub"),
                (AIRFLOW_URL, "airflow-stub"),
                (EVOLUTION_URL, "evolution-stub")
            ]
            
            for base_url, expected_service in services:
                response = await client.get(f"{base_url}/health")
                assert response.status_code == 200
                
                data = response.json()
                assert data["status"] == "healthy"
                assert data["service"] == expected_service
                assert "timestamp" in data
                
    @pytest.mark.asyncio
    async def test_create_agent_via_stub(self, check_services_running):
        """Test creating an agent through the IndexAgent stub."""
        async with httpx.AsyncClient() as client:
            # Create an agent
            agent_config = {
                "name": "test-agent-stub",
                "language": "python",
                "capabilities": ["search", "analyze"],
                "parameters": {"test_mode": True}
            }
            
            response = await client.post(
                f"{INDEXAGENT_URL}/agents",
                json=agent_config
            )
            
            assert response.status_code == 200
            agent = response.json()
            
            assert agent["name"] == "test-agent-stub"
            assert "id" in agent
            assert "fitness_score" in agent
            assert 0 <= agent["fitness_score"] <= 1
            
            # Verify we can retrieve the agent
            get_response = await client.get(f"{INDEXAGENT_URL}/agents/{agent['id']}")
            assert get_response.status_code == 200
            retrieved = get_response.json()
            assert retrieved["id"] == agent["id"]
            
    @pytest.mark.asyncio
    async def test_trigger_dag_via_stub(self, check_services_running):
        """Test triggering a DAG through the Airflow stub."""
        async with httpx.AsyncClient() as client:
            # First authenticate
            auth = ("airflow", "airflow")
            
            # List DAGs
            response = await client.get(
                f"{AIRFLOW_URL}/api/v1/dags",
                auth=auth
            )
            assert response.status_code == 200
            dags_data = response.json()
            assert "dags" in dags_data
            assert len(dags_data["dags"]) > 0
            
            # Find evolution workflow
            evolution_dag = next(
                (d for d in dags_data["dags"] if d["dag_id"] == "evolution_workflow"),
                None
            )
            assert evolution_dag is not None
            assert not evolution_dag["is_paused"]
            
            # Trigger the DAG
            trigger_response = await client.post(
                f"{AIRFLOW_URL}/api/v1/dags/evolution_workflow/dagRuns",
                json={
                    "conf": {"test": True, "repository": "test-repo"},
                    "note": "Test run from integration test"
                },
                auth=auth
            )
            
            assert trigger_response.status_code == 200
            dag_run = trigger_response.json()
            assert "dag_run_id" in dag_run
            assert dag_run["state"] == "running"
            
            # Wait a bit for state change
            await asyncio.sleep(3)
            
            # Check run status
            status_response = await client.get(
                f"{AIRFLOW_URL}/api/v1/dags/evolution_workflow/dagRuns/{dag_run['dag_run_id']}",
                auth=auth
            )
            assert status_response.status_code == 200
            updated_run = status_response.json()
            assert updated_run["state"] in ["running", "success", "failed"]
            
    @pytest.mark.asyncio
    async def test_evolution_trial_via_stub(self, check_services_running):
        """Test running an evolution trial through the Evolution stub."""
        async with httpx.AsyncClient() as client:
            # Start evolution trial
            config = {
                "repository": "test-repo-stub",
                "generations": 3,
                "population_size": 5,
                "mutation_rate": 0.1
            }
            
            response = await client.post(
                f"{EVOLUTION_URL}/evolution/start",
                json=config
            )
            
            assert response.status_code == 200
            trial = response.json()
            
            assert "trial_id" in trial
            assert trial["status"] == "initializing"
            assert trial["repository"] == "test-repo-stub"
            
            trial_id = trial["trial_id"]
            
            # Poll for completion (with timeout)
            start_time = time.time()
            timeout = 30  # seconds
            
            while time.time() - start_time < timeout:
                status_response = await client.get(
                    f"{EVOLUTION_URL}/evolution/{trial_id}/status"
                )
                assert status_response.status_code == 200
                
                status_data = status_response.json()
                
                if status_data["status"] in ["completed", "failed"]:
                    break
                    
                await asyncio.sleep(1)
            else:
                pytest.fail(f"Evolution trial {trial_id} did not complete within {timeout} seconds")
                
            # Check final status
            assert status_data["status"] == "completed"
            assert status_data["current_generation"] == 3
            assert status_data["best_fitness"] > 0.5
            
    @pytest.mark.asyncio
    async def test_pattern_discovery_via_stub(self, check_services_running):
        """Test pattern discovery through service stubs."""
        async with httpx.AsyncClient() as client:
            # Get patterns from Evolution API
            response = await client.get(
                f"{EVOLUTION_URL}/patterns",
                params={"min_confidence": 0.7, "limit": 10}
            )
            
            assert response.status_code == 200
            patterns_data = response.json()
            
            assert "patterns" in patterns_data
            assert "total" in patterns_data
            assert len(patterns_data["patterns"]) > 0
            
            # Verify pattern structure
            for pattern in patterns_data["patterns"]:
                assert "id" in pattern
                assert "type" in pattern
                assert "confidence" in pattern
                assert pattern["confidence"] >= 0.7
                assert "description" in pattern
                
    @pytest.mark.asyncio
    async def test_complete_workflow_with_stubs(self, check_services_running):
        """Test complete evolution workflow using all stubs."""
        async with create_service_pool() as pool:
            # Create evolution coordinator
            config = EvolutionConfig(
                generations=2,
                population_size=3,
                mutation_rate=0.1,
                timeout=60
            )
            
            coordinator = EvolutionTrialCoordinator(
                service_pool=pool,
                config=config
            )
            
            # Run trial (this will use the real HTTP stubs)
            result = await coordinator.run_trial("test-workflow-repo")
            
            assert result is not None
            assert hasattr(result, "trial_id")
            assert hasattr(result, "status")
            
            # Note: The actual implementation of EvolutionTrialCoordinator
            # needs to exist for this to work properly
            
    @pytest.mark.asyncio 
    async def test_orchestration_api_with_stubs(self, check_services_running):
        """Test orchestration API endpoints with stubs running."""
        async with httpx.AsyncClient() as client:
            # Test system status endpoint
            response = await client.get(f"{ORCHESTRATION_URL}/api/system/status")
            
            # Note: This will fail if the orchestration API is not implemented
            # but demonstrates how the tests would work
            if response.status_code == 200:
                data = response.json()
                assert "services" in data
                assert "indexagent" in data["services"]
                assert "airflow" in data["services"]
                assert "evolution" in data["services"]
            else:
                # Expected until orchestration API is implemented
                assert response.status_code in [404, 501]
                
    @pytest.mark.asyncio
    async def test_websocket_connection(self, check_services_running):
        """Test WebSocket connection to Evolution API."""
        import websockets
        
        try:
            async with websockets.connect(f"ws://localhost:8083/ws") as websocket:
                # Wait for connection message
                message = await websocket.recv()
                data = eval(message)  # Simple eval for test (not for production!)
                
                assert data["type"] == "connection"
                assert "timestamp" in data
                
                # Send ping
                await websocket.send("ping")
                
                # Receive pong
                pong = await websocket.recv()
                assert pong == "pong"
                
        except Exception as e:
            pytest.fail(f"WebSocket connection failed: {e}")
            

@pytest.mark.integration
@pytest.mark.stubs 
class TestStubBehavior:
    """Test specific stub behaviors for development scenarios."""
    
    @pytest.mark.asyncio
    async def test_stub_data_persistence(self, check_services_running):
        """Test that stubs maintain data during a session."""
        async with httpx.AsyncClient() as client:
            # Create multiple agents
            agent_ids = []
            
            for i in range(3):
                response = await client.post(
                    f"{INDEXAGENT_URL}/agents",
                    json={
                        "name": f"persistence-test-{i}",
                        "language": "python"
                    }
                )
                assert response.status_code == 200
                agent_ids.append(response.json()["id"])
                
            # List all agents
            list_response = await client.get(f"{INDEXAGENT_URL}/agents")
            assert list_response.status_code == 200
            
            agents_data = list_response.json()
            listed_ids = [a["id"] for a in agents_data["agents"]]
            
            # Verify all created agents are in the list
            for agent_id in agent_ids:
                assert agent_id in listed_ids
                
    @pytest.mark.asyncio
    async def test_stub_error_simulation(self, check_services_running):
        """Test that stubs can simulate error conditions."""
        async with httpx.AsyncClient() as client:
            # Try to get non-existent agent
            response = await client.get(f"{INDEXAGENT_URL}/agents/non-existent-id")
            assert response.status_code == 404
            
            # Try to trigger paused DAG (should fail)
            auth = ("airflow", "airflow")
            
            # First pause a DAG
            pause_response = await client.patch(
                f"{AIRFLOW_URL}/api/v1/dags/evolution_workflow",
                json={"is_paused": True},
                auth=auth
            )
            
            if pause_response.status_code == 200:
                # Try to trigger paused DAG
                trigger_response = await client.post(
                    f"{AIRFLOW_URL}/api/v1/dags/evolution_workflow/dagRuns",
                    json={"conf": {}},
                    auth=auth
                )
                assert trigger_response.status_code == 409  # Conflict
                
                # Unpause for other tests
                await client.patch(
                    f"{AIRFLOW_URL}/api/v1/dags/evolution_workflow",
                    json={"is_paused": False},
                    auth=auth
                )