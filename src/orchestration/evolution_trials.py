"""Evolution Trial Management for DEAN.

This module provides specialized management for DEAN evolution trials,
building on top of the WorkflowCoordinator to handle trial-specific logic.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field
import uuid

from .workflow_coordinator import WorkflowCoordinator
from .workflow_models import WorkflowStatus


class TrialStatus(str, Enum):
    """Evolution trial status."""
    PENDING = "pending"
    INITIALIZING = "initializing"
    RUNNING = "running"
    MONITORING = "monitoring"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentMetrics(BaseModel):
    """Metrics for an individual agent."""
    agent_id: str
    fitness_score: float = 0.0
    token_usage: int = 0
    patterns_discovered: int = 0
    efficiency_score: float = 0.0
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class GenerationMetrics(BaseModel):
    """Metrics for a single generation."""
    generation: int
    avg_fitness: float = 0.0
    max_fitness: float = 0.0
    min_fitness: float = 0.0
    diversity_index: float = 0.0
    total_tokens_used: int = 0
    patterns_discovered: int = 0
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class EvolutionTrial(BaseModel):
    """Evolution trial model with metadata and metrics."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    status: TrialStatus = TrialStatus.PENDING
    workflow_instance_id: Optional[str] = None
    
    # Trial parameters
    population_size: int = 10
    generations: int = 50
    mutation_rate: float = 0.1
    crossover_rate: float = 0.7
    token_budget: int = 100000
    diversity_threshold: float = 0.3
    
    # Tracking
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Metrics
    current_generation: int = 0
    total_tokens_used: int = 0
    agent_metrics: Dict[str, AgentMetrics] = {}
    generation_metrics: List[GenerationMetrics] = []
    discovered_patterns: List[Dict[str, Any]] = []
    
    # Results
    best_agent_id: Optional[str] = None
    best_fitness_score: float = 0.0
    final_diversity_index: float = 0.0
    success_rate: float = 0.0
    error_message: Optional[str] = None


