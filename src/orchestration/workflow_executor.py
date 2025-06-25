"""Workflow execution engine for DEAN orchestration system.

This module implements the core execution logic for workflows, including
step execution, retry handling, and rollback capabilities.
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Any, Callable, Set
from datetime import datetime, timedelta
import logging
from jsonpath_ng import parse
import httpx

from .workflow_models import (
    WorkflowDefinition, WorkflowInstance, WorkflowStep, WorkflowStatus,
    StepStatus, StepType, RetryPolicy, ServiceCallConfig, WorkflowEvent
)
from .service_registry import ServiceRegistry, CircuitBreakerError, ServiceNotFoundError

logger = logging.getLogger(__name__)


class WorkflowExecutor:
    """Executes workflow instances with proper error handling and rollback."""
    
    def __init__(
        self,
        service_registry: ServiceRegistry,
        max_concurrent_steps: int = 10,
        default_timeout: float = 300.0
    ):
        """Initialize workflow executor.
        
        Args:
            service_registry: ServiceRegistry for service discovery
            max_concurrent_steps: Maximum parallel step execution
            default_timeout: Default step timeout in seconds
        """
        self.service_registry = service_registry
        self.max_concurrent_steps = max_concurrent_steps
        self.default_timeout = default_timeout
        self._running_steps: Dict[str, asyncio.Task] = {}
        self._step_semaphore = asyncio.Semaphore(max_concurrent_steps)
        self._event_handlers: List[Callable[[WorkflowEvent], None]] = []
        
    def add_event_handler(self, handler: Callable[[WorkflowEvent], None]) -> None:
        """Add an event handler for workflow events."""
        self._event_handlers.append(handler)
        
    async def _emit_event(
        self,
        instance: WorkflowInstance,
        event_type: str,
        step_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Emit a workflow event."""
        event = WorkflowEvent(
            workflow_instance_id=instance.id,
            step_id=step_id,
            event_type=event_type,
            details=details
        )
        
        for handler in self._event_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"Error in event handler: {e}")
                
    async def execute_workflow(
        self,
        definition: WorkflowDefinition,
        instance: WorkflowInstance,
        context: Optional[Dict[str, Any]] = None
    ) -> WorkflowInstance:
        """Execute a workflow instance.
        
        Args:
            definition: Workflow definition
            instance: Workflow instance to execute
            context: Initial context values
            
        Returns:
            Updated workflow instance
        """
        # Initialize context
        if context:
            instance.context.update(context)
            
        # Update instance state
        instance.status = WorkflowStatus.RUNNING
        instance.started_at = datetime.utcnow()
        
        await self._emit_event(instance, "workflow_started")
        
        try:
            # Execute workflow
            await self._execute_steps(definition, instance)
            
            # Check final status
            if definition.is_complete():
                instance.status = WorkflowStatus.COMPLETED
                await self._emit_event(instance, "workflow_completed")
            elif definition.has_failed():
                instance.status = WorkflowStatus.FAILED
                await self._emit_event(instance, "workflow_failed")
                
                # Trigger rollback if needed
                if any(step.on_failure for step in definition.steps):
                    await self._rollback_workflow(definition, instance)
            
        except asyncio.CancelledError:
            instance.status = WorkflowStatus.CANCELLED
            await self._emit_event(instance, "workflow_cancelled")
            raise
            
        except Exception as e:
            logger.error(f"Workflow execution error: {e}")
            instance.status = WorkflowStatus.FAILED
            instance.error = str(e)
            await self._emit_event(instance, "workflow_error", details={"error": str(e)})
            
        finally:
            instance.completed_at = datetime.utcnow()
            
            # Cancel any remaining tasks
            for task in self._running_steps.values():
                if not task.done():
                    task.cancel()
                    
        return instance
        
    async def _execute_steps(
        self,
        definition: WorkflowDefinition,
        instance: WorkflowInstance
    ) -> None:
        """Execute workflow steps respecting dependencies."""
        completed_steps: Set[str] = set()
        
        while not definition.is_complete() and not definition.has_failed():
            # Get ready steps
            ready_steps = definition.get_ready_steps()
            
            if not ready_steps and not self._running_steps:
                # No steps ready and nothing running - deadlock
                raise RuntimeError("Workflow deadlock detected - no steps can proceed")
                
            # Execute ready steps
            tasks = []
            for step in ready_steps:
                if step.id not in self._running_steps:
                    task = asyncio.create_task(
                        self._execute_step(step, instance)
                    )
                    self._running_steps[step.id] = task
                    tasks.append(task)
                    
            # Wait for at least one step to complete
            if tasks:
                done, pending = await asyncio.wait(
                    tasks,
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                # Update running steps
                for task in done:
                    step_id = None
                    for sid, t in self._running_steps.items():
                        if t == task:
                            step_id = sid
                            break
                    if step_id:
                        del self._running_steps[step_id]
                        completed_steps.add(step_id)
                        
            await asyncio.sleep(0.1)  # Brief pause to prevent busy loop
            
    async def _execute_step(
        self,
        step: WorkflowStep,
        instance: WorkflowInstance
    ) -> None:
        """Execute a single workflow step."""
        async with self._step_semaphore:
            step.status = StepStatus.RUNNING
            step.start_time = datetime.utcnow()
            instance.current_steps.append(step.id)
            
            await self._emit_event(
                instance,
                "step_started",
                step_id=step.id,
                details={"step_name": step.name, "step_type": step.type}
            )
            
            try:
                # Execute based on step type
                if step.type == StepType.SERVICE_CALL:
                    result = await self._execute_service_call(step, instance)
                elif step.type == StepType.PARALLEL:
                    result = await self._execute_parallel(step, instance)
                elif step.type == StepType.CONDITIONAL:
                    result = await self._execute_conditional(step, instance)
                elif step.type == StepType.WAIT:
                    result = await self._execute_wait(step)
                elif step.type == StepType.TRANSFORM:
                    result = await self._execute_transform(step, instance)
                else:
                    raise ValueError(f"Unknown step type: {step.type}")
                    
                # Update step state
                step.status = StepStatus.SUCCESS
                step.result = result
                
                # Store result in context
                instance.context[f"step_{step.id}_result"] = result
                
                await self._emit_event(
                    instance,
                    "step_completed",
                    step_id=step.id,
                    details={"result_size": len(str(result)) if result else 0}
                )
                
            except Exception as e:
                await self._handle_step_failure(step, instance, e)
                
            finally:
                step.end_time = datetime.utcnow()
                if step.id in instance.current_steps:
                    instance.current_steps.remove(step.id)
                    
    async def _handle_step_failure(
        self,
        step: WorkflowStep,
        instance: WorkflowInstance,
        error: Exception
    ) -> None:
        """Handle step execution failure."""
        step.error = str(error)
        step.attempts += 1
        
        # Check if we should retry
        if step.retry_policy and step.attempts < step.retry_policy.max_attempts:
            # Calculate retry delay with exponential backoff
            delay = min(
                step.retry_policy.initial_delay_seconds * 
                (step.retry_policy.backoff_multiplier ** (step.attempts - 1)),
                step.retry_policy.max_delay_seconds
            )
            
            logger.info(f"Retrying step {step.id} after {delay}s (attempt {step.attempts})")
            await asyncio.sleep(delay)
            
            # Reset status and retry
            step.status = StepStatus.PENDING
            step.error = None
            
        else:
            # Mark as failed
            step.status = StepStatus.FAILED
            instance.failed_step_id = step.id
            
            if not step.skip_on_failure:
                instance.error = f"Step {step.id} failed: {error}"
                
            await self._emit_event(
                instance,
                "step_failed",
                step_id=step.id,
                details={"error": str(error), "attempts": step.attempts}
            )
            
    async def _execute_service_call(
        self,
        step: WorkflowStep,
        instance: WorkflowInstance
    ) -> Any:
        """Execute a service call step."""
        config = step.service_call
        
        # Substitute context variables in configuration
        endpoint = self._substitute_variables(config.endpoint, instance.context)
        params = self._substitute_dict(config.params, instance.context) if config.params else None
        body = self._substitute_dict(config.body, instance.context) if config.body else None
        headers = self._substitute_dict(config.headers, instance.context) if config.headers else {}
        
        # Add authentication token from context if available
        auth_token = instance.context.get("auth_token")
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"
            
        # Add DEAN service token for service-to-service auth
        service_token = instance.context.get("service_token")
        if service_token:
            headers["X-DEAN-Service-Token"] = service_token
            
        # Add request correlation ID
        if "X-Request-ID" not in headers:
            headers["X-Request-ID"] = instance.id
        
        # Use service registry to make the call
        try:
            response = await self.service_registry.call_service(
                config.service_name,
                endpoint,
                method=config.method,
                params=params,
                json=body,
                headers=headers,
                timeout=config.timeout_seconds
            )
            
            # Return response data
            if response.headers.get("content-type", "").startswith("application/json"):
                return response.json()
            else:
                return response.text
                
        except (ServiceNotFoundError, CircuitBreakerError) as e:
            # Service-specific errors
            logger.error(f"Service call failed for {config.service_name}: {e}")
            raise
            
    async def _execute_parallel(
        self,
        step: WorkflowStep,
        instance: WorkflowInstance
    ) -> Dict[str, Any]:
        """Execute parallel steps."""
        # This is a placeholder - in a full implementation,
        # this would coordinate execution of multiple steps in parallel
        results = {}
        
        # Execute all parallel steps concurrently
        tasks = {}
        for step_id in step.parallel_steps:
            # Find the step definition
            parallel_step = next(
                (s for s in instance.workflow.steps if s.id == step_id),
                None
            )
            if parallel_step:
                task = asyncio.create_task(
                    self._execute_step(parallel_step, instance)
                )
                tasks[step_id] = task
                
        # Wait for all to complete
        if tasks:
            await asyncio.gather(*tasks.values(), return_exceptions=True)
            
            # Collect results
            for step_id, task in tasks.items():
                try:
                    results[step_id] = task.result()
                except Exception as e:
                    results[step_id] = {"error": str(e)}
                    
        return results
        
    async def _execute_conditional(
        self,
        step: WorkflowStep,
        instance: WorkflowInstance
    ) -> Any:
        """Execute conditional logic."""
        config = step.conditional
        
        # Evaluate condition (simple implementation - could be enhanced)
        condition_result = self._evaluate_condition(
            config.condition,
            instance.context
        )
        
        # Return which branch was taken
        if condition_result and config.if_true:
            return {"branch": "true", "next_step": config.if_true}
        elif not condition_result and config.if_false:
            return {"branch": "false", "next_step": config.if_false}
        else:
            return {"branch": "true" if condition_result else "false", "next_step": None}
            
    async def _execute_wait(self, step: WorkflowStep) -> None:
        """Execute wait step."""
        await asyncio.sleep(step.wait_seconds)
        return {"waited_seconds": step.wait_seconds}
        
    async def _execute_transform(
        self,
        step: WorkflowStep,
        instance: WorkflowInstance
    ) -> Any:
        """Execute data transformation."""
        config = step.transform
        
        # Get input data using JSONPath
        jsonpath_expr = parse(config.input_path)
        matches = jsonpath_expr.find(instance.context)
        
        if not matches:
            raise ValueError(f"No data found at path: {config.input_path}")
            
        input_data = matches[0].value
        
        # Simple transformation (could be enhanced with more expressions)
        # For now, just return the extracted data
        result = input_data
        
        # Store in context
        instance.context[config.output_key] = result
        
        return result
        
    async def _rollback_workflow(
        self,
        definition: WorkflowDefinition,
        instance: WorkflowInstance
    ) -> None:
        """Execute rollback for failed workflow."""
        instance.status = WorkflowStatus.ROLLING_BACK
        await self._emit_event(instance, "rollback_started")
        
        # Find steps that need rollback (in reverse order)
        completed_steps = [
            step for step in definition.steps
            if step.status == StepStatus.SUCCESS and step.on_failure
        ]
        completed_steps.reverse()
        
        for step in completed_steps:
            try:
                # Find compensation step
                compensation_step = definition.get_step(step.on_failure)
                if compensation_step:
                    await self._execute_step(compensation_step, instance)
                    instance.rollback_completed.append(step.id)
                    
            except Exception as e:
                logger.error(f"Rollback failed for step {step.id}: {e}")
                instance.rollback_failed.append(step.id)
                
        instance.status = WorkflowStatus.ROLLED_BACK
        await self._emit_event(instance, "rollback_completed")
        
    def _substitute_variables(self, template: str, context: Dict[str, Any]) -> str:
        """Substitute context variables in a string template."""
        # Simple variable substitution - replace {{key}} with context[key]
        import re
        
        def replace_var(match):
            key = match.group(1).strip()
            # Support nested access like {{step_1_result.data}}
            value = context
            for part in key.split('.'):
                if isinstance(value, dict):
                    value = value.get(part, '')
                else:
                    value = ''
                    break
            return str(value)
            
        return re.sub(r'\{\{(.+?)\}\}', replace_var, template)
        
    def _substitute_dict(
        self,
        data: Optional[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Recursively substitute variables in a dictionary."""
        if not data:
            return data
            
        result = {}
        for key, value in data.items():
            if isinstance(value, str):
                result[key] = self._substitute_variables(value, context)
            elif isinstance(value, dict):
                result[key] = self._substitute_dict(value, context)
            elif isinstance(value, list):
                result[key] = [
                    self._substitute_variables(v, context) if isinstance(v, str) else v
                    for v in value
                ]
            else:
                result[key] = value
                
        return result
        
    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """Evaluate a simple condition expression."""
        # Very basic implementation - just check if a context key exists
        # In production, this would use a proper expression evaluator
        if condition.startswith("exists:"):
            key = condition[7:].strip()
            return key in context and context[key] is not None
        elif "==" in condition:
            # Simple equality check
            left, right = condition.split("==", 1)
            left_val = context.get(left.strip(), None)
            right_val = right.strip().strip('"').strip("'")
            return str(left_val) == right_val
        else:
            # Default to checking truthiness of a context value
            return bool(context.get(condition, False))