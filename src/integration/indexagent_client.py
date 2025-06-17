"""IndexAgent API client implementation."""

from typing import Any, Dict, List, Optional
from .base import ServiceClient


class IndexAgentClient(ServiceClient):
    """Client for IndexAgent API communication.
    
    Provides methods for:
    - Agent management (create, list, get, delete)
    - Evolution operations (population, generation, metrics)
    - Code search functionality
    """
    
    def __init__(self, base_url: str = "http://localhost:8081", **kwargs):
        """Initialize IndexAgent client.
        
        Args:
            base_url: IndexAgent API base URL
            **kwargs: Additional arguments for ServiceClient
        """
        super().__init__(base_url, "IndexAgent", **kwargs)
    
    async def health_check(self) -> Dict[str, Any]:
        """Check IndexAgent service health.
        
        Returns:
            Health status with service details
        """
        return await self.get("/health")
    
    # Agent Management
    
    async def list_agents(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        agent_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List all agents in the system.
        
        Args:
            limit: Maximum number of agents to return
            offset: Number of agents to skip
            agent_type: Filter by agent type
            
        Returns:
            List of agent configurations
        """
        params = {}
        if limit is not None:
            params['limit'] = limit
        if offset is not None:
            params['offset'] = offset
        if agent_type:
            params['type'] = agent_type
            
        return await self.get("/agents", params=params)
    
    async def create_agent(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new agent.
        
        Args:
            config: Agent configuration including:
                - name: Agent name
                - type: Agent type (optimization, analysis, etc.)
                - parameters: Type-specific parameters
                
        Returns:
            Created agent details with ID
        """
        return await self.post("/agents", json=config)
    
    async def get_agent(self, agent_id: str) -> Dict[str, Any]:
        """Get details for a specific agent.
        
        Args:
            agent_id: Unique agent identifier
            
        Returns:
            Agent configuration and status
        """
        return await self.get(f"/agents/{agent_id}")
    
    async def update_agent(self, agent_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update agent configuration.
        
        Args:
            agent_id: Unique agent identifier
            updates: Configuration updates
            
        Returns:
            Updated agent details
        """
        return await self.patch(f"/agents/{agent_id}", json=updates)
    
    async def delete_agent(self, agent_id: str) -> Dict[str, Any]:
        """Delete an agent.
        
        Args:
            agent_id: Unique agent identifier
            
        Returns:
            Deletion confirmation
        """
        return await self.delete(f"/agents/{agent_id}")
    
    # Evolution Operations
    
    async def initialize_population(
        self,
        size: int,
        agent_type: str,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Initialize a new agent population.
        
        Args:
            size: Population size
            agent_type: Type of agents to create
            config: Population configuration
            
        Returns:
            Population initialization details
        """
        payload = {
            "size": size,
            "agent_type": agent_type,
            "config": config or {},
        }
        return await self.post("/evolution/population", json=payload)
    
    async def trigger_generation(
        self,
        population_id: str,
        generation_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Trigger a new generation in the evolution process.
        
        Args:
            population_id: Population identifier
            generation_config: Generation-specific configuration
            
        Returns:
            Generation execution details
        """
        payload = {
            "population_id": population_id,
            "config": generation_config or {},
        }
        return await self.post("/evolution/generation", json=payload)
    
    async def get_evolution_metrics(
        self,
        population_id: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Retrieve evolution metrics.
        
        Args:
            population_id: Filter by population
            start_time: Metrics start time (ISO format)
            end_time: Metrics end time (ISO format)
            
        Returns:
            Evolution performance metrics
        """
        params = {}
        if population_id:
            params['population_id'] = population_id
        if start_time:
            params['start_time'] = start_time
        if end_time:
            params['end_time'] = end_time
            
        return await self.get("/evolution/metrics", params=params)
    
    async def get_lineage(self, agent_id: str) -> Dict[str, Any]:
        """Get agent lineage information.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Agent lineage tree with ancestors and descendants
        """
        return await self.get(f"/agents/{agent_id}/lineage")
    
    # Code Search Operations
    
    async def search_code(
        self,
        query: str,
        repositories: Optional[List[str]] = None,
        file_types: Optional[List[str]] = None,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """Search code repositories.
        
        Args:
            query: Search query string
            repositories: List of repository URLs to search
            file_types: Filter by file extensions
            limit: Maximum results to return
            
        Returns:
            Search results with code snippets
        """
        payload = {
            "query": query,
            "repositories": repositories or [],
            "file_types": file_types or [],
            "limit": limit,
        }
        return await self.post("/search", json=payload)
    
    async def get_index_status(self) -> Dict[str, Any]:
        """Get code indexing status.
        
        Returns:
            Indexing status and statistics
        """
        return await self.get("/search/index/status")
    
    async def trigger_reindex(self, repository: Optional[str] = None) -> Dict[str, Any]:
        """Trigger repository reindexing.
        
        Args:
            repository: Specific repository to reindex (or all if None)
            
        Returns:
            Reindexing job details
        """
        payload = {}
        if repository:
            payload['repository'] = repository
            
        return await self.post("/search/index/trigger", json=payload)
    
    # Pattern Operations
    
    async def get_patterns(
        self,
        pattern_type: Optional[str] = None,
        min_effectiveness: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """Get discovered patterns.
        
        Args:
            pattern_type: Filter by pattern type
            min_effectiveness: Minimum effectiveness threshold
            
        Returns:
            List of discovered patterns
        """
        params = {}
        if pattern_type:
            params['type'] = pattern_type
        if min_effectiveness is not None:
            params['min_effectiveness'] = min_effectiveness
            
        return await self.get("/patterns", params=params)
    
    async def apply_pattern(
        self,
        pattern_id: str,
        target_agents: List[str],
    ) -> Dict[str, Any]:
        """Apply a pattern to target agents.
        
        Args:
            pattern_id: Pattern identifier
            target_agents: List of agent IDs to apply pattern to
            
        Returns:
            Pattern application results
        """
        payload = {
            "pattern_id": pattern_id,
            "target_agents": target_agents,
        }
        return await self.post("/patterns/apply", json=payload)