"""Mock service implementations for testing."""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from aiohttp import web
import uuid


class MockIndexAgentService:
    """Mock implementation of IndexAgent API for testing."""
    
    def __init__(self, port: int = 18081):
        self.port = port
        self.agents: Dict[str, Dict[str, Any]] = {}
        self.populations: Dict[str, Dict[str, Any]] = {}
        self.patterns: List[Dict[str, Any]] = []
        self.search_results: List[Dict[str, Any]] = []
        
        # Add some default test data
        self._initialize_test_data()
    
    def _initialize_test_data(self):
        """Initialize with test data."""
        # Add a test agent
        test_agent_id = "test_agent_001"
        self.agents[test_agent_id] = {
            "id": test_agent_id,
            "name": "Test Performance Agent",
            "type": "optimization",
            "status": "active",
            "created_at": datetime.utcnow().isoformat(),
            "parameters": {
                "target": "performance",
                "language": "python"
            }
        }
        
        # Add a test pattern
        self.patterns.append({
            "id": "pattern_001",
            "type": "optimization",
            "effectiveness": 0.85,
            "description": "Loop optimization pattern",
            "discovered_at": datetime.utcnow().isoformat()
        })
    
    def create_app(self) -> web.Application:
        """Create aiohttp application with routes."""
        app = web.Application()
        app.router.add_get('/health', self.health_check)
        app.router.add_get('/agents', self.list_agents)
        app.router.add_post('/agents', self.create_agent)
        app.router.add_get('/agents/{agent_id}', self.get_agent)
        app.router.add_patch('/agents/{agent_id}', self.update_agent)
        app.router.add_delete('/agents/{agent_id}', self.delete_agent)
        app.router.add_post('/evolution/population', self.initialize_population)
        app.router.add_post('/evolution/generation', self.trigger_generation)
        app.router.add_get('/evolution/metrics', self.get_evolution_metrics)
        app.router.add_get('/patterns', self.get_patterns)
        app.router.add_post('/patterns/apply', self.apply_pattern)
        app.router.add_post('/search', self.search_code)
        app.router.add_get('/search/index/status', self.get_index_status)
        return app
    
    async def health_check(self, request: web.Request) -> web.Response:
        """Health check endpoint."""
        return web.json_response({
            "status": "healthy",
            "service": "MockIndexAgent",
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def list_agents(self, request: web.Request) -> web.Response:
        """List agents endpoint."""
        limit = int(request.query.get('limit', 10))
        offset = int(request.query.get('offset', 0))
        
        agents_list = list(self.agents.values())[offset:offset + limit]
        return web.json_response(agents_list)
    
    async def create_agent(self, request: web.Request) -> web.Response:
        """Create agent endpoint."""
        data = await request.json()
        agent_id = f"agent_{uuid.uuid4().hex[:8]}"
        
        agent = {
            "id": agent_id,
            "name": data.get("name", "Unnamed Agent"),
            "type": data.get("type", "generic"),
            "status": "active",
            "created_at": datetime.utcnow().isoformat(),
            "parameters": data.get("parameters", {})
        }
        
        self.agents[agent_id] = agent
        return web.json_response(agent, status=201)
    
    async def get_agent(self, request: web.Request) -> web.Response:
        """Get agent endpoint."""
        agent_id = request.match_info['agent_id']
        
        if agent_id not in self.agents:
            return web.json_response(
                {"error": "Agent not found"},
                status=404
            )
        
        return web.json_response(self.agents[agent_id])
    
    async def update_agent(self, request: web.Request) -> web.Response:
        """Update agent endpoint."""
        agent_id = request.match_info['agent_id']
        
        if agent_id not in self.agents:
            return web.json_response(
                {"error": "Agent not found"},
                status=404
            )
        
        data = await request.json()
        self.agents[agent_id].update(data)
        self.agents[agent_id]["updated_at"] = datetime.utcnow().isoformat()
        
        return web.json_response(self.agents[agent_id])
    
    async def delete_agent(self, request: web.Request) -> web.Response:
        """Delete agent endpoint."""
        agent_id = request.match_info['agent_id']
        
        if agent_id not in self.agents:
            return web.json_response(
                {"error": "Agent not found"},
                status=404
            )
        
        del self.agents[agent_id]
        return web.json_response({"status": "deleted"})
    
    async def initialize_population(self, request: web.Request) -> web.Response:
        """Initialize population endpoint."""
        data = await request.json()
        population_id = f"pop_{uuid.uuid4().hex[:8]}"
        
        population = {
            "id": population_id,
            "size": data.get("size", 10),
            "agent_type": data.get("agent_type", "generic"),
            "created_at": datetime.utcnow().isoformat(),
            "config": data.get("config", {})
        }
        
        self.populations[population_id] = population
        
        # Create agents for the population
        for i in range(population["size"]):
            agent_id = f"agent_{population_id}_{i}"
            self.agents[agent_id] = {
                "id": agent_id,
                "name": f"Agent {i}",
                "type": population["agent_type"],
                "population_id": population_id,
                "status": "active",
                "created_at": datetime.utcnow().isoformat()
            }
        
        return web.json_response(population)
    
    async def trigger_generation(self, request: web.Request) -> web.Response:
        """Trigger generation endpoint."""
        data = await request.json()
        
        return web.json_response({
            "generation_id": f"gen_{uuid.uuid4().hex[:8]}",
            "population_id": data.get("population_id"),
            "status": "started",
            "started_at": datetime.utcnow().isoformat()
        })
    
    async def get_evolution_metrics(self, request: web.Request) -> web.Response:
        """Get evolution metrics endpoint."""
        return web.json_response({
            "metrics": {
                "total_agents": len(self.agents),
                "active_populations": len(self.populations),
                "patterns_discovered": len(self.patterns),
                "average_fitness": 0.75,
                "best_fitness": 0.92,
                "diversity_score": 0.65
            },
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def get_patterns(self, request: web.Request) -> web.Response:
        """Get patterns endpoint."""
        pattern_type = request.query.get('type')
        min_effectiveness = float(request.query.get('min_effectiveness', 0))
        
        filtered_patterns = [
            p for p in self.patterns
            if (not pattern_type or p['type'] == pattern_type)
            and p['effectiveness'] >= min_effectiveness
        ]
        
        return web.json_response(filtered_patterns)
    
    async def apply_pattern(self, request: web.Request) -> web.Response:
        """Apply pattern endpoint."""
        data = await request.json()
        
        return web.json_response({
            "status": "applied",
            "pattern_id": data.get("pattern_id"),
            "affected_agents": len(data.get("target_agents", [])),
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def search_code(self, request: web.Request) -> web.Response:
        """Search code endpoint."""
        data = await request.json()
        query = data.get("query", "")
        
        # Return mock search results
        results = [
            {
                "file": "src/example.py",
                "line": 42,
                "match": f"# {query} implementation",
                "repository": "test-repo"
            }
        ]
        
        return web.json_response({
            "query": query,
            "results": results,
            "total": len(results)
        })
    
    async def get_index_status(self, request: web.Request) -> web.Response:
        """Get index status endpoint."""
        return web.json_response({
            "status": "ready",
            "indexed_repositories": 3,
            "total_files": 1234,
            "last_update": datetime.utcnow().isoformat()
        })


class MockAirflowService:
    """Mock implementation of Airflow API for testing."""
    
    def __init__(self, port: int = 18080):
        self.port = port
        self.dags: Dict[str, Dict[str, Any]] = {}
        self.dag_runs: Dict[str, Dict[str, Any]] = {}
        
        self._initialize_test_data()
    
    def _initialize_test_data(self):
        """Initialize with test data."""
        # Add test DAG
        self.dags["evolution_workflow"] = {
            "dag_id": "evolution_workflow",
            "description": "Evolution workflow DAG",
            "is_paused": False,
            "is_active": True,
            "tags": ["evolution", "dean"]
        }
    
    def create_app(self) -> web.Application:
        """Create aiohttp application with routes."""
        app = web.Application()
        app.router.add_get('/api/v1/health', self.health_check)
        app.router.add_get('/api/v1/dags', self.list_dags)
        app.router.add_get('/api/v1/dags/{dag_id}', self.get_dag)
        app.router.add_patch('/api/v1/dags/{dag_id}', self.update_dag)
        app.router.add_post('/api/v1/dags/{dag_id}/dagRuns', self.trigger_dag)
        app.router.add_get('/api/v1/dags/{dag_id}/dagRuns/{dag_run_id}', self.get_dag_run)
        return app
    
    async def health_check(self, request: web.Request) -> web.Response:
        """Health check endpoint."""
        return web.json_response({
            "status": "healthy",
            "metadatabase": {"status": "healthy"},
            "scheduler": {"status": "healthy"}
        })
    
    async def list_dags(self, request: web.Request) -> web.Response:
        """List DAGs endpoint."""
        return web.json_response({
            "dags": list(self.dags.values()),
            "total_entries": len(self.dags)
        })
    
    async def get_dag(self, request: web.Request) -> web.Response:
        """Get DAG endpoint."""
        dag_id = request.match_info['dag_id']
        
        if dag_id not in self.dags:
            return web.json_response(
                {"error": "DAG not found"},
                status=404
            )
        
        return web.json_response(self.dags[dag_id])
    
    async def update_dag(self, request: web.Request) -> web.Response:
        """Update DAG endpoint."""
        dag_id = request.match_info['dag_id']
        
        if dag_id not in self.dags:
            return web.json_response(
                {"error": "DAG not found"},
                status=404
            )
        
        data = await request.json()
        self.dags[dag_id].update(data)
        
        return web.json_response(self.dags[dag_id])
    
    async def trigger_dag(self, request: web.Request) -> web.Response:
        """Trigger DAG endpoint."""
        dag_id = request.match_info['dag_id']
        
        if dag_id not in self.dags:
            return web.json_response(
                {"error": "DAG not found"},
                status=404
            )
        
        data = await request.json()
        dag_run_id = data.get("dag_run_id", f"run_{uuid.uuid4().hex[:8]}")
        
        dag_run = {
            "dag_run_id": dag_run_id,
            "dag_id": dag_id,
            "execution_date": data.get("execution_date", datetime.utcnow().isoformat()),
            "state": "running",
            "conf": data.get("conf", {})
        }
        
        self.dag_runs[dag_run_id] = dag_run
        
        # Simulate completion after a delay
        asyncio.create_task(self._complete_dag_run(dag_run_id))
        
        return web.json_response(dag_run)
    
    async def _complete_dag_run(self, dag_run_id: str):
        """Simulate DAG completion."""
        await asyncio.sleep(2)  # Simulate execution time
        if dag_run_id in self.dag_runs:
            self.dag_runs[dag_run_id]["state"] = "success"
    
    async def get_dag_run(self, request: web.Request) -> web.Response:
        """Get DAG run endpoint."""
        dag_run_id = request.match_info['dag_run_id']
        
        if dag_run_id not in self.dag_runs:
            return web.json_response(
                {"error": "DAG run not found"},
                status=404
            )
        
        return web.json_response(self.dag_runs[dag_run_id])


class MockEvolutionAPIService:
    """Mock implementation of Evolution API for testing."""
    
    def __init__(self, port: int = 18090):
        self.port = port
        self.trials: Dict[str, Dict[str, Any]] = {}
        self.patterns: List[Dict[str, Any]] = []
        self.current_trial: Optional[str] = None
    
    def create_app(self) -> web.Application:
        """Create aiohttp application with routes."""
        app = web.Application()
        app.router.add_get('/health', self.health_check)
        app.router.add_post('/evolution/start', self.start_evolution)
        app.router.add_get('/evolution/status', self.get_evolution_status)
        app.router.add_post('/evolution/stop', self.stop_evolution)
        app.router.add_get('/patterns', self.get_patterns)
        app.router.add_post('/patterns/apply', self.apply_patterns)
        app.router.add_get('/metrics', self.get_metrics)
        return app
    
    async def health_check(self, request: web.Request) -> web.Response:
        """Health check endpoint."""
        return web.json_response({
            "status": "healthy",
            "service": "MockEvolutionAPI",
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def start_evolution(self, request: web.Request) -> web.Response:
        """Start evolution endpoint."""
        data = await request.json()
        trial_id = f"trial_{uuid.uuid4().hex[:8]}"
        
        trial = {
            "trial_id": trial_id,
            "status": "running",
            "started_at": datetime.utcnow().isoformat(),
            "config": data,
            "current_generation": 0,
            "total_generations": data.get("generations", 10)
        }
        
        self.trials[trial_id] = trial
        self.current_trial = trial_id
        
        # Simulate evolution progress
        asyncio.create_task(self._simulate_evolution(trial_id))
        
        return web.json_response(trial)
    
    async def _simulate_evolution(self, trial_id: str):
        """Simulate evolution progress."""
        trial = self.trials.get(trial_id)
        if not trial:
            return
        
        for gen in range(trial["total_generations"]):
            await asyncio.sleep(1)  # Simulate generation time
            trial["current_generation"] = gen + 1
            
            # Add a pattern occasionally
            if gen % 3 == 0:
                self.patterns.append({
                    "id": f"pattern_{uuid.uuid4().hex[:8]}",
                    "type": "optimization",
                    "effectiveness": 0.7 + (gen * 0.02),
                    "trial_id": trial_id,
                    "generation": gen + 1
                })
        
        trial["status"] = "completed"
        trial["completed_at"] = datetime.utcnow().isoformat()
    
    async def get_evolution_status(self, request: web.Request) -> web.Response:
        """Get evolution status endpoint."""
        trial_id = request.query.get('trial_id', self.current_trial)
        
        if not trial_id or trial_id not in self.trials:
            return web.json_response({
                "status": "no_active_trial"
            })
        
        trial = self.trials[trial_id]
        return web.json_response({
            "trial_id": trial_id,
            "status": trial["status"],
            "current_generation": trial["current_generation"],
            "total_generations": trial["total_generations"],
            "best_fitness": 0.85,
            "diversity": 0.72
        })
    
    async def stop_evolution(self, request: web.Request) -> web.Response:
        """Stop evolution endpoint."""
        data = await request.json()
        trial_id = data.get("trial_id", self.current_trial)
        
        if trial_id and trial_id in self.trials:
            self.trials[trial_id]["status"] = "stopped"
            self.trials[trial_id]["stopped_at"] = datetime.utcnow().isoformat()
        
        return web.json_response({"status": "stopped"})
    
    async def get_patterns(self, request: web.Request) -> web.Response:
        """Get patterns endpoint."""
        return web.json_response(self.patterns)
    
    async def apply_patterns(self, request: web.Request) -> web.Response:
        """Apply patterns endpoint."""
        data = await request.json()
        
        return web.json_response({
            "status": "applied",
            "patterns_applied": len(data.get("pattern_ids", [])),
            "target_population": data.get("target_population")
        })
    
    async def get_metrics(self, request: web.Request) -> web.Response:
        """Get metrics endpoint."""
        # Return Prometheus-style metrics
        metrics = """
# HELP evolution_generations_total Total generations completed
# TYPE evolution_generations_total counter
evolution_generations_total 42

# HELP evolution_patterns_discovered Total patterns discovered
# TYPE evolution_patterns_discovered counter
evolution_patterns_discovered 7

# HELP evolution_fitness_best Best fitness score
# TYPE evolution_fitness_best gauge
evolution_fitness_best 0.92
"""
        return web.Response(text=metrics, content_type='text/plain')