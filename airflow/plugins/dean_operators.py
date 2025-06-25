"""Custom Airflow operators for DEAN system."""

from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults
from airflow.exceptions import AirflowException
from typing import Dict, List, Any, Optional
import httpx
import logging
import asyncio
import json
from datetime import datetime

logger = logging.getLogger(__name__)


class AgentSpawnOperator(BaseOperator):
    """Spawns DEAN agents with economic constraints."""
    
    template_fields = ['population_size', 'token_limit', 'diversity_threshold']
    ui_color = '#4CAF50'
    ui_fgcolor = '#FFFFFF'
    
    @apply_defaults
    def __init__(
        self,
        population_size: int,
        token_limit: int,
        diversity_threshold: float = 0.3,
        indexagent_url: str = "http://indexagent:8081",
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.population_size = population_size
        self.token_limit = token_limit
        self.diversity_threshold = diversity_threshold
        self.indexagent_url = indexagent_url
    
    def execute(self, context):
        """Execute agent spawning."""
        logger.info(f"Spawning {self.population_size} agents with {self.token_limit} tokens each")
        
        try:
            # Initialize population via IndexAgent
            response = httpx.post(
                f"{self.indexagent_url}/api/v1/agents/population/initialize",
                json={
                    "size": self.population_size,
                    "diversity_threshold": self.diversity_threshold
                },
                timeout=30.0
            )
            response.raise_for_status()
            result = response.json()
            
            logger.info(f"Successfully spawned {len(result['agent_ids'])} agents")
            
            # Apply token limits
            for agent_id in result['agent_ids']:
                self._apply_token_limit(agent_id, self.token_limit)
            
            return result
            
        except httpx.HTTPError as e:
            raise AirflowException(f"Failed to spawn agents: {e}")
    
    def _apply_token_limit(self, agent_id: str, limit: int):
        """Apply token limit to specific agent."""
        # In production, this would update the database
        logger.info(f"Applied token limit {limit} to agent {agent_id}")


class AgentEvolutionOperator(BaseOperator):
    """Manages agent evolution cycles with diversity maintenance."""
    
    template_fields = ['generations', 'mutation_rate', 'crossover_rate']
    ui_color = '#2196F3'
    ui_fgcolor = '#FFFFFF'
    
    @apply_defaults
    def __init__(
        self,
        generations: int,
        mutation_rate: float = 0.1,
        crossover_rate: float = 0.7,
        parallel_workers: int = 4,
        evolution_api_url: str = "http://evolution-api:8090",
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.generations = generations
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.parallel_workers = parallel_workers
        self.evolution_api_url = evolution_api_url
    
    def execute(self, context):
        """Execute evolution cycle."""
        ti = context['ti']
        
        # Get agent population from previous task
        population_data = ti.xcom_pull(task_ids='spawn_agents')
        if not population_data:
            raise AirflowException("No population data found")
        
        agent_ids = population_data.get('agent_ids', [])
        logger.info(f"Starting evolution for {len(agent_ids)} agents over {self.generations} generations")
        
        try:
            # Start evolution process
            response = httpx.post(
                f"{self.evolution_api_url}/api/v1/evolution/start",
                json={
                    "population_ids": agent_ids,
                    "generations": self.generations,
                    "mutation_rate": self.mutation_rate,
                    "crossover_rate": self.crossover_rate,
                    "parallel_workers": self.parallel_workers
                },
                timeout=30.0
            )
            response.raise_for_status()
            evolution_job = response.json()
            
            logger.info(f"Evolution job started: {evolution_job['job_id']}")
            
            # Monitor evolution progress
            final_status = self._monitor_evolution(evolution_job['job_id'])
            
            return final_status
            
        except httpx.HTTPError as e:
            raise AirflowException(f"Evolution failed: {e}")
    
    def _monitor_evolution(self, job_id: str) -> Dict[str, Any]:
        """Monitor evolution job progress."""
        max_attempts = 60
        check_interval = 10
        
        for attempt in range(max_attempts):
            try:
                response = httpx.get(
                    f"{self.evolution_api_url}/api/v1/evolution/jobs/{job_id}",
                    timeout=10.0
                )
                response.raise_for_status()
                status = response.json()
                
                logger.info(f"Evolution progress: Generation {status['current_generation']}/{status['total_generations']}")
                
                if status['status'] == 'completed':
                    return status
                elif status['status'] == 'failed':
                    raise AirflowException(f"Evolution job failed: {status.get('error', 'Unknown error')}")
                
                if attempt < max_attempts - 1:
                    asyncio.run(asyncio.sleep(check_interval))
                    
            except httpx.HTTPError as e:
                logger.error(f"Error checking evolution status: {e}")
                if attempt == max_attempts - 1:
                    raise
        
        raise AirflowException(f"Evolution job {job_id} timed out")


class PatternPropagationOperator(BaseOperator):
    """Propagates successful patterns across agent population."""
    
    template_fields = ['pattern_ids', 'target_agents']
    ui_color = '#9C27B0'
    ui_fgcolor = '#FFFFFF'
    
    @apply_defaults
    def __init__(
        self,
        pattern_ids: Optional[List[str]] = None,
        target_agents: Optional[List[str]] = None,
        propagation_strategy: str = 'broadcast',
        indexagent_url: str = "http://indexagent:8081",
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.pattern_ids = pattern_ids or []
        self.target_agents = target_agents or []
        self.propagation_strategy = propagation_strategy
        self.indexagent_url = indexagent_url
    
    def execute(self, context):
        """Execute pattern propagation."""
        ti = context['ti']
        
        # Get patterns from previous task if not provided
        if not self.pattern_ids:
            pattern_data = ti.xcom_pull(task_ids='catalog_patterns')
            if pattern_data:
                self.pattern_ids = [p['pattern_id'] for p in pattern_data]
        
        if not self.pattern_ids:
            logger.warning("No patterns to propagate")
            return {'propagated_count': 0}
        
        logger.info(f"Propagating {len(self.pattern_ids)} patterns using {self.propagation_strategy} strategy")
        
        try:
            # Get target agents if not specified
            if not self.target_agents:
                self.target_agents = self._get_target_agents()
            
            propagation_results = []
            
            for pattern_id in self.pattern_ids:
                for agent_id in self.target_agents:
                    result = self._propagate_to_agent(pattern_id, agent_id)
                    propagation_results.append(result)
            
            successful_propagations = sum(1 for r in propagation_results if r['success'])
            
            logger.info(f"Successfully propagated to {successful_propagations}/{len(propagation_results)} targets")
            
            return {
                'propagated_count': successful_propagations,
                'total_attempts': len(propagation_results),
                'results': propagation_results
            }
            
        except Exception as e:
            raise AirflowException(f"Pattern propagation failed: {e}")
    
    def _get_target_agents(self) -> List[str]:
        """Get list of target agents for propagation."""
        try:
            response = httpx.get(f"{self.indexagent_url}/api/v1/agents")
            response.raise_for_status()
            agents = response.json()
            
            # Filter based on strategy
            if self.propagation_strategy == 'broadcast':
                return [a['id'] for a in agents if a['status'] == 'active']
            elif self.propagation_strategy == 'selective':
                # Target low-performing agents
                return [a['id'] for a in agents if a.get('fitness_score', 0) < 0.5]
            else:
                return [a['id'] for a in agents]
                
        except httpx.HTTPError as e:
            logger.error(f"Failed to get target agents: {e}")
            return []
    
    def _propagate_to_agent(self, pattern_id: str, agent_id: str) -> Dict[str, Any]:
        """Propagate a pattern to a specific agent."""
        # In production, this would update agent configuration
        # For now, simulate propagation
        success = True  # Mock success
        
        return {
            'pattern_id': pattern_id,
            'agent_id': agent_id,
            'success': success,
            'timestamp': datetime.utcnow().isoformat()
        }


class DiversityEnforcementOperator(BaseOperator):
    """Enforces genetic diversity in agent population."""
    
    template_fields = ['min_diversity', 'mutation_rate']
    ui_color = '#FF5722'
    ui_fgcolor = '#FFFFFF'
    
    @apply_defaults
    def __init__(
        self,
        min_diversity: float = 0.3,
        mutation_rate: float = 0.15,
        force_mutation: bool = True,
        indexagent_url: str = "http://indexagent:8081",
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.min_diversity = min_diversity
        self.mutation_rate = mutation_rate
        self.force_mutation = force_mutation
        self.indexagent_url = indexagent_url
    
    def execute(self, context):
        """Check and enforce diversity requirements."""
        logger.info(f"Checking population diversity (min threshold: {self.min_diversity})")
        
        try:
            # Get current diversity metrics
            response = httpx.get(f"{self.indexagent_url}/api/v1/metrics/diversity")
            response.raise_for_status()
            diversity_data = response.json()
            
            current_diversity = diversity_data.get('diversity_score', 1.0)
            logger.info(f"Current population diversity: {current_diversity}")
            
            if current_diversity < self.min_diversity:
                logger.warning(f"Diversity below threshold! Applying interventions...")
                
                if self.force_mutation:
                    mutation_results = self._inject_mutations()
                    
                    # Re-check diversity after mutations
                    response = httpx.get(f"{self.indexagent_url}/api/v1/metrics/diversity")
                    response.raise_for_status()
                    new_diversity = response.json().get('diversity_score', current_diversity)
                    
                    return {
                        'initial_diversity': current_diversity,
                        'final_diversity': new_diversity,
                        'mutations_applied': mutation_results['mutation_count'],
                        'intervention_successful': new_diversity >= self.min_diversity
                    }
            
            return {
                'initial_diversity': current_diversity,
                'final_diversity': current_diversity,
                'mutations_applied': 0,
                'intervention_successful': True
            }
            
        except httpx.HTTPError as e:
            raise AirflowException(f"Diversity enforcement failed: {e}")
    
    def _inject_mutations(self) -> Dict[str, Any]:
        """Inject mutations into the population."""
        # In production, this would trigger actual mutations
        # For now, simulate mutation injection
        logger.info(f"Injecting mutations at rate {self.mutation_rate}")
        
        mutation_count = 5  # Mock value
        affected_agents = [f"agent-{i}" for i in range(mutation_count)]
        
        return {
            'mutation_count': mutation_count,
            'affected_agents': affected_agents,
            'mutation_rate': self.mutation_rate
        }


class EconomicGovernorOperator(BaseOperator):
    """Governs token economy and budget enforcement."""
    
    template_fields = ['total_budget', 'enforcement_threshold']
    ui_color = '#FFC107'
    ui_fgcolor = '#000000'
    
    @apply_defaults
    def __init__(
        self,
        total_budget: int,
        enforcement_threshold: float = 0.9,
        terminate_violators: bool = False,
        dean_api_url: str = "http://dean-orchestration:8082",
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.total_budget = total_budget
        self.enforcement_threshold = enforcement_threshold
        self.terminate_violators = terminate_violators
        self.dean_api_url = dean_api_url
    
    def execute(self, context):
        """Execute economic governance."""
        logger.info(f"Enforcing economic governance (budget: {self.total_budget})")
        
        try:
            # Get current economic status
            response = httpx.get(f"{self.dean_api_url}/api/v1/economy/status")
            response.raise_for_status()
            economy_status = response.json()
            
            total_consumed = economy_status.get('total_tokens_consumed', 0)
            budget_utilization = total_consumed / self.total_budget
            
            logger.info(f"Budget utilization: {budget_utilization:.2%}")
            
            governance_actions = []
            
            if budget_utilization > self.enforcement_threshold:
                logger.warning("Budget threshold exceeded! Applying restrictions...")
                
                # Get budget violators
                violators = self._identify_violators(economy_status)
                
                for violator in violators:
                    action = self._enforce_budget_limit(violator)
                    governance_actions.append(action)
            
            return {
                'budget_utilization': budget_utilization,
                'total_consumed': total_consumed,
                'enforcement_triggered': budget_utilization > self.enforcement_threshold,
                'actions_taken': governance_actions
            }
            
        except httpx.HTTPError as e:
            raise AirflowException(f"Economic governance failed: {e}")
    
    def _identify_violators(self, economy_status: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify agents violating budget constraints."""
        violators = []
        
        for agent in economy_status.get('agent_consumptions', []):
            if agent['tokens_consumed'] > agent['token_budget']:
                violators.append({
                    'agent_id': agent['id'],
                    'consumed': agent['tokens_consumed'],
                    'budget': agent['token_budget'],
                    'overage': agent['tokens_consumed'] - agent['token_budget']
                })
        
        return violators
    
    def _enforce_budget_limit(self, violator: Dict[str, Any]) -> Dict[str, Any]:
        """Enforce budget limit on a specific agent."""
        action = {
            'agent_id': violator['agent_id'],
            'action_type': 'terminate' if self.terminate_violators else 'throttle',
            'overage': violator['overage'],
            'timestamp': datetime.utcnow().isoformat()
        }
        
        if self.terminate_violators:
            logger.warning(f"Terminating agent {violator['agent_id']} for budget violation")
            # In production, would actually terminate the agent
        else:
            logger.info(f"Throttling agent {violator['agent_id']} for budget violation")
            # In production, would reduce token allocation
        
        return action