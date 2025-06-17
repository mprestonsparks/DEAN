"""Service-specific adapter patterns for protocol handling."""

from typing import Any, Dict, List, Optional, Protocol
from datetime import datetime
import asyncio
from contextlib import asynccontextmanager

from .base import ServiceClient, ServiceError
from .indexagent_client import IndexAgentClient
from .airflow_client import AirflowClient
from .infra_client import EvolutionAPIClient


class EvolutionWorkflowAdapter:
    """Adapter for coordinating evolution workflows across services.
    
    Provides high-level operations that coordinate multiple services
    to execute complete evolution workflows.
    """
    
    def __init__(
        self,
        indexagent: IndexAgentClient,
        airflow: AirflowClient,
        evolution: EvolutionAPIClient,
    ):
        """Initialize workflow adapter.
        
        Args:
            indexagent: IndexAgent client
            airflow: Airflow client
            evolution: Evolution API client
        """
        self.indexagent = indexagent
        self.airflow = airflow
        self.evolution = evolution
    
    async def execute_evolution_trial(
        self,
        population_size: int,
        generations: int,
        agent_type: str = "optimization",
        dag_id: str = "evolution_workflow",
        **kwargs
    ) -> Dict[str, Any]:
        """Execute a complete evolution trial.
        
        Coordinates:
        1. Population initialization in IndexAgent
        2. Evolution start in Evolution API
        3. Workflow execution in Airflow
        4. Result aggregation
        
        Args:
            population_size: Size of agent population
            generations: Number of generations
            agent_type: Type of agents to evolve
            dag_id: Airflow DAG to execute
            **kwargs: Additional configuration
            
        Returns:
            Trial execution summary
        """
        trial_result = {
            "status": "initializing",
            "population_id": None,
            "trial_id": None,
            "dag_run_id": None,
            "start_time": datetime.utcnow().isoformat(),
        }
        
        try:
            # Step 1: Initialize population in IndexAgent
            population = await self.indexagent.initialize_population(
                size=population_size,
                agent_type=agent_type,
                config=kwargs.get("agent_config", {}),
            )
            trial_result["population_id"] = population.get("population_id")
            trial_result["status"] = "population_created"
            
            # Step 2: Start evolution in Evolution API
            evolution_config = {
                "population_size": population_size,
                "generations": generations,
                "mutation_rate": kwargs.get("mutation_rate", 0.1),
                "crossover_rate": kwargs.get("crossover_rate", 0.7),
                "selection_method": kwargs.get("selection_method", "tournament"),
            }
            evolution = await self.evolution.start_evolution(**evolution_config)
            trial_result["trial_id"] = evolution.get("trial_id")
            trial_result["status"] = "evolution_started"
            
            # Step 3: Trigger Airflow workflow
            dag_config = {
                "population_id": trial_result["population_id"],
                "trial_id": trial_result["trial_id"],
                "generations": generations,
                **kwargs.get("dag_config", {}),
            }
            dag_run = await self.airflow.trigger_dag(
                dag_id=dag_id,
                conf=dag_config,
            )
            trial_result["dag_run_id"] = dag_run.get("dag_run_id")
            trial_result["status"] = "workflow_triggered"
            
            # Step 4: Monitor execution (optional)
            if kwargs.get("wait_for_completion", False):
                timeout = kwargs.get("timeout", 3600)
                final_status = await self.airflow.wait_for_dag_completion(
                    dag_id=dag_id,
                    dag_run_id=trial_result["dag_run_id"],
                    timeout=timeout,
                )
                trial_result["workflow_status"] = final_status.get("state")
                
                # Get final evolution status
                evolution_status = await self.evolution.get_evolution_status(
                    trial_result["trial_id"]
                )
                trial_result["evolution_status"] = evolution_status
                trial_result["status"] = "completed"
            
            trial_result["end_time"] = datetime.utcnow().isoformat()
            return trial_result
            
        except Exception as e:
            trial_result["status"] = "failed"
            trial_result["error"] = str(e)
            trial_result["end_time"] = datetime.utcnow().isoformat()
            raise


