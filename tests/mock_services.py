"""Mock DEAN services for integration testing.

This module provides mock implementations of DEAN services (IndexAgent, Airflow, EvolutionAPI)
for testing the orchestration layer without requiring actual services to be running.
"""

from fastapi import FastAPI, HTTPException, Request
from typing import Dict, List, Any, Optional
import asyncio
import random
import uuid
from datetime import datetime
from pydantic import BaseModel


class MockAgentMetrics(BaseModel):
    """Mock agent metrics for testing."""
    agent_id: str
    fitness_score: float
    token_usage: int
    patterns_discovered: int
    efficiency_score: float


class MockIndexAgentService:
    """Mock IndexAgent service for testing."""
    
    def __init__(self):
        self.app = FastAPI()
        self.agents = {}
        self.populations = {}
        self.patterns = []
        self.setup_routes()
        
    def setup_routes(self):
        """Set up mock API routes."""
        
        @self.app.get("/health")
        async def health():
            return {"status": "healthy", "version": "1.0.0-mock"}
            
        @self.app.post("/api/v1/token/validate")
        async def validate_token(request: Dict[str, Any]):
            budget = request.get("budget", 100000)
            reserved = request.get("reserved_percentage", 0.1)
            
            return {
                "valid": True,
                "available_budget": budget * (1 - reserved),
                "budget_per_agent": budget * (1 - reserved) / 10  # Assume 10 agents
            }
            
        @self.app.post("/api/v1/agents/population/initialize")
        async def initialize_population(request: Dict[str, Any]):
            pop_id = str(uuid.uuid4())
            size = request.get("size", 10)
            
            # Create mock agents
            agent_ids = []
            for i in range(size):
                agent_id = str(uuid.uuid4())
                self.agents[agent_id] = MockAgentMetrics(
                    agent_id=agent_id,
                    fitness_score=random.uniform(0.1, 1.0),
                    token_usage=0,
                    patterns_discovered=0,
                    efficiency_score=random.uniform(0.5, 1.5)
                )
                agent_ids.append(agent_id)
                
            self.populations[pop_id] = {
                "id": pop_id,
                "agent_ids": agent_ids,
                "created_at": datetime.utcnow().isoformat()
            }
            
            return {
                "population_id": pop_id,
                "agent_ids": agent_ids,
                "size": size
            }
            
        @self.app.get("/api/v1/metrics/diversity")
        async def get_diversity_metrics(population_id: str):
            # Simulate diversity metrics
            return {
                "population_id": population_id,
                "variance": random.uniform(0.2, 0.5),
                "diversity_index": random.uniform(0.3, 0.7),
                "cluster_count": random.randint(3, 7)
            }
            
        @self.app.get("/api/v1/metrics/efficiency")
        async def get_efficiency_metrics(population_id: str):
            # Simulate efficiency metrics
            return {
                "population_id": population_id,
                "average_efficiency": random.uniform(0.6, 1.2),
                "best_efficiency": random.uniform(1.0, 2.0),
                "worst_efficiency": random.uniform(0.1, 0.5)
            }
            
        @self.app.post("/api/v1/evolution/inject-mutations")
        async def inject_mutations(request: Dict[str, Any]):
            return {
                "success": True,
                "mutated_agents": random.randint(2, 5),
                "new_variance": random.uniform(0.4, 0.6)
            }
            
        @self.app.get("/api/v1/patterns/discovered")
        async def get_discovered_patterns(since: Optional[str] = None, min_effectiveness: float = 0.5):
            # Generate mock patterns
            patterns = []
            for i in range(random.randint(0, 5)):
                patterns.append({
                    "id": str(uuid.uuid4()),
                    "type": random.choice(["optimization", "refactoring", "algorithm"]),
                    "effectiveness": random.uniform(min_effectiveness, 1.0),
                    "discovered_at": datetime.utcnow().isoformat()
                })
            
            self.patterns.extend(patterns)
            return patterns
            
        @self.app.post("/api/v1/patterns/store")
        async def store_patterns(request: Dict[str, Any]):
            return {
                "success": True,
                "stored_count": len(request.get("patterns", []))
            }
            
        @self.app.post("/api/v1/token/allocations/update")
        async def update_allocations(request: Dict[str, Any]):
            return {
                "success": True,
                "updated_agents": len(self.agents)
            }
            
        @self.app.delete("/api/v1/agents/population/cleanup")
        async def cleanup_population(request: Dict[str, Any]):
            pop_id = request.get("population_id")
            if pop_id in self.populations:
                # Clean up agents
                for agent_id in self.populations[pop_id]["agent_ids"]:
                    self.agents.pop(agent_id, None)
                self.populations.pop(pop_id)
                
            return {"success": True}


