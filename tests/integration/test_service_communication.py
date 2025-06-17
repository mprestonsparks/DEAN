"""Integration tests for service communication."""

import pytest
import asyncio

from integration import ServicePool, create_service_pool


@pytest.mark.integration
@pytest.mark.mock_services
class TestServiceCommunication:
    """Test communication between services using mocks."""
    
    @pytest.mark.asyncio
    async def test_health_check_all_services(self, all_mock_services, test_config):
        """Test health checking all services."""
        async with create_service_pool(**test_config['service_endpoints']) as pool:
            health_status = await pool.health.check_all_services()
            
            assert health_status['status'] == 'healthy'
            assert 'indexagent' in health_status['services']
            assert 'airflow' in health_status['services']
            assert 'evolution' in health_status['services']
            
            for service, status in health_status['services'].items():
                assert status.get('status') == 'healthy'
    
    @pytest.mark.asyncio
    async def test_evolution_workflow(self, all_mock_services, test_config):
        """Test complete evolution workflow."""
        async with create_service_pool(**test_config['service_endpoints']) as pool:
            # Execute evolution trial
            result = await pool.workflow.execute_evolution_trial(
                population_size=5,
                generations=3,
                agent_type="optimization",
                wait_for_completion=False  # Don't wait in tests
            )
            
            assert result['status'] == 'workflow_triggered'
            assert result['population_id'] is not None
            assert result['trial_id'] is not None
            assert result['dag_run_id'] is not None
    
    @pytest.mark.asyncio
    async def test_pattern_propagation(self, all_mock_services, test_config):
        """Test pattern propagation between services."""
        async with create_service_pool(**test_config['service_endpoints']) as pool:
            # Start evolution to generate patterns
            evolution_result = await pool.evolution.start_evolution(
                population_size=5,
                generations=2
            )
            trial_id = evolution_result['trial_id']
            
            # Wait a bit for mock evolution to generate patterns
            await asyncio.sleep(3)
            
            # Get patterns
            patterns = await pool.evolution.get_patterns(trial_id=trial_id)
            assert len(patterns) > 0
            
            # Propagate patterns
            propagation_result = await pool.patterns.propagate_successful_patterns(
                trial_id=trial_id,
                min_effectiveness=0.7
            )
            
            assert propagation_result['status'] in ['patterns_propagated', 'no_patterns_found']
    
    @pytest.mark.asyncio
    async def test_service_error_handling(self, test_config):
        """Test error handling when services are unavailable."""
        # Use wrong ports to simulate unavailable services
        bad_config = {
            'indexagent': 'http://localhost:19999',
            'airflow': 'http://localhost:19998',
            'evolution': 'http://localhost:19997',
        }
        
        async with create_service_pool(**bad_config) as pool:
            health_status = await pool.health.check_all_services()
            
            assert health_status['status'] == 'unhealthy'
            
            for service, status in health_status['services'].items():
                assert status.get('status') == 'unhealthy'
                assert 'error' in status
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self, all_mock_services, test_config):
        """Test concurrent operations across services."""
        async with create_service_pool(**test_config['service_endpoints']) as pool:
            # Run multiple operations concurrently
            tasks = [
                pool.indexagent.list_agents(),
                pool.airflow.list_dags(),
                pool.evolution.get_patterns(),
                pool.health.check_all_services()
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Verify all operations succeeded
            for result in results:
                assert not isinstance(result, Exception)
    
    @pytest.mark.asyncio
    async def test_agent_creation_and_retrieval(self, all_mock_services, test_config):
        """Test creating and retrieving agents."""
        async with create_service_pool(**test_config['service_endpoints']) as pool:
            # Create an agent
            agent_config = {
                "name": "Test Agent",
                "type": "optimization",
                "parameters": {
                    "target": "performance"
                }
            }
            
            created_agent = await pool.indexagent.create_agent(agent_config)
            assert 'id' in created_agent
            
            # Retrieve the agent
            agent_id = created_agent['id']
            retrieved_agent = await pool.indexagent.get_agent(agent_id)
            
            assert retrieved_agent['id'] == agent_id
            assert retrieved_agent['name'] == "Test Agent"
    
    @pytest.mark.asyncio
    async def test_dag_execution_monitoring(self, all_mock_services, test_config):
        """Test DAG execution and monitoring."""
        async with create_service_pool(**test_config['service_endpoints']) as pool:
            # Trigger a DAG
            dag_run = await pool.airflow.trigger_dag(
                "evolution_workflow",
                conf={"test": True}
            )
            
            dag_run_id = dag_run['dag_run_id']
            
            # Check initial status
            status = await pool.airflow.get_dag_run(
                "evolution_workflow",
                dag_run_id
            )
            
            assert status['state'] in ['running', 'queued']
            
            # Wait for completion (mock completes quickly)
            await asyncio.sleep(3)
            
            # Check final status
            final_status = await pool.airflow.get_dag_run(
                "evolution_workflow",
                dag_run_id
            )
            
            assert final_status['state'] == 'success'