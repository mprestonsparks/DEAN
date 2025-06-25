"""Workflow Coordinator for DEAN orchestration system.

This module provides high-level workflow management, including
workflow lifecycle management, state persistence, and API integration.
"""

import asyncio
import json
import yaml
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import logging
import redis.asyncio as redis
from pathlib import Path

from .workflow_models import (
    WorkflowDefinition, WorkflowInstance, WorkflowStatus,
    WorkflowTemplate, WorkflowEvent, StepType, ServiceCallConfig,
    RetryPolicy, WorkflowStep, ConditionalConfig, TransformConfig
)
from .workflow_executor import WorkflowExecutor
from .service_registry import ServiceRegistry

logger = logging.getLogger(__name__)


class WorkflowCoordinator:
    """Coordinates workflow execution with state management and persistence."""
    
    def __init__(
        self,
        service_registry: ServiceRegistry,
        redis_url: Optional[str] = None,
        enable_persistence: bool = True,
        workflow_templates_path: Optional[str] = None
    ):
        """Initialize workflow coordinator.
        
        Args:
            service_registry: ServiceRegistry for service discovery
            redis_url: Redis URL for state persistence
            enable_persistence: Enable Redis-based persistence
            workflow_templates_path: Path to workflow template files
        """
        self.service_registry = service_registry
        self.redis_url = redis_url
        self.enable_persistence = enable_persistence
        self.workflow_templates_path = workflow_templates_path
        
        self._redis: Optional[redis.Redis] = None
        self._executor = WorkflowExecutor(service_registry)
        self._workflows: Dict[str, WorkflowDefinition] = {}
        self._instances: Dict[str, WorkflowInstance] = {}
        self._templates: Dict[str, WorkflowTemplate] = {}
        self._running_tasks: Dict[str, asyncio.Task] = {}
        
        # Add event handler for persistence
        self._executor.add_event_handler(self._handle_workflow_event)
        
    async def start(self) -> None:
        """Start the workflow coordinator."""
        # Initialize Redis connection if persistence is enabled
        if self.enable_persistence and self.redis_url:
            try:
                self._redis = redis.from_url(self.redis_url)
                await self._redis.ping()
                await self._load_state_from_redis()
                logger.info("Connected to Redis for workflow state persistence")
            except Exception as e:
                logger.warning(f"Redis connection failed, continuing without persistence: {e}")
                self._redis = None
                
        # Load workflow templates
        if self.workflow_templates_path:
            await self._load_templates()
            
        logger.info("Workflow coordinator started")
        
    async def stop(self) -> None:
        """Stop the workflow coordinator."""
        # Cancel all running tasks
        for task in self._running_tasks.values():
            if not task.done():
                task.cancel()
                
        # Wait for tasks to complete
        if self._running_tasks:
            await asyncio.gather(
                *self._running_tasks.values(),
                return_exceptions=True
            )
            
        # Close Redis connection
        if self._redis:
            await self._redis.close()
            
        logger.info("Workflow coordinator stopped")
        
    async def create_workflow(
        self,
        definition: Union[WorkflowDefinition, Dict[str, Any], str]
    ) -> WorkflowDefinition:
        """Create a new workflow definition.
        
        Args:
            definition: WorkflowDefinition object, dict, or YAML/JSON string
            
        Returns:
            Created workflow definition
        """
        # Parse definition if needed
        if isinstance(definition, str):
            # Try to parse as YAML first, then JSON
            try:
                data = yaml.safe_load(definition)
            except yaml.YAMLError:
                data = json.loads(definition)
            definition = WorkflowDefinition(**data)
        elif isinstance(definition, dict):
            definition = WorkflowDefinition(**definition)
            
        # Store workflow
        self._workflows[definition.id] = definition
        
        # Persist to Redis
        await self._persist_workflow(definition)
        
        logger.info(f"Created workflow: {definition.name} (ID: {definition.id})")
        return definition
        
    async def create_workflow_from_template(
        self,
        template_name: str,
        context: Optional[Dict[str, Any]] = None
    ) -> WorkflowInstance:
        """Create and start a workflow from a template.
        
        Args:
            template_name: Name of the workflow template
            context: Initial context values
            
        Returns:
            Running workflow instance
        """
        template = self._templates.get(template_name)
        if not template:
            raise ValueError(f"Template '{template_name}' not found")
            
        # Validate required context keys
        if template.required_context_keys:
            missing_keys = set(template.required_context_keys) - set(context or {})
            if missing_keys:
                raise ValueError(f"Missing required context keys: {missing_keys}")
                
        # Merge contexts
        full_context = template.default_context.copy()
        if context:
            full_context.update(context)
            
        # Create workflow instance
        instance = await self.start_workflow(
            template.workflow_definition.id,
            context=full_context
        )
        
        return instance
        
    async def start_workflow(
        self,
        workflow_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> WorkflowInstance:
        """Start a workflow execution.
        
        Args:
            workflow_id: ID of the workflow to execute
            context: Initial context values
            
        Returns:
            Running workflow instance
        """
        # Get workflow definition
        definition = self._workflows.get(workflow_id)
        if not definition:
            raise ValueError(f"Workflow '{workflow_id}' not found")
            
        # Create instance
        instance = WorkflowInstance(
            workflow_id=workflow_id,
            workflow_name=definition.name,
            workflow_version=definition.version,
            context=context or {}
        )
        
        # Store instance
        self._instances[instance.id] = instance
        
        # Start execution
        task = asyncio.create_task(
            self._executor.execute_workflow(definition, instance, context)
        )
        self._running_tasks[instance.id] = task
        
        # Persist initial state
        await self._persist_instance(instance)
        
        logger.info(f"Started workflow instance: {instance.id}")
        return instance
        
    async def get_workflow_status(self, instance_id: str) -> Optional[WorkflowInstance]:
        """Get the status of a workflow instance.
        
        Args:
            instance_id: Workflow instance ID
            
        Returns:
            Workflow instance or None if not found
        """
        return self._instances.get(instance_id)
        
    async def list_workflows(
        self,
        status: Optional[WorkflowStatus] = None,
        limit: int = 100
    ) -> List[WorkflowInstance]:
        """List workflow instances.
        
        Args:
            status: Filter by status
            limit: Maximum number to return
            
        Returns:
            List of workflow instances
        """
        instances = list(self._instances.values())
        
        # Filter by status if specified
        if status:
            instances = [i for i in instances if i.status == status]
            
        # Sort by creation time (newest first)
        instances.sort(key=lambda i: i.created_at, reverse=True)
        
        return instances[:limit]
        
    async def cancel_workflow(self, instance_id: str) -> bool:
        """Cancel a running workflow.
        
        Args:
            instance_id: Workflow instance ID
            
        Returns:
            True if cancelled, False if not found
        """
        instance = self._instances.get(instance_id)
        if not instance:
            return False
            
        task = self._running_tasks.get(instance_id)
        if task and not task.done():
            task.cancel()
            instance.status = WorkflowStatus.CANCELLED
            await self._persist_instance(instance)
            return True
            
        return False
        
    async def resume_workflow(self, instance_id: str) -> WorkflowInstance:
        """Resume a failed or interrupted workflow.
        
        Args:
            instance_id: Workflow instance ID
            
        Returns:
            Resumed workflow instance
        """
        instance = self._instances.get(instance_id)
        if not instance:
            raise ValueError(f"Workflow instance '{instance_id}' not found")
            
        if instance.status not in [WorkflowStatus.FAILED, WorkflowStatus.CANCELLED]:
            raise ValueError(f"Cannot resume workflow in status: {instance.status}")
            
        # Get workflow definition
        definition = self._workflows.get(instance.workflow_id)
        if not definition:
            raise ValueError(f"Workflow definition not found for instance")
            
        # Reset failed steps to pending
        for step in definition.steps:
            if step.status in ["failed", "running"]:
                step.status = "pending"
                step.error = None
                
        # Resume execution
        task = asyncio.create_task(
            self._executor.execute_workflow(definition, instance)
        )
        self._running_tasks[instance.id] = task
        
        logger.info(f"Resumed workflow instance: {instance_id}")
        return instance
        
    async def _handle_workflow_event(self, event: WorkflowEvent) -> None:
        """Handle workflow events for persistence."""
        # Update instance in Redis after each event
        instance = self._instances.get(event.workflow_instance_id)
        if instance:
            await self._persist_instance(instance)
            
    async def _persist_workflow(self, workflow: WorkflowDefinition) -> None:
        """Persist workflow definition to Redis."""
        if not self._redis:
            return
            
        try:
            data = workflow.json()
            await self._redis.hset(
                "dean:workflows",
                workflow.id,
                data
            )
        except Exception as e:
            logger.error(f"Failed to persist workflow: {e}")
            
    async def _persist_instance(self, instance: WorkflowInstance) -> None:
        """Persist workflow instance to Redis."""
        if not self._redis:
            return
            
        try:
            data = json.dumps(instance.to_dict())
            await self._redis.hset(
                "dean:workflow_instances",
                instance.id,
                data
            )
            
            # Also store in status-specific sets for querying
            await self._redis.sadd(
                f"dean:workflow_instances:{instance.status.value}",
                instance.id
            )
        except Exception as e:
            logger.error(f"Failed to persist workflow instance: {e}")
            
    async def _load_state_from_redis(self) -> None:
        """Load workflow state from Redis on startup."""
        if not self._redis:
            return
            
        try:
            # Load workflow definitions
            workflows_data = await self._redis.hgetall("dean:workflows")
            for workflow_id, data in workflows_data.items():
                try:
                    workflow = WorkflowDefinition(**json.loads(data))
                    self._workflows[workflow_id.decode()] = workflow
                except Exception as e:
                    logger.error(f"Failed to load workflow {workflow_id}: {e}")
                    
            # Load workflow instances
            instances_data = await self._redis.hgetall("dean:workflow_instances")
            for instance_id, data in instances_data.items():
                try:
                    instance = WorkflowInstance.from_dict(json.loads(data))
                    self._instances[instance_id.decode()] = instance
                except Exception as e:
                    logger.error(f"Failed to load workflow instance {instance_id}: {e}")
                    
            logger.info(
                f"Loaded {len(self._workflows)} workflows and "
                f"{len(self._instances)} instances from Redis"
            )
            
        except Exception as e:
            logger.error(f"Failed to load state from Redis: {e}")
            
    async def _load_templates(self) -> None:
        """Load workflow templates from files."""
        template_path = Path(self.workflow_templates_path)
        if not template_path.exists():
            logger.warning(f"Template path does not exist: {template_path}")
            return
            
        for file_path in template_path.glob("*.yaml"):
            try:
                with open(file_path) as f:
                    data = yaml.safe_load(f)
                    
                # Convert to workflow definition
                workflow_def = WorkflowDefinition(**data.get("workflow", {}))
                
                # Create template
                template = WorkflowTemplate(
                    name=data.get("name", file_path.stem),
                    description=data.get("description"),
                    category=data.get("category", "general"),
                    workflow_definition=workflow_def,
                    default_context=data.get("default_context", {}),
                    required_context_keys=data.get("required_context_keys", []),
                    tags=data.get("tags", {})
                )
                
                self._templates[template.name] = template
                self._workflows[workflow_def.id] = workflow_def
                
                logger.info(f"Loaded workflow template: {template.name}")
                
            except Exception as e:
                logger.error(f"Failed to load template {file_path}: {e}")
                
    def get_workflow_metrics(self) -> Dict[str, Any]:
        """Get workflow coordinator metrics."""
        status_counts = {}
        for instance in self._instances.values():
            status_counts[instance.status.value] = \
                status_counts.get(instance.status.value, 0) + 1
                
        return {
            "total_workflows": len(self._workflows),
            "total_instances": len(self._instances),
            "running_instances": len(self._running_tasks),
            "status_breakdown": status_counts,
            "templates_loaded": len(self._templates)
        }


# Utility functions for creating common workflow patterns

def create_evolution_trial_workflow() -> WorkflowDefinition:
    """Create a standard evolution trial workflow."""
    return WorkflowDefinition(
        name="Evolution Trial",
        description="Standard DEAN agent evolution trial workflow",
        steps=[
            WorkflowStep(
                id="validate_budget",
                name="Validate Token Budget",
                type=StepType.SERVICE_CALL,
                service_call=ServiceCallConfig(
                    service_name="IndexAgent",
                    endpoint="/api/v1/token/validate",
                    method="POST",
                    body={"budget": "{{token_budget}}"}
                ),
                retry_policy=RetryPolicy(max_attempts=2)
            ),
            WorkflowStep(
                id="create_population",
                name="Create Agent Population",
                type=StepType.SERVICE_CALL,
                depends_on=["validate_budget"],
                service_call=ServiceCallConfig(
                    service_name="IndexAgent",
                    endpoint="/api/v1/agents/population/initialize",
                    method="POST",
                    body={
                        "size": "{{population_size}}",
                        "diversity_threshold": "{{diversity_threshold}}"
                    }
                ),
                on_failure="cleanup_population"
            ),
            WorkflowStep(
                id="start_evolution",
                name="Start Evolution Process",
                type=StepType.SERVICE_CALL,
                depends_on=["create_population"],
                service_call=ServiceCallConfig(
                    service_name="EvolutionAPI",
                    endpoint="/api/v1/evolution/start",
                    method="POST",
                    body={
                        "population_ids": "{{step_create_population_result.agent_ids}}",
                        "generations": "{{generations}}",
                        "token_budget": "{{token_budget}}"
                    }
                ),
                timeout_seconds=600.0
            ),
            WorkflowStep(
                id="trigger_airflow",
                name="Trigger Airflow DAG",
                type=StepType.SERVICE_CALL,
                depends_on=["start_evolution"],
                service_call=ServiceCallConfig(
                    service_name="Airflow",
                    endpoint="/api/v1/dags/agent_evolution_trial/dagRuns",
                    method="POST",
                    body={
                        "conf": {
                            "trial_id": "{{workflow_instance_id}}",
                            "evolution_job_id": "{{step_start_evolution_result.job_id}}"
                        }
                    }
                )
            ),
            WorkflowStep(
                id="monitor_progress",
                name="Monitor Evolution Progress",
                type=StepType.WAIT,
                depends_on=["trigger_airflow"],
                wait_seconds=30.0
            ),
            WorkflowStep(
                id="collect_patterns",
                name="Collect Discovered Patterns",
                type=StepType.SERVICE_CALL,
                depends_on=["monitor_progress"],
                service_call=ServiceCallConfig(
                    service_name="IndexAgent",
                    endpoint="/api/v1/patterns/discovered",
                    method="GET",
                    params={"since": "{{step_start_evolution_result.started_at}}"}
                )
            ),
            WorkflowStep(
                id="update_allocations",
                name="Update Token Allocations",
                type=StepType.SERVICE_CALL,
                depends_on=["collect_patterns"],
                service_call=ServiceCallConfig(
                    service_name="IndexAgent",
                    endpoint="/api/v1/token/allocations/update",
                    method="POST",
                    body={"patterns": "{{step_collect_patterns_result}}"}
                )
            ),
            # Compensation steps
            WorkflowStep(
                id="cleanup_population",
                name="Cleanup Failed Population",
                type=StepType.SERVICE_CALL,
                service_call=ServiceCallConfig(
                    service_name="IndexAgent",
                    endpoint="/api/v1/agents/population/cleanup",
                    method="DELETE",
                    body={"population_id": "{{step_create_population_result.population_id}}"}
                ),
                skip_on_failure=True
            )
        ]
    )