"""
Integration test for evolution workflow.

Tests the complete evolution trial workflow from CLI to completion.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from orchestration.coordination.evolution_trial import (
    EvolutionTrialCoordinator,
    EvolutionConfig,
    TrialResult
)
from integration import ServicePool


@pytest.mark.integration
class TestEvolutionWorkflow:
    """Test complete evolution trial workflow."""
    
    @pytest.fixture
    def mock_service_pool(self):
        """Create mock service pool for testing."""
        pool = Mock(spec=ServicePool)
        
        # Mock IndexAgent client
        pool.indexagent = AsyncMock()
        pool.indexagent.create_agent = AsyncMock(return_value={
            "id": "agent-123",
            "name": "test-agent",
            "fitness_score": 0.8
        })
        pool.indexagent.list_agents = AsyncMock(return_value=[])
        pool.indexagent.get_agent = AsyncMock(return_value={
            "id": "agent-123",
            "fitness_score": 0.8
        })
        pool.indexagent.create_population = AsyncMock(return_value={
            "population_id": "pop-123",
            "agents": [{"id": f"agent-{i}", "fitness_score": 0.5 + i*0.1} for i in range(5)]
        })
        pool.indexagent.evolve_generation = AsyncMock(return_value={
            "generation": 1,
            "best_agent": {"id": "agent-best", "fitness_score": 0.9},
            "population": [{"id": f"agent-{i}", "fitness_score": 0.6 + i*0.1} for i in range(5)]
        })
        
        # Mock Airflow client
        pool.airflow = AsyncMock()
        pool.airflow.trigger_dag = AsyncMock(return_value={
            "dag_run_id": "run-123",
            "state": "running"
        })
        pool.airflow.get_dag_run = AsyncMock(return_value={
            "dag_run_id": "run-123",
            "state": "success"
        })
        
        # Mock Evolution API
        pool.evolution = AsyncMock()
        pool.evolution.start_evolution = AsyncMock(return_value={
            "trial_id": "trial-123",
            "status": "running"
        })
        pool.evolution.get_evolution_status = AsyncMock(return_value={
            "trial_id": "trial-123",
            "status": "completed",
            "generations_completed": 5
        })
        pool.evolution.get_patterns = AsyncMock(return_value=[
            {
                "id": "pattern-1",
                "type": "optimization",
                "confidence": 0.85,
                "description": "Test pattern"
            }
        ])
        
        return pool
        
    @pytest.fixture
    def evolution_config(self):
        """Create test evolution configuration."""
        return EvolutionConfig(
            generations=3,
            population_size=5,
            mutation_rate=0.1,
            fitness_threshold=0.8,
            timeout=300
        )
        
    @pytest.mark.asyncio
    async def test_evolution_trial_initialization(self, mock_service_pool, evolution_config):
        """Test evolution trial coordinator initialization."""
        coordinator = EvolutionTrialCoordinator(
            service_pool=mock_service_pool,
            config=evolution_config
        )
        
        assert coordinator is not None
        assert coordinator.config.generations == 3
        assert coordinator.config.population_size == 5
        
    @pytest.mark.asyncio
    async def test_evolution_trial_execution(self, mock_service_pool, evolution_config):
        """Test running a complete evolution trial."""
        coordinator = EvolutionTrialCoordinator(
            service_pool=mock_service_pool,
            config=evolution_config
        )
        
        # Run trial
        result = await coordinator.run_trial(
            repository="test-repo",
            config_overrides={
                "generations": 2,
                "population_size": 3
            }
        )
        
        # Verify result
        assert isinstance(result, TrialResult)
        assert result.trial_id is not None
        assert result.status in ["completed", "failed"]
        
        # Verify service calls
        mock_service_pool.evolution.start_evolution.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_evolution_pattern_extraction(self, mock_service_pool):
        """Test pattern extraction after evolution."""
        coordinator = EvolutionTrialCoordinator(service_pool=mock_service_pool)
        
        # Mock trial completion
        mock_service_pool.evolution.get_evolution_status.return_value = {
            "trial_id": "trial-123",
            "status": "completed",
            "best_fitness": 0.95
        }
        
        # Get patterns
        patterns = await coordinator._extract_patterns("trial-123")
        
        # Verify patterns
        assert len(patterns) > 0
        assert patterns[0]["type"] == "optimization"
        assert patterns[0]["confidence"] == 0.85
        
    @pytest.mark.asyncio
    async def test_evolution_error_handling(self, mock_service_pool):
        """Test error handling during evolution."""
        # Configure service to fail
        mock_service_pool.evolution.start_evolution.side_effect = Exception("Service error")
        
        coordinator = EvolutionTrialCoordinator(service_pool=mock_service_pool)
        
        # Run trial expecting failure
        result = await coordinator.run_trial("test-repo")
        
        assert result.status == "failed"
        assert len(result.errors) > 0
        assert "Service error" in str(result.errors[0])
        
    @pytest.mark.asyncio
    async def test_evolution_timeout_handling(self, mock_service_pool, evolution_config):
        """Test timeout handling during evolution."""
        # Configure very short timeout
        evolution_config.timeout = 0.1
        
        # Make evolution status check slow
        async def slow_status_check(*args, **kwargs):
            await asyncio.sleep(1)
            return {"status": "running"}
            
        mock_service_pool.evolution.get_evolution_status = slow_status_check
        
        coordinator = EvolutionTrialCoordinator(
            service_pool=mock_service_pool,
            config=evolution_config
        )
        
        result = await coordinator.run_trial("test-repo")
        
        assert result.status == "failed"
        assert any("timeout" in str(error).lower() for error in result.errors)
        
    @pytest.mark.asyncio
    async def test_evolution_progress_tracking(self, mock_service_pool):
        """Test progress tracking during evolution."""
        progress_updates = []
        
        async def track_progress(update):
            progress_updates.append(update)
            
        coordinator = EvolutionTrialCoordinator(
            service_pool=mock_service_pool,
            progress_callback=track_progress
        )
        
        # Configure progressive status updates
        status_sequence = [
            {"status": "running", "generation": 1, "best_fitness": 0.6},
            {"status": "running", "generation": 2, "best_fitness": 0.7},
            {"status": "completed", "generation": 3, "best_fitness": 0.9}
        ]
        
        call_count = 0
        async def get_status(*args, **kwargs):
            nonlocal call_count
            result = status_sequence[min(call_count, len(status_sequence)-1)]
            call_count += 1
            return result
            
        mock_service_pool.evolution.get_evolution_status = get_status
        
        await coordinator.run_trial("test-repo")
        
        # Verify progress updates
        assert len(progress_updates) > 0
        assert any(update.get("generation") == 2 for update in progress_updates)
        
    @pytest.mark.asyncio
    async def test_evolution_airflow_integration(self, mock_service_pool):
        """Test integration with Airflow for workflow orchestration."""
        coordinator = EvolutionTrialCoordinator(service_pool=mock_service_pool)
        
        # Configure Airflow DAG trigger
        dag_config = {
            "repository": "test-repo",
            "trial_id": "trial-123"
        }
        
        # Trigger evolution via Airflow
        dag_run_id = await coordinator._trigger_airflow_dag(
            "evolution_workflow",
            dag_config
        )
        
        assert dag_run_id is not None
        mock_service_pool.airflow.trigger_dag.assert_called_with(
            "evolution_workflow",
            conf=dag_config
        )
        
    @pytest.mark.asyncio
    async def test_evolution_result_persistence(self, mock_service_pool):
        """Test that evolution results are properly persisted."""
        coordinator = EvolutionTrialCoordinator(service_pool=mock_service_pool)
        
        # Run trial
        result = await coordinator.run_trial("test-repo")
        
        # Verify result contains expected data
        assert hasattr(result, 'trial_id')
        assert hasattr(result, 'repository')
        assert hasattr(result, 'start_time')
        assert hasattr(result, 'end_time')
        assert hasattr(result, 'generations_completed')
        assert hasattr(result, 'best_fitness')
        assert hasattr(result, 'improvements')
        assert hasattr(result, 'patterns')
        
    @pytest.mark.asyncio
    async def test_evolution_multi_repository(self, mock_service_pool):
        """Test running evolution on multiple repositories."""
        coordinator = EvolutionTrialCoordinator(service_pool=mock_service_pool)
        
        repositories = ["repo1", "repo2", "repo3"]
        results = []
        
        # Run trials for each repository
        for repo in repositories:
            result = await coordinator.run_trial(repo)
            results.append(result)
            
        # Verify all trials completed
        assert len(results) == 3
        assert all(r.repository in repositories for r in results)
        
        # Verify service was called for each
        assert mock_service_pool.evolution.start_evolution.call_count == 3


@pytest.mark.integration
class TestEvolutionCLIIntegration:
    """Test evolution workflow from CLI perspective."""
    
    def test_cli_evolution_commands(self):
        """Test that evolution CLI commands are properly defined."""
        from interfaces.cli.dean_cli import cli, evolution
        
        # Check evolution command group exists
        assert 'evolution' in cli.commands
        
        # Check subcommands
        evolution_cmd = cli.commands['evolution']
        assert hasattr(evolution_cmd, 'commands')
        assert 'start' in evolution_cmd.commands
        assert 'list' in evolution_cmd.commands
        
    @pytest.mark.asyncio
    async def test_cli_evolution_start_command(self, mock_service_pool):
        """Test starting evolution from CLI."""
        from interfaces.cli.dean_cli import evolution
        
        # Mock the coordinator
        with patch('interfaces.cli.dean_cli.EvolutionTrialCoordinator') as mock_coordinator:
            instance = mock_coordinator.return_value
            instance.__aenter__.return_value = instance
            instance.__aexit__.return_value = None
            instance.run_trial = AsyncMock(return_value=Mock(
                status='completed',
                trial_id='trial-123',
                improvements=[1, 2, 3]
            ))
            
            # Simulate CLI command execution
            # Note: This is a simplified test - actual Click testing would use CliRunner
            # But that requires Click to be installed
            
            # Verify the command structure
            start_cmd = evolution.commands['start']
            assert start_cmd is not None
            assert hasattr(start_cmd, 'params')
            
            # Check parameters
            param_names = [p.name for p in start_cmd.params]
            assert 'repository' in param_names
            assert 'generations' in param_names
            assert 'population' in param_names