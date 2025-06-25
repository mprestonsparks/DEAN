"""Comprehensive test suite for WorkflowCoordinator."""

import asyncio
import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.orchestration.workflow_models import (
    WorkflowDefinition, WorkflowInstance, WorkflowStep, WorkflowStatus,
    StepStatus, StepType, ServiceCallConfig, RetryPolicy, ConditionalConfig
)
from src.orchestration.workflow_coordinator import (
    WorkflowCoordinator, create_evolution_trial_workflow
)
from src.orchestration.workflow_executor import WorkflowExecutor
from src.orchestration.service_registry import ServiceRegistry


@pytest.fixture
async def mock_service_registry():
    """Create a mock service registry."""
    registry = AsyncMock(spec=ServiceRegistry)
    registry.call_service = AsyncMock()
    return registry


@pytest.fixture
async def coordinator(mock_service_registry):
    """Create a workflow coordinator without Redis."""
    coord = WorkflowCoordinator(
        service_registry=mock_service_registry,
        enable_persistence=False
    )
    await coord.start()
    yield coord
    await coord.stop()


@pytest.fixture
def simple_workflow():
    """Create a simple test workflow."""
    return WorkflowDefinition(
        name="Test Workflow",
        description="Simple test workflow",
        steps=[
            WorkflowStep(
                id="step1",
                name="First Step",
                type=StepType.SERVICE_CALL,
                service_call=ServiceCallConfig(
                    service_name="TestService",
                    endpoint="/api/test",
                    method="GET"
                )
            ),
            WorkflowStep(
                id="step2",
                name="Second Step",
                type=StepType.SERVICE_CALL,
                depends_on=["step1"],
                service_call=ServiceCallConfig(
                    service_name="TestService",
                    endpoint="/api/test2",
                    method="POST",
                    body={"data": "{{step_step1_result}}"}
                )
            )
        ]
    )


@pytest.fixture
def complex_workflow():
    """Create a complex workflow with various step types."""
    return WorkflowDefinition(
        name="Complex Workflow",
        description="Complex workflow with multiple step types",
        steps=[
            WorkflowStep(
                id="validate",
                name="Validate Input",
                type=StepType.SERVICE_CALL,
                service_call=ServiceCallConfig(
                    service_name="ValidationService",
                    endpoint="/validate",
                    method="POST",
                    body={"input": "{{input_data}}"}
                ),
                retry_policy=RetryPolicy(max_attempts=3)
            ),
            WorkflowStep(
                id="check_condition",
                name="Check Condition",
                type=StepType.CONDITIONAL,
                depends_on=["validate"],
                conditional=ConditionalConfig(
                    condition="step_validate_result.valid == true",
                    if_true="process_data",
                    if_false="handle_error"
                )
            ),
            WorkflowStep(
                id="process_data",
                name="Process Data",
                type=StepType.SERVICE_CALL,
                depends_on=["check_condition"],
                service_call=ServiceCallConfig(
                    service_name="ProcessingService",
                    endpoint="/process",
                    method="POST"
                ),
                on_failure="rollback"
            ),
            WorkflowStep(
                id="handle_error",
                name="Handle Error",
                type=StepType.SERVICE_CALL,
                depends_on=["check_condition"],
                service_call=ServiceCallConfig(
                    service_name="ErrorService",
                    endpoint="/error",
                    method="POST"
                ),
                skip_on_failure=True
            ),
            WorkflowStep(
                id="wait",
                name="Wait for Processing",
                type=StepType.WAIT,
                depends_on=["process_data"],
                wait_seconds=2.0
            ),
            WorkflowStep(
                id="rollback",
                name="Rollback Changes",
                type=StepType.SERVICE_CALL,
                service_call=ServiceCallConfig(
                    service_name="ProcessingService",
                    endpoint="/rollback",
                    method="POST"
                )
            )
        ]
    )


