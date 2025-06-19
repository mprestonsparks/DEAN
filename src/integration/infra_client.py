"""Infrastructure service clients implementation."""

from typing import Any, Dict, List, Optional
from datetime import datetime
from .base import ServiceClient


class EvolutionAPIClient(ServiceClient):
    """Client for Evolution API communication.
    
    Provides methods for:
    - Evolution control (start, stop, status)
    - Pattern management
    - Meta-learning operations
    """
    
    def __init__(self, base_url: str = "http://localhost:8090", **kwargs):
        """Initialize Evolution API client.
        
        Args:
            base_url: Evolution API base URL
            **kwargs: Additional arguments for ServiceClient
        """
        super().__init__(base_url, "EvolutionAPI", **kwargs)
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Evolution API service health.
        
        Returns:
            Health status with service details
        """
        return await self.get("/health")
    
    # Evolution Control
    
    async def start_evolution(
        self,
        population_size: int = 50,
        generations: int = 10,
        mutation_rate: float = 0.1,
        crossover_rate: float = 0.7,
        selection_method: str = "tournament",
        constraints: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Start a new evolution cycle.
        
        Args:
            population_size: Initial population size
            generations: Number of generations to run
            mutation_rate: Probability of mutation
            crossover_rate: Probability of crossover
            selection_method: Selection algorithm (tournament, roulette, rank)
            constraints: Additional constraints (max_tokens, time_limit, etc.)
            
        Returns:
            Evolution trial details with trial_id
        """
        payload = {
            "population_size": population_size,
            "generations": generations,
            "mutation_rate": mutation_rate,
            "crossover_rate": crossover_rate,
            "selection_method": selection_method,
            "constraints": constraints or {},
        }
        return await self.post("/evolution/start", json=payload)
    
    async def get_evolution_status(self, trial_id: Optional[str] = None) -> Dict[str, Any]:
        """Get current evolution status.
        
        Args:
            trial_id: Specific trial ID (or current if None)
            
        Returns:
            Evolution status including current generation and metrics
        """
        endpoint = "/evolution/status"
        if trial_id:
            endpoint += f"?trial_id={trial_id}"
        return await self.get(endpoint)
    
    async def stop_evolution(self, trial_id: Optional[str] = None) -> Dict[str, Any]:
        """Stop the current evolution cycle.
        
        Args:
            trial_id: Specific trial ID to stop (or current if None)
            
        Returns:
            Final evolution status and summary
        """
        payload = {}
        if trial_id:
            payload['trial_id'] = trial_id
        return await self.post("/evolution/stop", json=payload)
    
    async def pause_evolution(self, trial_id: Optional[str] = None) -> Dict[str, Any]:
        """Pause the current evolution cycle.
        
        Args:
            trial_id: Specific trial ID to pause
            
        Returns:
            Pause confirmation
        """
        payload = {}
        if trial_id:
            payload['trial_id'] = trial_id
        return await self.post("/evolution/pause", json=payload)
    
    async def resume_evolution(self, trial_id: str) -> Dict[str, Any]:
        """Resume a paused evolution cycle.
        
        Args:
            trial_id: Trial ID to resume
            
        Returns:
            Resume confirmation
        """
        return await self.post("/evolution/resume", json={"trial_id": trial_id})
    
    # Pattern Management
    
    async def get_patterns(
        self,
        pattern_type: Optional[str] = None,
        min_effectiveness: Optional[float] = None,
        trial_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve discovered patterns.
        
        Args:
            pattern_type: Filter by pattern type
            min_effectiveness: Minimum effectiveness threshold
            trial_id: Filter by evolution trial
            
        Returns:
            List of discovered patterns
        """
        params = {}
        if pattern_type:
            params['type'] = pattern_type
        if min_effectiveness is not None:
            params['min_effectiveness'] = min_effectiveness
        if trial_id:
            params['trial_id'] = trial_id
            
        return await self.get("/patterns", params=params)
    
    async def apply_patterns(
        self,
        pattern_ids: List[str],
        target_population: str,
    ) -> Dict[str, Any]:
        """Apply patterns to agent population.
        
        Args:
            pattern_ids: List of pattern IDs to apply
            target_population: Target population ID
            
        Returns:
            Pattern application results
        """
        payload = {
            "pattern_ids": pattern_ids,
            "target_population": target_population,
        }
        return await self.post("/patterns/apply", json=payload)
    
    async def evaluate_pattern(
        self,
        pattern_id: str,
        test_agents: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Evaluate pattern effectiveness.
        
        Args:
            pattern_id: Pattern to evaluate
            test_agents: Specific agents to test on
            
        Returns:
            Pattern evaluation metrics
        """
        payload = {
            "pattern_id": pattern_id,
        }
        if test_agents:
            payload['test_agents'] = test_agents
            
        return await self.post("/patterns/evaluate", json=payload)
    
    # Meta-Learning Operations
    
    async def extract_strategies(
        self,
        trial_id: str,
        min_performance_delta: float = 0.1,
    ) -> List[Dict[str, Any]]:
        """Extract successful strategies from evolution trial.
        
        Args:
            trial_id: Evolution trial to analyze
            min_performance_delta: Minimum performance improvement
            
        Returns:
            List of extracted strategies
        """
        payload = {
            "trial_id": trial_id,
            "min_performance_delta": min_performance_delta,
        }
        return await self.post("/meta-learning/extract", json=payload)
    
    async def transfer_learning(
        self,
        source_domain: str,
        target_domain: str,
        strategies: List[str],
    ) -> Dict[str, Any]:
        """Transfer strategies between domains.
        
        Args:
            source_domain: Source domain identifier
            target_domain: Target domain identifier
            strategies: Strategy IDs to transfer
            
        Returns:
            Transfer results and effectiveness
        """
        payload = {
            "source_domain": source_domain,
            "target_domain": target_domain,
            "strategies": strategies,
        }
        return await self.post("/meta-learning/transfer", json=payload)
    
    # Metrics
    
    async def get_metrics(self, format: str = "prometheus") -> str:
        """Get evolution metrics in specified format.
        
        Args:
            format: Metric format (prometheus, json)
            
        Returns:
            Metrics in requested format
        """
        headers = {}
        if format == "prometheus":
            headers['Accept'] = "text/plain"
        
        response = await self._request('GET', "/metrics", headers=headers)
        return response if isinstance(response, str) else str(response)
    
    async def get_trial_history(
        self,
        limit: int = 10,
        offset: int = 0,
        status: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get evolution trial history.
        
        Args:
            limit: Maximum trials to return
            offset: Number of trials to skip
            status: Filter by status (running, completed, failed)
            
        Returns:
            Paginated trial history
        """
        params = {
            'limit': limit,
            'offset': offset,
        }
        if status:
            params['status'] = status
            
        return await self.get("/trials", params=params)


class InfrastructureClient:
    """Aggregated client for infrastructure services.
    
    Provides unified access to:
    - Evolution API
    - Database operations (future)
    - Cache operations (future)
    - Monitoring services (future)
    """
    
    def __init__(
        self,
        evolution_api_url: str = "http://localhost:8090",
        database_url: Optional[str] = None,
        redis_url: Optional[str] = None,
        service_name: Optional[str] = None,
        pushgateway_url: Optional[str] = None,
        **kwargs
    ):
        """Initialize infrastructure client.
        
        Args:
            evolution_api_url: Evolution API URL
            database_url: PostgreSQL connection URL
            redis_url: Redis connection URL
            service_name: Service name for monitoring
            pushgateway_url: Prometheus pushgateway URL
            **kwargs: Additional configuration
        """
        self.evolution = EvolutionAPIClient(evolution_api_url, **kwargs)
        
        # Initialize database client if URL provided
        self.database = None
        if database_url:
            from .database_client import DatabaseClient
            self.database = DatabaseClient(database_url)
        
        # Initialize cache client if URL provided
        self.cache = None
        if redis_url:
            from .redis_cache_client import RedisCacheClient
            self.cache = RedisCacheClient(
                redis_url=redis_url,
                password=kwargs.get("redis_password")
            )
        
        # Initialize monitoring client if service name provided
        self.monitoring = None
        if service_name:
            from .monitoring_client import MonitoringClient
            self.monitoring = MonitoringClient(
                service_name=service_name,
                pushgateway_url=pushgateway_url,
                custom_labels=kwargs.get("custom_labels", {})
            )
    
    async def connect_all(self):
        """Connect all configured clients."""
        if self.database:
            await self.database.connect()
        
        if self.cache:
            await self.cache.connect()
        
        if self.monitoring:
            await self.monitoring.start()
    
    async def close(self):
        """Close all client connections."""
        await self.evolution.close()
        
        if self.database:
            await self.database.disconnect()
        
        if self.cache:
            await self.cache.disconnect()
        
        if self.monitoring:
            await self.monitoring.stop()
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()