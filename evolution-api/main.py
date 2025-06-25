"""Evolution API Service - Main Entry Point."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import os
import logging
from datetime import datetime
import uuid
import random

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Evolution API Service",
    description="Genetic algorithm and evolution management for DEAN",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class EvolutionRequest(BaseModel):
    population_ids: List[str]
    generations: int = 50
    token_budget: int = 100000

class EvolutionJob(BaseModel):
    id: str
    status: str = "running"
    current_generation: int = 0
    total_generations: int
    population_ids: List[str]
    token_budget: int
    tokens_consumed: int = 0
    best_fitness: float = 0.0
    diversity_score: float = 1.0
    created_at: datetime
    updated_at: datetime

# In-memory storage
evolution_jobs: Dict[str, EvolutionJob] = {}

# API Endpoints

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Evolution API",
        "version": "1.0.0",
        "status": "operational"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Evolution API",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/api/v1/evolution/start")
async def start_evolution(request: EvolutionRequest):
    """Start evolution process."""
    job_id = str(uuid.uuid4())
    job = EvolutionJob(
        id=job_id,
        total_generations=request.generations,
        population_ids=request.population_ids,
        token_budget=request.token_budget,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    evolution_jobs[job_id] = job
    logger.info(f"Started evolution job {job_id} with {len(request.population_ids)} agents")
    
    # Simulate some initial progress
    job.current_generation = 1
    job.tokens_consumed = random.randint(100, 1000)
    job.best_fitness = random.uniform(0.1, 0.3)
    job.diversity_score = random.uniform(0.7, 1.0)
    
    return {"job_id": job_id, "status": "started"}

@app.get("/api/v1/evolution/status")
async def get_evolution_status():
    """Get overall evolution status."""
    active_jobs = [j for j in evolution_jobs.values() if j.status == "running"]
    
    return {
        "active_trials": len(active_jobs),
        "total_agents": sum(len(j.population_ids) for j in active_jobs),
        "generation": max((j.current_generation for j in active_jobs), default=0),
        "fitness_average": sum(j.best_fitness for j in active_jobs) / len(active_jobs) if active_jobs else 0.0,
        "diversity_score": sum(j.diversity_score for j in active_jobs) / len(active_jobs) if active_jobs else 0.0,
        "service_status": "available"
    }

@app.get("/api/v1/evolution/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Get specific evolution job status."""
    if job_id not in evolution_jobs:
        raise HTTPException(status_code=404, detail="Evolution job not found")
    
    job = evolution_jobs[job_id]
    
    # Simulate progress
    if job.status == "running" and job.current_generation < job.total_generations:
        job.current_generation += 1
        job.tokens_consumed += random.randint(500, 2000)
        job.best_fitness = min(0.95, job.best_fitness + random.uniform(0.01, 0.05))
        job.diversity_score = max(0.3, job.diversity_score - random.uniform(0.01, 0.03))
        job.updated_at = datetime.utcnow()
        
        if job.current_generation >= job.total_generations:
            job.status = "completed"
    
    return job

@app.get("/api/v1/metrics")
async def get_metrics():
    """Get evolution metrics."""
    return {
        "total_jobs": len(evolution_jobs),
        "active_jobs": sum(1 for j in evolution_jobs.values() if j.status == "running"),
        "completed_jobs": sum(1 for j in evolution_jobs.values() if j.status == "completed"),
        "total_tokens_consumed": sum(j.tokens_consumed for j in evolution_jobs.values()),
        "average_fitness": sum(j.best_fitness for j in evolution_jobs.values()) / len(evolution_jobs) if evolution_jobs else 0.0
    }

@app.get("/metrics")
async def prometheus_metrics():
    """Prometheus metrics endpoint."""
    active_jobs = sum(1 for j in evolution_jobs.values() if j.status == "running")
    total_tokens = sum(j.tokens_consumed for j in evolution_jobs.values())
    
    metrics = f"""# HELP evolution_active_jobs Number of active evolution jobs
# TYPE evolution_active_jobs gauge
evolution_active_jobs {active_jobs}

# HELP evolution_total_tokens_consumed Total tokens consumed
# TYPE evolution_total_tokens_consumed counter
evolution_total_tokens_consumed {total_tokens}

# HELP evolution_health_status Service health status
# TYPE evolution_health_status gauge
evolution_health_status 1
"""
    return metrics

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("EVOLUTION_PORT", "8090"))
    uvicorn.run(app, host="0.0.0.0", port=port)