class EvolutionTrialManager:
    """Manages DEAN evolution trials."""
    
    def __init__(self, workflow_coordinator: WorkflowCoordinator):
        """Initialize the evolution trial manager.
        
        Args:
            workflow_coordinator: The workflow coordinator instance
        """
        self.workflow_coordinator = workflow_coordinator
        self.trials: Dict[str, EvolutionTrial] = {}
        self._update_tasks: Dict[str, asyncio.Task] = {}
        self._subscribers: Dict[str, List[asyncio.Queue]] = {}
        
    async def create_trial(
        self,
        name: str,
        population_size: int = 10,
        generations: int = 50,
        mutation_rate: float = 0.1,
        crossover_rate: float = 0.7,
        token_budget: int = 100000,
        diversity_threshold: float = 0.3,
        auth_token: Optional[str] = None
    ) -> EvolutionTrial:
        """Create a new evolution trial.
        
        Args:
            name: Trial name
            population_size: Number of agents
            generations: Number of evolution generations
            mutation_rate: Mutation rate (0-1)
            crossover_rate: Crossover rate (0-1)
            token_budget: Total token budget
            diversity_threshold: Minimum diversity threshold
            auth_token: JWT authentication token
            
        Returns:
            Created evolution trial
        """
        trial = EvolutionTrial(
            name=name,
            population_size=population_size,
            generations=generations,
            mutation_rate=mutation_rate,
            crossover_rate=crossover_rate,
            token_budget=token_budget,
            diversity_threshold=diversity_threshold
        )
        
        self.trials[trial.id] = trial
        return trial
        
    async def start_trial(self, trial_id: str, auth_token: Optional[str] = None) -> EvolutionTrial:
        """Start an evolution trial.
        
        Args:
            trial_id: Trial ID
            auth_token: JWT authentication token for service calls
            
        Returns:
            Updated trial
        """
        trial = self.trials.get(trial_id)
        if not trial:
            raise ValueError(f"Trial {trial_id} not found")
            
        if trial.status != TrialStatus.PENDING:
            raise ValueError(f"Trial {trial_id} is not in pending state")
            
        # Update status
        trial.status = TrialStatus.INITIALIZING
        trial.started_at = datetime.utcnow()
        
        # Create workflow context
        context = {
            "trial_id": trial.id,
            "population_size": trial.population_size,
            "generations": trial.generations,
            "mutation_rate": trial.mutation_rate,
            "crossover_rate": trial.crossover_rate,
            "token_budget": trial.token_budget,
            "diversity_threshold": trial.diversity_threshold,
            "auth_token": auth_token  # Pass auth token to workflow
        }
        
        # Start evolution workflow
        try:
            workflow_instance = await self.workflow_coordinator.create_workflow_from_template(
                "Evolution Trial",
                context=context
            )
            
            trial.workflow_instance_id = workflow_instance.id
            trial.status = TrialStatus.RUNNING
            
            # Start background update task
            self._update_tasks[trial.id] = asyncio.create_task(
                self._monitor_trial(trial.id)
            )
            
        except Exception as e:
            trial.status = TrialStatus.FAILED
            trial.error_message = str(e)
            raise
            
        return trial
        
    async def get_trial(self, trial_id: str) -> Optional[EvolutionTrial]:
        """Get trial by ID.
        
        Args:
            trial_id: Trial ID
            
        Returns:
            Trial if found
        """
        return self.trials.get(trial_id)
        
    async def list_trials(
        self,
        status: Optional[TrialStatus] = None,
        limit: int = 100
    ) -> List[EvolutionTrial]:
        """List trials with optional filtering.
        
        Args:
            status: Filter by status
            limit: Maximum number of trials
            
        Returns:
            List of trials
        """
        trials = list(self.trials.values())
        
        if status:
            trials = [t for t in trials if t.status == status]
            
        # Sort by created_at descending
        trials.sort(key=lambda t: t.created_at, reverse=True)
        
        return trials[:limit]
        
    async def cancel_trial(self, trial_id: str) -> bool:
        """Cancel a running trial.
        
        Args:
            trial_id: Trial ID
            
        Returns:
            True if cancelled successfully
        """
        trial = self.trials.get(trial_id)
        if not trial:
            return False
            
        if trial.status not in [TrialStatus.RUNNING, TrialStatus.MONITORING]:
            return False
            
        # Cancel workflow if running
        if trial.workflow_instance_id:
            cancelled = await self.workflow_coordinator.cancel_workflow(
                trial.workflow_instance_id
            )
            if not cancelled:
                return False
                
        # Update status
        trial.status = TrialStatus.CANCELLED
        trial.completed_at = datetime.utcnow()
        
        # Cancel update task
        if trial_id in self._update_tasks:
            self._update_tasks[trial_id].cancel()
            del self._update_tasks[trial_id]
            
        # Notify subscribers
        await self._broadcast_update(trial_id, {
            "type": "cancelled",
            "trial_id": trial_id,
            "message": "Trial cancelled by user"
        })
        
        return True
        
    async def subscribe_to_trial(self, trial_id: str) -> asyncio.Queue:
        """Subscribe to trial updates.
        
        Args:
            trial_id: Trial ID
            
        Returns:
            Queue for receiving updates
        """
        if trial_id not in self._subscribers:
            self._subscribers[trial_id] = []
            
        queue = asyncio.Queue(maxsize=100)
        self._subscribers[trial_id].append(queue)
        
        # Send initial status
        trial = self.trials.get(trial_id)
        if trial:
            await queue.put({
                "type": "status",
                "trial": trial.dict()
            })
            
        return queue
        
    async def unsubscribe_from_trial(self, trial_id: str, queue: asyncio.Queue):
        """Unsubscribe from trial updates.
        
        Args:
            trial_id: Trial ID
            queue: Subscription queue
        """
        if trial_id in self._subscribers:
            if queue in self._subscribers[trial_id]:
                self._subscribers[trial_id].remove(queue)
                
    async def _monitor_trial(self, trial_id: str):
        """Monitor trial progress and update metrics.
        
        Args:
            trial_id: Trial ID
        """
        trial = self.trials.get(trial_id)
        if not trial or not trial.workflow_instance_id:
            return
            
        try:
            while trial.status in [TrialStatus.RUNNING, TrialStatus.MONITORING]:
                # Get workflow status
                workflow_instance = await self.workflow_coordinator.get_workflow_status(
                    trial.workflow_instance_id
                )
                
                if workflow_instance:
                    # Update trial based on workflow status
                    await self._update_trial_from_workflow(trial, workflow_instance)
                    
                    # Check if workflow completed
                    if workflow_instance.status == WorkflowStatus.COMPLETED:
                        trial.status = TrialStatus.COMPLETED
                        trial.completed_at = datetime.utcnow()
                        break
                    elif workflow_instance.status == WorkflowStatus.FAILED:
                        trial.status = TrialStatus.FAILED
                        trial.error_message = workflow_instance.error
                        trial.completed_at = datetime.utcnow()
                        break
                    elif workflow_instance.status == WorkflowStatus.CANCELLED:
                        trial.status = TrialStatus.CANCELLED
                        trial.completed_at = datetime.utcnow()
                        break
                        
                # Broadcast update
                await self._broadcast_trial_update(trial)
                
                # Wait before next check
                await asyncio.sleep(2.0)
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            trial.status = TrialStatus.FAILED
            trial.error_message = f"Monitoring error: {str(e)}"
            
        finally:
            # Final update
            await self._broadcast_trial_update(trial)
            
            # Cleanup
            if trial_id in self._update_tasks:
                del self._update_tasks[trial_id]
                
    async def _update_trial_from_workflow(self, trial: EvolutionTrial, workflow_instance):
        """Update trial metrics from workflow instance.
        
        Args:
            trial: Evolution trial
            workflow_instance: Workflow instance
        """
        context = workflow_instance.context
        
        # Extract metrics from workflow context
        if "current_generation" in context:
            trial.current_generation = context["current_generation"]
            
        if "total_tokens_used" in context:
            trial.total_tokens_used = context["total_tokens_used"]
            
        if "agent_metrics" in context:
            # Update agent metrics
            for agent_id, metrics in context["agent_metrics"].items():
                trial.agent_metrics[agent_id] = AgentMetrics(
                    agent_id=agent_id,
                    **metrics
                )
                
        if "generation_metrics" in context:
            # Add new generation metrics
            gen_metrics = context["generation_metrics"]
            if isinstance(gen_metrics, dict):
                trial.generation_metrics.append(
                    GenerationMetrics(**gen_metrics)
                )
                
        if "discovered_patterns" in context:
            # Add new patterns
            patterns = context["discovered_patterns"]
            if isinstance(patterns, list):
                trial.discovered_patterns.extend(patterns)
                
        # Update best agent
        if trial.agent_metrics:
            best_agent = max(
                trial.agent_metrics.values(),
                key=lambda a: a.fitness_score
            )
            trial.best_agent_id = best_agent.agent_id
            trial.best_fitness_score = best_agent.fitness_score
            
        # Update diversity from latest generation
        if trial.generation_metrics:
            latest_gen = trial.generation_metrics[-1]
            trial.final_diversity_index = latest_gen.diversity_index
            
    async def _broadcast_trial_update(self, trial: EvolutionTrial):
        """Broadcast trial update to subscribers.
        
        Args:
            trial: Evolution trial
        """
        update = {
            "type": "update",
            "trial_id": trial.id,
            "status": trial.status,
            "current_generation": trial.current_generation,
            "total_tokens_used": trial.total_tokens_used,
            "best_fitness_score": trial.best_fitness_score,
            "agent_count": len(trial.agent_metrics),
            "patterns_discovered": len(trial.discovered_patterns),
            "generation_metrics": [m.dict() for m in trial.generation_metrics[-5:]]  # Last 5
        }
        
        await self._broadcast_update(trial.id, update)
        
    async def _broadcast_update(self, trial_id: str, update: Dict[str, Any]):
        """Broadcast update to all subscribers.
        
        Args:
            trial_id: Trial ID
            update: Update data
        """
        if trial_id not in self._subscribers:
            return
            
        # Send to all subscribers
        dead_queues = []
        for queue in self._subscribers[trial_id]:
            try:
                await queue.put(update)
            except asyncio.QueueFull:
                # Remove full queues
                dead_queues.append(queue)
                
        # Clean up dead queues
        for queue in dead_queues:
            self._subscribers[trial_id].remove(queue)
            
    def get_trial_metrics_summary(self, trial_id: str) -> Optional[Dict[str, Any]]:
        """Get trial metrics summary.
        
        Args:
            trial_id: Trial ID
            
        Returns:
            Metrics summary if trial exists
        """
        trial = self.trials.get(trial_id)
        if not trial:
            return None
            
        return {
            "trial_id": trial.id,
            "name": trial.name,
            "status": trial.status,
            "progress": {
                "current_generation": trial.current_generation,
                "total_generations": trial.generations,
                "percentage": (trial.current_generation / trial.generations * 100) if trial.generations > 0 else 0
            },
            "resource_usage": {
                "tokens_used": trial.total_tokens_used,
                "tokens_budget": trial.token_budget,
                "tokens_remaining": trial.token_budget - trial.total_tokens_used,
                "usage_percentage": (trial.total_tokens_used / trial.token_budget * 100) if trial.token_budget > 0 else 0
            },
            "performance": {
                "best_fitness": trial.best_fitness_score,
                "diversity_index": trial.final_diversity_index,
                "patterns_discovered": len(trial.discovered_patterns),
                "active_agents": len(trial.agent_metrics)
            },
            "timing": {
                "started_at": trial.started_at.isoformat() if trial.started_at else None,
                "duration_seconds": (datetime.utcnow() - trial.started_at).total_seconds() if trial.started_at else 0,
                "estimated_completion": self._estimate_completion(trial)
            }
        }
        
    def _estimate_completion(self, trial: EvolutionTrial) -> Optional[str]:
        """Estimate trial completion time.
        
        Args:
            trial: Evolution trial
            
        Returns:
            Estimated completion time ISO string
        """
        if not trial.started_at or trial.current_generation == 0:
            return None
            
        elapsed = (datetime.utcnow() - trial.started_at).total_seconds()
        rate = trial.current_generation / elapsed  # generations per second
        
        if rate > 0:
            remaining = trial.generations - trial.current_generation
            estimated_seconds = remaining / rate
            estimated_completion = datetime.utcnow() + timedelta(seconds=estimated_seconds)
            return estimated_completion.isoformat()
            
        return None