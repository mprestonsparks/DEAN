"""Evolution trial coordination for DEAN system.

Adapted from dean-agent-workspace/run_evolution_trial.py
Coordinates evolution trials across services without direct repository dependencies.
"""

import asyncio
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

import structlog
from pydantic import BaseModel, Field

from ...integration import ServicePool, ServiceError

# Configure structured logging
logger = structlog.get_logger(__name__)


class EvolutionConfig(BaseModel):
    """Configuration for evolution trials."""
    
    population_size: int = Field(10, description="Size of agent population")
    generations: int = Field(5, description="Number of generations to evolve")
    mutation_rate: float = Field(0.1, description="Mutation probability")
    crossover_rate: float = Field(0.7, description="Crossover probability")
    selection_pressure: float = Field(0.3, description="Selection pressure")
    diversity_threshold: float = Field(0.3, description="Minimum diversity threshold")
    token_budget: int = Field(5000, description="Token budget per agent")
    optimization_goals: List[str] = Field(
        default_factory=lambda: ["performance", "security", "maintainability"],
        description="Optimization objectives"
    )
    wait_for_completion: bool = Field(
        True,
        description="Wait for trial completion"
    )
    timeout: int = Field(3600, description="Maximum trial duration in seconds")


class EvolutionTrialResult(BaseModel):
    """Results from an evolution trial."""
    
    trial_id: str
    status: str
    start_time: datetime
    end_time: Optional[datetime] = None
    repository: Optional[str] = None
    population_id: Optional[str] = None
    dag_run_id: Optional[str] = None
    agents: List[Dict[str, Any]] = Field(default_factory=list)
    generations: List[Dict[str, Any]] = Field(default_factory=list)
    improvements: List[Dict[str, Any]] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    errors: List[str] = Field(default_factory=list)