class TestWorkflowCoordinator:
    """Test WorkflowCoordinator functionality."""
    
    @pytest.mark.asyncio
    async def test_create_workflow(self, coordinator, simple_workflow):
        """Test workflow creation."""
        # Create workflow
        created = await coordinator.create_workflow(simple_workflow)
        
        assert created.id == simple_workflow.id
        assert created.name == "Test Workflow"
        assert len(created.steps) == 2
        
        # Verify workflow is stored
        assert simple_workflow.id in coordinator._workflows
        
    @pytest.mark.asyncio
    async def test_create_workflow_from_yaml(self, coordinator):
        """Test workflow creation from YAML string."""
        yaml_workflow = """
name: YAML Test Workflow
version: "1.0.0"
steps:
  - id: step1
    name: First Step
    type: service_call
    service_call:
      service_name: TestService
      endpoint: /api/test
      method: GET
"""
        
        workflow = await coordinator.create_workflow(yaml_workflow)
        
        assert workflow.name == "YAML Test Workflow"
        assert len(workflow.steps) == 1
        assert workflow.steps[0].type == StepType.SERVICE_CALL
        
    @pytest.mark.asyncio
    async def test_start_workflow(self, coordinator, simple_workflow, mock_service_registry):
        """Test starting a workflow execution."""
        # Mock service responses
        mock_service_registry.call_service.side_effect = [
            Mock(json=lambda: {"result": "success"}),
            Mock(json=lambda: {"processed": True})
        ]
        
        # Create and start workflow
        await coordinator.create_workflow(simple_workflow)
        instance = await coordinator.start_workflow(
            simple_workflow.id,
            context={"test": "value"}
        )
        
        assert instance.workflow_id == simple_workflow.id
        assert instance.status == WorkflowStatus.RUNNING
        assert instance.context["test"] == "value"
        assert instance.id in coordinator._instances
        
        # Wait for completion
        await asyncio.sleep(0.5)
        
        # Check service calls were made
        assert mock_service_registry.call_service.call_count == 2
        
    @pytest.mark.asyncio
    async def test_workflow_with_retry(self, coordinator, mock_service_registry):
        """Test workflow step retry on failure."""
        # Create workflow with retry
        workflow = WorkflowDefinition(
            name="Retry Test",
            steps=[
                WorkflowStep(
                    id="retry_step",
                    name="Retry Step",
                    type=StepType.SERVICE_CALL,
                    service_call=ServiceCallConfig(
                        service_name="TestService",
                        endpoint="/api/test"
                    ),
                    retry_policy=RetryPolicy(
                        max_attempts=3,
                        initial_delay_seconds=0.1
                    )
                )
            ]
        )
        
        # Mock service to fail twice then succeed
        mock_service_registry.call_service.side_effect = [
            Exception("First failure"),
            Exception("Second failure"),
            Mock(json=lambda: {"success": True})
        ]
        
        # Execute workflow
        await coordinator.create_workflow(workflow)
        instance = await coordinator.start_workflow(workflow.id)
        
        # Wait for completion
        await asyncio.sleep(1.0)
        
        # Verify retries happened
        assert mock_service_registry.call_service.call_count == 3
        
        # Check final status
        updated_instance = await coordinator.get_workflow_status(instance.id)
        assert updated_instance.status == WorkflowStatus.COMPLETED
        
    @pytest.mark.asyncio
    async def test_workflow_rollback(self, coordinator, mock_service_registry):
        """Test workflow rollback on failure."""
        # Create workflow with rollback
        workflow = WorkflowDefinition(
            name="Rollback Test",
            steps=[
                WorkflowStep(
                    id="main_step",
                    name="Main Step",
                    type=StepType.SERVICE_CALL,
                    service_call=ServiceCallConfig(
                        service_name="TestService",
                        endpoint="/api/process"
                    ),
                    on_failure="rollback_step"
                ),
                WorkflowStep(
                    id="failing_step",
                    name="Failing Step",
                    type=StepType.SERVICE_CALL,
                    depends_on=["main_step"],
                    service_call=ServiceCallConfig(
                        service_name="TestService",
                        endpoint="/api/fail"
                    )
                ),
                WorkflowStep(
                    id="rollback_step",
                    name="Rollback Step",
                    type=StepType.SERVICE_CALL,
                    service_call=ServiceCallConfig(
                        service_name="TestService",
                        endpoint="/api/rollback"
                    )
                )
            ]
        )
        
        # Mock service responses
        mock_service_registry.call_service.side_effect = [
            Mock(json=lambda: {"success": True}),  # main_step succeeds
            Exception("Step failed"),  # failing_step fails
            Mock(json=lambda: {"rolled_back": True})  # rollback_step
        ]
        
        # Execute workflow
        await coordinator.create_workflow(workflow)
        instance = await coordinator.start_workflow(workflow.id)
        
        # Wait for completion
        await asyncio.sleep(1.0)
        
        # Verify rollback was called
        assert mock_service_registry.call_service.call_count == 3
        
        # Check instance status
        updated_instance = await coordinator.get_workflow_status(instance.id)
        assert updated_instance.status == WorkflowStatus.ROLLED_BACK
        assert "main_step" in updated_instance.rollback_completed
        
    @pytest.mark.asyncio
    async def test_parallel_step_execution(self, coordinator, mock_service_registry):
        """Test parallel step execution."""
        # Create workflow with parallel steps
        workflow = WorkflowDefinition(
            name="Parallel Test",
            steps=[
                WorkflowStep(
                    id="parallel_group",
                    name="Parallel Group",
                    type=StepType.PARALLEL,
                    parallel_steps=["step1", "step2", "step3"]
                ),
                WorkflowStep(
                    id="step1",
                    name="Parallel Step 1",
                    type=StepType.SERVICE_CALL,
                    service_call=ServiceCallConfig(
                        service_name="Service1",
                        endpoint="/api/1"
                    )
                ),
                WorkflowStep(
                    id="step2",
                    name="Parallel Step 2",
                    type=StepType.SERVICE_CALL,
                    service_call=ServiceCallConfig(
                        service_name="Service2",
                        endpoint="/api/2"
                    )
                ),
                WorkflowStep(
                    id="step3",
                    name="Parallel Step 3",
                    type=StepType.SERVICE_CALL,
                    service_call=ServiceCallConfig(
                        service_name="Service3",
                        endpoint="/api/3"
                    )
                )
            ]
        )
        
        # Track call times
        call_times = []
        
        async def mock_call(*args, **kwargs):
            call_times.append(datetime.utcnow())
            await asyncio.sleep(0.1)
            return Mock(json=lambda: {"result": "success"})
            
        mock_service_registry.call_service.side_effect = mock_call
        
        # Execute workflow
        await coordinator.create_workflow(workflow)
        instance = await coordinator.start_workflow(workflow.id)
        
        # Wait for completion
        await asyncio.sleep(0.5)
        
        # Verify parallel execution
        assert len(call_times) == 3
        # Check that calls were made close together (parallel)
        time_diff = (call_times[-1] - call_times[0]).total_seconds()
        assert time_diff < 0.2  # Should be much less than 0.3 (sequential)
        
    @pytest.mark.asyncio
    async def test_conditional_workflow(self, coordinator, mock_service_registry):
        """Test conditional workflow execution."""
        # Create conditional workflow
        workflow = WorkflowDefinition(
            name="Conditional Test",
            steps=[
                WorkflowStep(
                    id="check",
                    name="Check Value",
                    type=StepType.SERVICE_CALL,
                    service_call=ServiceCallConfig(
                        service_name="CheckService",
                        endpoint="/check"
                    )
                ),
                WorkflowStep(
                    id="condition",
                    name="Conditional",
                    type=StepType.CONDITIONAL,
                    depends_on=["check"],
                    conditional=ConditionalConfig(
                        condition="exists:step_check_result.valid",
                        if_true="true_branch",
                        if_false="false_branch"
                    )
                ),
                WorkflowStep(
                    id="true_branch",
                    name="True Branch",
                    type=StepType.SERVICE_CALL,
                    depends_on=["condition"],
                    service_call=ServiceCallConfig(
                        service_name="TrueService",
                        endpoint="/true"
                    )
                ),
                WorkflowStep(
                    id="false_branch",
                    name="False Branch",
                    type=StepType.SERVICE_CALL,
                    depends_on=["condition"],
                    service_call=ServiceCallConfig(
                        service_name="FalseService",
                        endpoint="/false"
                    )
                )
            ]
        )
        
        # Mock service to return valid=true
        mock_service_registry.call_service.side_effect = [
            Mock(json=lambda: {"valid": True}),
            Mock(json=lambda: {"branch": "true"})
        ]
        
        # Execute workflow
        await coordinator.create_workflow(workflow)
        instance = await coordinator.start_workflow(workflow.id)
        
        # Wait for completion
        await asyncio.sleep(0.5)
        
        # Verify only true branch was called
        calls = mock_service_registry.call_service.call_args_list
        assert len(calls) == 2
        assert calls[1][0][1] == "/true"  # True branch endpoint
        
    @pytest.mark.asyncio
    async def test_workflow_cancellation(self, coordinator, mock_service_registry):
        """Test workflow cancellation."""
        # Create long-running workflow
        workflow = WorkflowDefinition(
            name="Cancellation Test",
            steps=[
                WorkflowStep(
                    id="long_step",
                    name="Long Running Step",
                    type=StepType.WAIT,
                    wait_seconds=10.0
                )
            ]
        )
        
        # Start workflow
        await coordinator.create_workflow(workflow)
        instance = await coordinator.start_workflow(workflow.id)
        
        # Wait a bit then cancel
        await asyncio.sleep(0.1)
        cancelled = await coordinator.cancel_workflow(instance.id)
        
        assert cancelled is True
        
        # Check status
        updated_instance = await coordinator.get_workflow_status(instance.id)
        assert updated_instance.status == WorkflowStatus.CANCELLED
        
    @pytest.mark.asyncio
    async def test_workflow_resumption(self, coordinator, mock_service_registry):
        """Test resuming a failed workflow."""
        # Create workflow
        workflow = WorkflowDefinition(
            name="Resume Test",
            steps=[
                WorkflowStep(
                    id="step1",
                    name="First Step",
                    type=StepType.SERVICE_CALL,
                    service_call=ServiceCallConfig(
                        service_name="Service1",
                        endpoint="/api/1"
                    )
                ),
                WorkflowStep(
                    id="step2",
                    name="Second Step",
                    type=StepType.SERVICE_CALL,
                    depends_on=["step1"],
                    service_call=ServiceCallConfig(
                        service_name="Service2",
                        endpoint="/api/2"
                    )
                )
            ]
        )
        
        # Mock first execution to fail on second step
        mock_service_registry.call_service.side_effect = [
            Mock(json=lambda: {"success": True}),
            Exception("Step 2 failed")
        ]
        
        # Start workflow
        await coordinator.create_workflow(workflow)
        instance = await coordinator.start_workflow(workflow.id)
        
        # Wait for failure
        await asyncio.sleep(0.5)
        
        # Verify failed status
        assert instance.status == WorkflowStatus.FAILED
        
        # Mock successful execution for resume
        mock_service_registry.call_service.side_effect = [
            Mock(json=lambda: {"success": True})
        ]
        
        # Resume workflow
        resumed_instance = await coordinator.resume_workflow(instance.id)
        
        # Wait for completion
        await asyncio.sleep(0.5)
        
        # Check completion
        final_instance = await coordinator.get_workflow_status(instance.id)
        assert final_instance.status == WorkflowStatus.COMPLETED
        
    @pytest.mark.asyncio
    async def test_list_workflows(self, coordinator, simple_workflow):
        """Test listing workflow instances."""
        # Create and start multiple workflows
        await coordinator.create_workflow(simple_workflow)
        
        instances = []
        for i in range(3):
            instance = await coordinator.start_workflow(simple_workflow.id)
            instances.append(instance)
            
        # List all workflows
        all_workflows = await coordinator.list_workflows()
        assert len(all_workflows) >= 3
        
        # List by status
        running_workflows = await coordinator.list_workflows(
            status=WorkflowStatus.RUNNING
        )
        assert all(w.status == WorkflowStatus.RUNNING for w in running_workflows)
        
    @pytest.mark.asyncio
    async def test_workflow_metrics(self, coordinator, simple_workflow):
        """Test workflow metrics collection."""
        # Create and start workflow
        await coordinator.create_workflow(simple_workflow)
        instance = await coordinator.start_workflow(simple_workflow.id)
        
        # Get metrics
        metrics = coordinator.get_workflow_metrics()
        
        assert metrics["total_workflows"] == 1
        assert metrics["total_instances"] == 1
        assert metrics["running_instances"] == 1
        assert "status_breakdown" in metrics
        