class PatternPropagationAdapter:
    """Adapter for pattern propagation across services."""
    
    def __init__(
        self,
        indexagent: IndexAgentClient,
        evolution: EvolutionAPIClient,
    ):
        """Initialize pattern adapter.
        
        Args:
            indexagent: IndexAgent client
            evolution: Evolution API client
        """
        self.indexagent = indexagent
        self.evolution = evolution
    
    async def propagate_successful_patterns(
        self,
        trial_id: str,
        min_effectiveness: float = 0.7,
        target_agents: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Propagate successful patterns from evolution trial.
        
        Args:
            trial_id: Evolution trial to extract patterns from
            min_effectiveness: Minimum pattern effectiveness
            target_agents: Specific agents to apply patterns to
            
        Returns:
            Pattern propagation results
        """
        # Extract successful patterns
        patterns = await self.evolution.get_patterns(
            trial_id=trial_id,
            min_effectiveness=min_effectiveness,
        )
        
        if not patterns:
            return {
                "status": "no_patterns_found",
                "trial_id": trial_id,
            }
        
        # Get pattern details from IndexAgent
        detailed_patterns = []
        for pattern in patterns:
            pattern_detail = await self.indexagent.get_patterns(
                pattern_type=pattern.get("type"),
            )
            detailed_patterns.extend(pattern_detail)
        
        # Apply patterns to target agents
        if target_agents is None:
            # Get all active agents
            agents = await self.indexagent.list_agents()
            target_agents = [agent["id"] for agent in agents]
        
        results = []
        for pattern in detailed_patterns:
            result = await self.indexagent.apply_pattern(
                pattern_id=pattern["id"],
                target_agents=target_agents,
            )
            results.append(result)
        
        return {
            "status": "patterns_propagated",
            "patterns_count": len(detailed_patterns),
            "agents_updated": len(target_agents),
            "results": results,
        }


class HealthCheckAdapter:
    """Adapter for aggregated health checking across services."""
    
    def __init__(self, clients: Dict[str, ServiceClient]):
        """Initialize health check adapter.
        
        Args:
            clients: Dictionary of service name to client
        """
        self.clients = clients
    
    async def check_all_services(self) -> Dict[str, Any]:
        """Check health of all services concurrently.
        
        Returns:
            Aggregated health status
        """
        health_checks = {}
        
        # Run health checks concurrently
        tasks = {
            name: client.health_check()
            for name, client in self.clients.items()
        }
        
        results = await asyncio.gather(
            *tasks.values(),
            return_exceptions=True,
        )
        
        # Process results
        overall_status = "healthy"
        for (name, _), result in zip(tasks.items(), results):
            if isinstance(result, Exception):
                health_checks[name] = {
                    "status": "unhealthy",
                    "error": str(result),
                }
                overall_status = "unhealthy"
            else:
                health_checks[name] = result
                if result.get("status") != "healthy":
                    overall_status = "unhealthy"
        
        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "services": health_checks,
        }


class ServicePool:
    """Connection pool for managing multiple service clients."""
    
    def __init__(
        self,
        indexagent_url: str = "http://localhost:8081",
        airflow_url: str = "http://localhost:8080",
        evolution_url: str = "http://localhost:8090",
        **kwargs
    ):
        """Initialize service pool.
        
        Args:
            indexagent_url: IndexAgent API URL
            airflow_url: Airflow API URL
            evolution_url: Evolution API URL
            **kwargs: Additional client configuration
        """
        self.indexagent = IndexAgentClient(indexagent_url, **kwargs)
        self.airflow = AirflowClient(airflow_url, **kwargs)
        self.evolution = EvolutionAPIClient(evolution_url, **kwargs)
        
        self.clients = {
            "indexagent": self.indexagent,
            "airflow": self.airflow,
            "evolution": self.evolution,
        }
        
        # Initialize adapters
        self.workflow = EvolutionWorkflowAdapter(
            self.indexagent,
            self.airflow,
            self.evolution,
        )
        self.patterns = PatternPropagationAdapter(
            self.indexagent,
            self.evolution,
        )
        self.health = HealthCheckAdapter(self.clients)
    
    async def close(self):
        """Close all client connections."""
        for client in self.clients.values():
            await client.close()
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


@asynccontextmanager
async def create_service_pool(**kwargs) -> ServicePool:
    """Create a service pool with proper cleanup.
    
    Usage:
        async with create_service_pool() as pool:
            result = await pool.workflow.execute_evolution_trial(...)
    """
    pool = ServicePool(**kwargs)
    try:
        yield pool
    finally:
        await pool.close()