class EvolutionTrialCoordinator:
    """Coordinates evolution trials across DEAN services.
    
    Manages:
    - System health validation
    - Repository registration
    - Agent population creation
    - Evolution monitoring
    - Result collection
    """
    
    def __init__(
        self,
        service_pool: Optional[ServicePool] = None,
        config: Optional[EvolutionConfig] = None
    ):
        """Initialize evolution trial coordinator.
        
        Args:
            service_pool: Service client pool
            config: Evolution configuration
        """
        self.pool = service_pool
        self.config = config or EvolutionConfig()
        self.logger = logger.bind(component="evolution_coordinator")
        self._owned_pool = False
    
    async def __aenter__(self):
        """Async context manager entry."""
        if self.pool is None:
            self.pool = ServicePool()
            self._owned_pool = True
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._owned_pool and self.pool:
            await self.pool.close()
    
    async def run_trial(
        self,
        repository_path: str,
        config_overrides: Optional[Dict[str, Any]] = None
    ) -> EvolutionTrialResult:
        """Execute a complete evolution trial.
        
        Args:
            repository_path: Path to target repository
            config_overrides: Configuration overrides
            
        Returns:
            Evolution trial results
        """
        # Generate trial ID
        trial_id = f"trial_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Initialize result
        result = EvolutionTrialResult(
            trial_id=trial_id,
            status="initializing",
            start_time=datetime.utcnow(),
            repository=repository_path
        )
        
        # Apply configuration overrides
        if config_overrides:
            config_dict = self.config.dict()
            config_dict.update(config_overrides)
            self.config = EvolutionConfig(**config_dict)
        
        self.logger.info(
            "Starting evolution trial",
            trial_id=trial_id,
            repository=repository_path,
            config=self.config.dict()
        )
        
        try:
            # Check system health
            if not await self._check_system_health():
                raise RuntimeError("System health check failed")
            
            result.status = "system_ready"
            
            # Register repository
            repo_id = await self._register_repository(repository_path)
            if not repo_id:
                raise RuntimeError("Failed to register repository")
            
            result.status = "repository_registered"
            
            # Execute evolution workflow
            workflow_result = await self.pool.workflow.execute_evolution_trial(
                population_size=self.config.population_size,
                generations=self.config.generations,
                agent_type="optimization",
                mutation_rate=self.config.mutation_rate,
                crossover_rate=self.config.crossover_rate,
                selection_method="tournament",
                dag_config={
                    "repository_id": repo_id,
                    "optimization_goals": self.config.optimization_goals,
                    "token_budget": self.config.token_budget,
                },
                wait_for_completion=self.config.wait_for_completion,
                timeout=self.config.timeout
            )
            
            result.population_id = workflow_result.get("population_id")
            result.dag_run_id = workflow_result.get("dag_run_id")
            result.status = workflow_result.get("status", "running")
            
            # Monitor evolution if waiting for completion
            if self.config.wait_for_completion:
                await self._monitor_evolution(result)
            
            # Collect results
            await self._collect_results(result)
            
            result.status = "completed"
            result.end_time = datetime.utcnow()
            
            self.logger.info(
                "Evolution trial completed",
                trial_id=trial_id,
                duration=(result.end_time - result.start_time).total_seconds(),
                improvements_count=len(result.improvements)
            )
            
        except Exception as e:
            self.logger.error(
                "Evolution trial failed",
                trial_id=trial_id,
                error=str(e)
            )
            result.status = "failed"
            result.errors.append(str(e))
            result.end_time = datetime.utcnow()
        
        return result
    
    async def _check_system_health(self) -> bool:
        """Check if all required services are healthy.
        
        Returns:
            True if all services are healthy
        """
        self.logger.info("Checking system health")
        
        health_status = await self.pool.health.check_all_services()
        
        if health_status['status'] != 'healthy':
            for service, status in health_status['services'].items():
                if status.get('status') != 'healthy':
                    self.logger.error(
                        "Service unhealthy",
                        service=service,
                        status=status
                    )
            return False
        
        self.logger.info("All services healthy")
        return True
    
    async def _register_repository(self, repo_path: str) -> Optional[str]:
        """Register repository with Evolution API.
        
        Args:
            repo_path: Repository path
            
        Returns:
            Repository ID if successful
        """
        self.logger.info("Registering repository", path=repo_path)
        
        try:
            # Import repository manager
            from ..repository_manager import RepositoryManager
            
            # Create repository manager instance
            repo_manager = RepositoryManager(
                base_path=os.getenv("REPO_BASE_PATH", "/repos"),
                db_pool=None,  # Would be passed from main app context
                redis_client=None  # Would be passed from main app context
            )
            
            # Register repository
            repo_id = await repo_manager.register_repository(
                repo_path=repo_path,
                metadata={
                    "trial_id": self.trial_id,
                    "registered_by": "evolution_trial",
                    "purpose": "agent_evolution"
                }
            )
            
            self.logger.info(f"Repository registered successfully: {repo_id}")
            return repo_id
            
        except Exception as e:
            self.logger.error("Repository registration failed", error=str(e))
            return None
    
    async def _monitor_evolution(self, result: EvolutionTrialResult):
        """Monitor evolution progress.
        
        Args:
            result: Trial result to update
        """
        self.logger.info("Monitoring evolution progress", trial_id=result.trial_id)
        
        start_time = datetime.utcnow()
        
        while (datetime.utcnow() - start_time).total_seconds() < self.config.timeout:
            try:
                # Get evolution status
                status = await self.pool.evolution.get_evolution_status(
                    result.trial_id
                )
                
                current_generation = status.get("current_generation", 0)
                total_generations = status.get("total_generations", self.config.generations)
                
                self.logger.info(
                    "Evolution progress",
                    generation=f"{current_generation}/{total_generations}",
                    best_fitness=status.get("best_fitness"),
                    population_diversity=status.get("diversity")
                )
                
                # Check if completed
                if status.get("status") in ["completed", "failed"]:
                    break
                
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                self.logger.error("Failed to get evolution status", error=str(e))
                await asyncio.sleep(10)
    
    async def _collect_results(self, result: EvolutionTrialResult):
        """Collect evolution results.
        
        Args:
            result: Trial result to populate
        """
        self.logger.info("Collecting evolution results", trial_id=result.trial_id)
        
        try:
            # Get final evolution metrics
            metrics = await self.pool.indexagent.get_evolution_metrics(
                population_id=result.population_id
            )
            result.metrics = metrics
            
            # Get discovered patterns
            patterns = await self.pool.evolution.get_patterns(
                trial_id=result.trial_id,
                min_effectiveness=0.5
            )
            
            # Get agent improvements
            if result.population_id:
                agents = await self.pool.indexagent.list_agents(
                    limit=self.config.population_size
                )
                result.agents = agents
                
                # Extract improvements
                for agent in agents:
                    if agent.get("performance_delta", 0) > 0:
                        result.improvements.append({
                            "agent_id": agent["id"],
                            "improvement": agent["performance_delta"],
                            "changes": agent.get("modifications", [])
                        })
            
            self.logger.info(
                "Results collected",
                patterns_found=len(patterns),
                improvements_found=len(result.improvements)
            )
            
        except Exception as e:
            self.logger.error("Failed to collect results", error=str(e))
            result.errors.append(f"Result collection error: {str(e)}")
    
    async def analyze_trial(self, result: EvolutionTrialResult) -> Dict[str, Any]:
        """Analyze trial results for insights.
        
        Args:
            result: Completed trial result
            
        Returns:
            Analysis summary
        """
        self.logger.info("Analyzing trial results", trial_id=result.trial_id)
        
        analysis = {
            "trial_id": result.trial_id,
            "duration_seconds": (
                result.end_time - result.start_time
            ).total_seconds() if result.end_time else 0,
            "success_rate": len(result.improvements) / self.config.population_size
            if self.config.population_size > 0 else 0,
            "average_improvement": sum(
                imp["improvement"] for imp in result.improvements
            ) / len(result.improvements) if result.improvements else 0,
            "best_improvement": max(
                (imp["improvement"] for imp in result.improvements),
                default=0
            ),
            "patterns_discovered": len(result.metrics.get("patterns", [])),
            "token_efficiency": result.metrics.get("tokens_used", 0) / 
            max(len(result.improvements), 1)
        }
        
        return analysis