class TestWorkflowPersistence:
    """Test workflow persistence with Redis."""
    
    @pytest.mark.asyncio
    async def test_redis_persistence(self):
        """Test workflow persistence to Redis."""
        # Mock Redis
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        mock_redis.hset = AsyncMock()
        mock_redis.hgetall = AsyncMock(return_value={})
        mock_redis.sadd = AsyncMock()
        
        with patch('redis.asyncio.from_url', return_value=mock_redis):
            # Create coordinator with persistence
            registry = AsyncMock(spec=ServiceRegistry)
            coordinator = WorkflowCoordinator(
                service_registry=registry,
                redis_url="redis://localhost",
                enable_persistence=True
            )
            await coordinator.start()
            
            # Create workflow
            workflow = WorkflowDefinition(
                name="Persistent Workflow",
                steps=[
                    WorkflowStep(
                        id="step1",
                        name="Step 1",
                        type=StepType.WAIT,
                        wait_seconds=1.0
                    )
                ]
            )
            
            await coordinator.create_workflow(workflow)
            
            # Verify Redis was called
            mock_redis.hset.assert_called()
            call_args = mock_redis.hset.call_args
            assert call_args[0][0] == "dean:workflows"
            assert call_args[0][1] == workflow.id
            
            await coordinator.stop()
            

class TestEvolutionTrialWorkflow:
    """Test the pre-built evolution trial workflow."""
    
    def test_create_evolution_trial_workflow(self):
        """Test creating evolution trial workflow."""
        workflow = create_evolution_trial_workflow()
        
        assert workflow.name == "Evolution Trial"
        assert len(workflow.steps) > 5
        
        # Check key steps exist
        step_ids = {step.id for step in workflow.steps}
        assert "validate_budget" in step_ids
        assert "create_population" in step_ids
        assert "start_evolution" in step_ids
        assert "trigger_airflow" in step_ids
        assert "collect_patterns" in step_ids
        assert "update_allocations" in step_ids
        
        # Check compensation step
        assert "cleanup_population" in step_ids
        
        # Verify dependencies
        create_pop_step = next(s for s in workflow.steps if s.id == "create_population")
        assert "validate_budget" in create_pop_step.depends_on
        assert create_pop_step.on_failure == "cleanup_population"