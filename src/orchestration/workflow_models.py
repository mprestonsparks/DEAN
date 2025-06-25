"""Workflow definition models for DEAN orchestration system.

This module defines the data models and schemas for workflow definitions,
supporting complex multi-service orchestration with conditional logic.
"""

from typing import Dict, List, Optional, Any, Union, Set
from enum import Enum
from pydantic import BaseModel, Field, validator
from datetime import datetime
import uuid


class StepType(str, Enum):
    """Types of workflow steps."""
    SERVICE_CALL = "service_call"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"
    WAIT = "wait"
    TRANSFORM = "transform"


class StepStatus(str, Enum):
    """Status of a workflow step."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    ROLLED_BACK = "rolled_back"


class WorkflowStatus(str, Enum):
    """Overall workflow execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ROLLING_BACK = "rolling_back"
    ROLLED_BACK = "rolled_back"


class RetryPolicy(BaseModel):
    """Retry configuration for steps."""
    max_attempts: int = 3
    backoff_multiplier: float = 2.0
    initial_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0
    retryable_status_codes: List[int] = Field(default_factory=lambda: [500, 502, 503, 504])


class ServiceCallConfig(BaseModel):
    """Configuration for service call steps."""
    service_name: str
    endpoint: str
    method: str = "GET"
    headers: Optional[Dict[str, str]] = None
    params: Optional[Dict[str, Any]] = None
    body: Optional[Dict[str, Any]] = None
    timeout_seconds: float = 30.0
    
    @validator('method')
    def validate_method(cls, v):
        allowed_methods = ["GET", "POST", "PUT", "PATCH", "DELETE"]
        if v.upper() not in allowed_methods:
            raise ValueError(f"Method must be one of {allowed_methods}")
        return v.upper()


class ConditionalConfig(BaseModel):
    """Configuration for conditional execution."""
    condition: str  # Expression to evaluate
    if_true: Optional[str] = None  # Step ID to execute if true
    if_false: Optional[str] = None  # Step ID to execute if false


class TransformConfig(BaseModel):
    """Configuration for data transformation steps."""
    input_path: str  # JSONPath to input data
    output_key: str  # Key to store result in context
    expression: str  # Transformation expression


class WorkflowStep(BaseModel):
    """Individual workflow step definition."""
    id: str
    name: str
    type: StepType
    depends_on: List[str] = Field(default_factory=list)
    
    # Step-specific configurations
    service_call: Optional[ServiceCallConfig] = None
    parallel_steps: Optional[List[str]] = None
    conditional: Optional[ConditionalConfig] = None
    wait_seconds: Optional[float] = None
    transform: Optional[TransformConfig] = None
    
    # Common configurations
    retry_policy: Optional[RetryPolicy] = None
    timeout_seconds: float = 300.0
    on_failure: Optional[str] = None  # Step ID for compensation
    skip_on_failure: bool = False
    
    # Runtime fields
    status: StepStatus = StepStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    attempts: int = 0
    
    @validator('type', always=True)
    def validate_config(cls, v, values):
        """Ensure appropriate config is provided for step type."""
        if v == StepType.SERVICE_CALL and not values.get('service_call'):
            raise ValueError("service_call config required for SERVICE_CALL steps")
        elif v == StepType.PARALLEL and not values.get('parallel_steps'):
            raise ValueError("parallel_steps required for PARALLEL steps")
        elif v == StepType.CONDITIONAL and not values.get('conditional'):
            raise ValueError("conditional config required for CONDITIONAL steps")
        elif v == StepType.WAIT and values.get('wait_seconds') is None:
            raise ValueError("wait_seconds required for WAIT steps")
        elif v == StepType.TRANSFORM and not values.get('transform'):
            raise ValueError("transform config required for TRANSFORM steps")
        return v