class MockEvolutionAPIService:
    """Mock Evolution API service for testing."""
    
    def __init__(self):
        self.app = FastAPI()
        self.evolution_jobs = {}
        self.setup_routes()
        
    def setup_routes(self):
        """Set up mock API routes."""
        
        @self.app.get("/health")
        async def health():
            return {"status": "healthy", "version": "1.0.0-mock"}
            
        @self.app.post("/api/v1/evolution/start")
        async def start_evolution(request: Dict[str, Any]):
            job_id = str(uuid.uuid4())
            
            self.evolution_jobs[job_id] = {
                "id": job_id,
                "status": "running",
                "population_ids": request.get("population_ids", []),
                "generations": request.get("generations", 50),
                "current_generation": 0,
                "started_at": datetime.utcnow().isoformat()
            }
            
            # Simulate evolution progress in background
            asyncio.create_task(self._simulate_evolution(job_id))
            
            return {
                "job_id": job_id,
                "status": "started"
            }
            
        @self.app.get("/api/v1/evolution/status")
        async def get_evolution_status():
            active_jobs = [j for j in self.evolution_jobs.values() if j["status"] == "running"]
            
            return {
                "active_trials": len(active_jobs),
                "total_agents": sum(len(j["population_ids"]) for j in active_jobs),
                "generation": max((j["current_generation"] for j in active_jobs), default=0),
                "fitness_average": random.uniform(0.5, 0.9),
                "diversity_score": random.uniform(0.3, 0.6),
                "service_status": "available"
            }
            
    async def _simulate_evolution(self, job_id: str):
        """Simulate evolution progress."""
        job = self.evolution_jobs[job_id]
        
        for gen in range(job["generations"]):
            if job["status"] != "running":
                break
                
            await asyncio.sleep(0.5)  # Simulate processing time
            job["current_generation"] = gen + 1
            
        job["status"] = "completed"
        job["completed_at"] = datetime.utcnow().isoformat()


class MockAirflowService:
    """Mock Airflow service for testing."""
    
    def __init__(self):
        self.app = FastAPI()
        self.dag_runs = {}
        self.setup_routes()
        
    def setup_routes(self):
        """Set up mock API routes."""
        
        @self.app.get("/health")
        async def health():
            return {"status": "healthy", "version": "3.0.0-mock"}
            
        @self.app.get("/api/v1/health")
        async def api_health():
            return {
                "metadatabase": {"status": "healthy"},
                "scheduler": {"status": "healthy"}
            }
            
        @self.app.post("/api/v1/dags/{dag_id}/dagRuns")
        async def trigger_dag(dag_id: str, request: Dict[str, Any]):
            run_id = f"{dag_id}__{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            
            self.dag_runs[run_id] = {
                "dag_run_id": run_id,
                "dag_id": dag_id,
                "state": "running",
                "conf": request.get("conf", {}),
                "start_date": datetime.utcnow().isoformat()
            }
            
            # Simulate DAG completion in background
            asyncio.create_task(self._simulate_dag_run(run_id))
            
            return {
                "dag_run_id": run_id,
                "dag_id": dag_id,
                "state": "running"
            }
            
    async def _simulate_dag_run(self, run_id: str):
        """Simulate DAG execution."""
        await asyncio.sleep(2.0)  # Simulate execution time
        
        if run_id in self.dag_runs:
            self.dag_runs[run_id]["state"] = "success"
            self.dag_runs[run_id]["end_date"] = datetime.utcnow().isoformat()


class MockDEANServices:
    """Container for all mock DEAN services."""
    
    def __init__(self):
        self.indexagent = MockIndexAgentService()
        self.evolution_api = MockEvolutionAPIService()
        self.airflow = MockAirflowService()
        
    async def start_all(self, 
                       indexagent_port: int = 8081,
                       evolution_port: int = 8090,
                       airflow_port: int = 8080):
        """Start all mock services on specified ports."""
        import uvicorn
        from multiprocessing import Process
        
        # Create server processes
        self.processes = []
        
        # IndexAgent
        def run_indexagent():
            uvicorn.run(self.indexagent.app, host="0.0.0.0", port=indexagent_port)
            
        p1 = Process(target=run_indexagent)
        p1.start()
        self.processes.append(p1)
        
        # Evolution API
        def run_evolution():
            uvicorn.run(self.evolution_api.app, host="0.0.0.0", port=evolution_port)
            
        p2 = Process(target=run_evolution)
        p2.start()
        self.processes.append(p2)
        
        # Airflow
        def run_airflow():
            uvicorn.run(self.airflow.app, host="0.0.0.0", port=airflow_port)
            
        p3 = Process(target=run_airflow)
        p3.start()
        self.processes.append(p3)
        
        # Wait for services to start
        await asyncio.sleep(2.0)
        
    def stop_all(self):
        """Stop all mock services."""
        for process in self.processes:
            process.terminate()
            process.join()


# Convenience function for testing
async def create_mock_services():
    """Create and return mock services for testing."""
    services = MockDEANServices()
    return services