class WorkflowDefinition(BaseModel):
    """Complete workflow definition."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    version: str = "1.0.0"
    description: Optional[str] = None
    
    # Workflow configuration
    steps: List[WorkflowStep]
    timeout_seconds: float = 3600.0
    max_parallel_steps: int = 10
    
    # Metadata
    tags: Dict[str, str] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('steps')
    def validate_dag(cls, steps):
        """Validate that steps form a valid DAG (no circular dependencies)."""
        step_ids = {step.id for step in steps}
        
        # Check all step IDs are unique
        if len(step_ids) != len(steps):
            raise ValueError("Duplicate step IDs found")
        
        # Build dependency graph
        graph = {step.id: set(step.depends_on) for step in steps}
        
        # Check all dependencies exist
        for step_id, deps in graph.items():
            for dep in deps:
                if dep not in step_ids:
                    raise ValueError(f"Step {step_id} depends on non-existent step {dep}")
        
        # Check for circular dependencies using DFS
        visited = set()
        rec_stack = set()
        
        def has_cycle(node):
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(node)
            return False
        
        for node in graph:
            if node not in visited:
                if has_cycle(node):
                    raise ValueError("Circular dependency detected in workflow")
        
        return steps
    
    def get_step(self, step_id: str) -> Optional[WorkflowStep]:
        """Get a step by ID."""
        for step in self.steps:
            if step.id == step_id:
                return step
        return None
    
    def get_ready_steps(self) -> List[WorkflowStep]:
        """Get steps that are ready to execute."""
        ready = []
        for step in self.steps:
            if step.status != StepStatus.PENDING:
                continue
                
            # Check if all dependencies are satisfied
            deps_satisfied = all(
                self.get_step(dep_id) and 
                self.get_step(dep_id).status == StepStatus.SUCCESS
                for dep_id in step.depends_on
            )
            
            if deps_satisfied:
                ready.append(step)
                
        return ready
    
    def is_complete(self) -> bool:
        """Check if workflow execution is complete."""
        return all(
            step.status in [StepStatus.SUCCESS, StepStatus.SKIPPED]
            for step in self.steps
        )
    
    def has_failed(self) -> bool:
        """Check if workflow has any failed steps."""
        return any(
            step.status == StepStatus.FAILED and not step.skip_on_failure
            for step in self.steps
        )


class WorkflowInstance(BaseModel):
    """Runtime instance of a workflow execution."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    workflow_id: str
    workflow_name: str
    workflow_version: str
    
    # Execution state
    status: WorkflowStatus = WorkflowStatus.PENDING
    context: Dict[str, Any] = Field(default_factory=dict)
    current_steps: List[str] = Field(default_factory=list)
    
    # Timing
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Error tracking
    error: Optional[str] = None
    failed_step_id: Optional[str] = None
    
    # Rollback tracking
    rollback_completed: List[str] = Field(default_factory=list)
    rollback_failed: List[str] = Field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = self.dict()
        # Convert datetime objects to ISO format
        for key in ['created_at', 'started_at', 'completed_at']:
            if data.get(key):
                data[key] = data[key].isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowInstance':
        """Create from dictionary."""
        # Convert ISO strings back to datetime
        for key in ['created_at', 'started_at', 'completed_at']:
            if data.get(key) and isinstance(data[key], str):
                data[key] = datetime.fromisoformat(data[key])
        return cls(**data)


class WorkflowEvent(BaseModel):
    """Event emitted during workflow execution."""
    workflow_instance_id: str
    step_id: Optional[str] = None
    event_type: str  # started, completed, failed, etc.
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    details: Optional[Dict[str, Any]] = None
    
    
class CompensationAction(BaseModel):
    """Compensation action for rollback scenarios."""
    step_id: str
    action_type: str  # service_call, custom_logic
    service_call: Optional[ServiceCallConfig] = None
    custom_handler: Optional[str] = None  # Function name to call
    
    
class WorkflowTemplate(BaseModel):
    """Reusable workflow template."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    category: str  # evolution, pattern, maintenance, etc.
    
    # Template definition
    workflow_definition: WorkflowDefinition
    default_context: Dict[str, Any] = Field(default_factory=dict)
    required_context_keys: List[str] = Field(default_factory=list)
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    tags: Dict[str, str] = Field(default_factory=dict)