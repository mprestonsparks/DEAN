#!/usr/bin/env python3
"""
IndexAgent API Stub

Provides a minimal implementation of the IndexAgent API for development.
Stores all data in memory - not persistent across restarts.
"""

import asyncio
import os
import random
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
import structlog
import uvicorn
import jwt

# Configure logging
logger = structlog.get_logger()

# Create FastAPI app
app = FastAPI(
    title="IndexAgent Stub API",
    description="Mock IndexAgent service for DEAN development",
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

# In-memory storage
class DataStore:
    def __init__(self):
        self.agents: Dict[str, Dict] = {}
        self.populations: Dict[str, Dict] = {}
        self.patterns: List[Dict] = self._generate_sample_patterns()
        self.metrics: Dict[str, Any] = {
            "agents_created": 0,
            "patterns_extracted": len(self.patterns),
            "search_queries": 0,
            "avg_query_time_ms": 85
        }
        
    def _generate_sample_patterns(self) -> List[Dict]:
        """Generate sample patterns for testing."""
        patterns = [
            {
                "id": f"pattern-{i}",
                "type": random.choice(["optimization", "refactoring", "bug_fix", "feature"]),
                "confidence": round(random.uniform(0.7, 0.95), 2),
                "description": f"Pattern {i}: {random.choice(['Code optimization', 'Error handling', 'Performance improvement', 'API design'])}",
                "occurrences": random.randint(5, 50),
                "repositories": [f"repo-{j}" for j in range(random.randint(1, 5))],
                "created_at": datetime.utcnow().isoformat()
            }
            for i in range(10)
        ]
        return patterns

# Initialize data store
data_store = DataStore()

# Authentication configuration
JWT_SECRET = os.getenv("JWT_SECRET_KEY", "test-secret-key")  # Use same secret as main app
JWT_ALGORITHM = "HS256"

# Security scheme
security = HTTPBearer()

# Authentication dependency
def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token for protected endpoints.
    
    This is a simplified version for the stub. In production, this would:
    - Validate token signature
    - Check token expiration
    - Verify user roles
    - Handle service-to-service authentication
    """
    token = credentials.credentials
    
    try:
        # Decode and verify token
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        
        # Check required fields
        if "sub" not in payload or "username" not in payload:
            raise HTTPException(status_code=401, detail="Invalid token structure")
            
        # Check token type
        if payload.get("type") not in ["access", "service"]:
            raise HTTPException(status_code=401, detail="Invalid token type")
            
        return payload
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        logger.error("Token verification failed", error=str(e))
        raise HTTPException(status_code=401, detail="Authentication failed")

def get_current_user(token_data: dict = Depends(verify_token)):
    """Get current user from token."""
    return {
        "user_id": token_data.get("sub"),
        "username": token_data.get("username"),
        "roles": token_data.get("roles", [])
    }

# Pydantic models
class AgentConfig(BaseModel):
    name: str
    language: str = "python"
    capabilities: List[str] = Field(default_factory=lambda: ["search", "analyze", "evolve"])
    parameters: Dict[str, Any] = Field(default_factory=dict)

class Agent(BaseModel):
    id: str
    name: str
    config: AgentConfig
    fitness_score: float = 0.5
    generation: int = 0
    created_at: str
    status: str = "active"

class PopulationConfig(BaseModel):
    size: int = 10
    mutation_rate: float = 0.1
    crossover_rate: float = 0.7
    selection_method: str = "tournament"

class SearchRequest(BaseModel):
    query: str
    repositories: Optional[List[str]] = None
    limit: int = 10
    filters: Optional[Dict[str, Any]] = None

# Health endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "indexagent-stub",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime_seconds": int(time.time() - app.state.start_time)
    }

# Agent CRUD endpoints
@app.get("/agents")
async def list_agents(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    user: dict = Depends(get_current_user)
):
    """List all agents."""
    agents = list(data_store.agents.values())
    return {
        "agents": agents[offset:offset + limit],
        "total": len(agents),
        "limit": limit,
        "offset": offset
    }

@app.post("/agents")
async def create_agent(config: AgentConfig, user: dict = Depends(get_current_user)):
    """Create a new agent."""
    # Simulate processing delay
    await asyncio.sleep(random.uniform(0.1, 0.3))
    
    agent_id = f"agent-{uuid4().hex[:8]}"
    agent = Agent(
        id=agent_id,
        name=config.name,
        config=config,
        fitness_score=round(random.uniform(0.3, 0.7), 3),
        generation=0,
        created_at=datetime.utcnow().isoformat()
    )
    
    data_store.agents[agent_id] = agent.dict()
    data_store.metrics["agents_created"] += 1
    
    logger.info("Agent created", agent_id=agent_id, name=config.name, user=user["username"])
    return agent

@app.get("/agents/{agent_id}")
async def get_agent(agent_id: str, user: dict = Depends(get_current_user)):
    """Get a specific agent."""
    if agent_id not in data_store.agents:
        raise HTTPException(status_code=404, detail="Agent not found")
    return data_store.agents[agent_id]

@app.delete("/agents/{agent_id}")
async def delete_agent(agent_id: str, user: dict = Depends(get_current_user)):
    """Delete an agent."""
    if agent_id not in data_store.agents:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    del data_store.agents[agent_id]
    logger.info("Agent deleted", agent_id=agent_id, user=user["username"])
    return {"status": "deleted", "agent_id": agent_id}

# Evolution endpoints
@app.post("/evolution/population")
async def create_population(config: PopulationConfig, user: dict = Depends(get_current_user)):
    """Initialize a population of agents."""
    # Simulate population creation
    await asyncio.sleep(random.uniform(0.5, 1.0))
    
    population_id = f"pop-{uuid4().hex[:8]}"
    agents = []
    
    for i in range(config.size):
        agent_config = AgentConfig(
            name=f"agent-gen0-{i}",
            language="python",
            capabilities=["search", "analyze", "evolve"],
            parameters={
                "mutation_rate": config.mutation_rate,
                "gene_expression": random.random()
            }
        )
        
        # Create agent without user context for internal call
        agent_dict = Agent(
            id=f"agent-{uuid4().hex[:8]}",
            name=agent_config.name,
            config=agent_config,
            fitness_score=round(random.uniform(0.3, 0.7), 3),
            generation=0,
            created_at=datetime.utcnow().isoformat()
        ).dict()
        data_store.agents[agent_dict["id"]] = agent_dict
        agent = Agent(**agent_dict)
        agents.append(agent.dict())
    
    population = {
        "population_id": population_id,
        "config": config.dict(),
        "agents": agents,
        "generation": 0,
        "best_fitness": max(a["fitness_score"] for a in agents),
        "avg_fitness": sum(a["fitness_score"] for a in agents) / len(agents),
        "created_at": datetime.utcnow().isoformat()
    }
    
    data_store.populations[population_id] = population
    logger.info("Population created", population_id=population_id, size=config.size, user=user["username"])
    
    return population

@app.post("/evolution/generation")
async def evolve_generation(population_id: str, user: dict = Depends(get_current_user)):
    """Evolve a population to the next generation."""
    if population_id not in data_store.populations:
        raise HTTPException(status_code=404, detail="Population not found")
    
    # Simulate evolution processing
    await asyncio.sleep(random.uniform(1.0, 2.0))
    
    population = data_store.populations[population_id]
    current_gen = population["generation"]
    agents = population["agents"]
    
    # Simulate evolution - improve fitness scores
    new_agents = []
    for agent in agents:
        # Create evolved version
        new_fitness = min(0.99, agent["fitness_score"] + random.uniform(0.05, 0.15))
        evolved_agent = dict(agent)
        evolved_agent.update({
            "id": f"agent-{uuid4().hex[:8]}",
            "name": f"agent-gen{current_gen + 1}-{len(new_agents)}",
            "fitness_score": round(new_fitness, 3),
            "generation": current_gen + 1
        })
        new_agents.append(evolved_agent)
        data_store.agents[evolved_agent["id"]] = evolved_agent
    
    # Update population
    population.update({
        "agents": new_agents,
        "generation": current_gen + 1,
        "best_fitness": max(a["fitness_score"] for a in new_agents),
        "avg_fitness": sum(a["fitness_score"] for a in new_agents) / len(new_agents)
    })
    
    # Occasionally discover new patterns
    if random.random() > 0.7:
        new_pattern = {
            "id": f"pattern-{len(data_store.patterns)}",
            "type": "evolution_discovered",
            "confidence": round(random.uniform(0.8, 0.95), 2),
            "description": f"Evolution pattern discovered in generation {current_gen + 1}",
            "occurrences": 1,
            "repositories": [population_id],
            "created_at": datetime.utcnow().isoformat()
        }
        data_store.patterns.append(new_pattern)
        data_store.metrics["patterns_extracted"] += 1
    
    logger.info("Generation evolved", 
                population_id=population_id, 
                generation=current_gen + 1,
                best_fitness=population["best_fitness"],
                user=user["username"])
    
    return {
        "generation": current_gen + 1,
        "best_agent": max(new_agents, key=lambda a: a["fitness_score"]),
        "population": new_agents,
        "stats": {
            "best_fitness": population["best_fitness"],
            "avg_fitness": population["avg_fitness"],
            "improvement": round(population["best_fitness"] - 
                                max(a["fitness_score"] for a in agents), 3)
        }
    }

@app.get("/evolution/metrics")
async def get_evolution_metrics(user: dict = Depends(get_current_user)):
    """Get evolution metrics."""
    return {
        "total_agents": len(data_store.agents),
        "active_populations": len(data_store.populations),
        "patterns_discovered": len([p for p in data_store.patterns 
                                   if p["type"] == "evolution_discovered"]),
        "average_fitness": round(sum(a["fitness_score"] for a in data_store.agents.values()) / 
                                max(1, len(data_store.agents)), 3),
        "metrics": data_store.metrics
    }

# Search endpoints
@app.post("/search")
async def search(request: SearchRequest, user: dict = Depends(get_current_user)):
    """Search for code patterns."""
    # Simulate search delay
    await asyncio.sleep(random.uniform(0.05, 0.15))
    
    data_store.metrics["search_queries"] += 1
    
    # Mock search results
    results = []
    for i in range(min(request.limit, 5)):
        results.append({
            "id": f"result-{uuid4().hex[:8]}",
            "score": round(random.uniform(0.7, 0.99), 3),
            "repository": random.choice(request.repositories) if request.repositories 
                          else f"repo-{random.randint(1, 10)}",
            "file_path": f"src/{random.choice(['utils', 'core', 'api'])}/file_{i}.py",
            "line_number": random.randint(10, 200),
            "snippet": f"def {request.query}_function():\n    # Implementation here\n    pass",
            "context": "Mock search result for development"
        })
    
    logger.info("Search executed", query=request.query, results=len(results), user=user["username"])
    
    return {
        "query": request.query,
        "results": results,
        "total_results": len(results),
        "execution_time_ms": random.randint(50, 150)
    }

# Pattern endpoints  
@app.get("/patterns")
async def get_patterns(
    pattern_type: Optional[str] = None,
    min_confidence: float = Query(0.0, ge=0.0, le=1.0),
    limit: int = Query(100, ge=1, le=1000),
    user: dict = Depends(get_current_user)
):
    """Get discovered patterns."""
    patterns = data_store.patterns
    
    # Filter by type if specified
    if pattern_type:
        patterns = [p for p in patterns if p["type"] == pattern_type]
    
    # Filter by confidence
    patterns = [p for p in patterns if p["confidence"] >= min_confidence]
    
    # Sort by confidence descending
    patterns.sort(key=lambda p: p["confidence"], reverse=True)
    
    return {
        "patterns": patterns[:limit],
        "total": len(patterns),
        "filters": {
            "pattern_type": pattern_type,
            "min_confidence": min_confidence
        }
    }

@app.get("/metrics")
async def get_metrics(user: dict = Depends(get_current_user)):
    """Get service metrics."""
    return data_store.metrics

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize the service."""
    app.state.start_time = time.time()
    logger.info("IndexAgent stub started", port=8081)
    
    # Create some initial data (bypass auth for startup)
    initial_agents = [
        AgentConfig(name="search-agent-1", language="python"),
        AgentConfig(name="analyze-agent-1", language="python"),
        AgentConfig(name="evolution-agent-1", language="python")
    ]
    
    for config in initial_agents:
        agent_id = f"agent-{uuid4().hex[:8]}"
        agent = Agent(
            id=agent_id,
            name=config.name,
            config=config,
            fitness_score=round(random.uniform(0.3, 0.7), 3),
            generation=0,
            created_at=datetime.utcnow().isoformat()
        )
        data_store.agents[agent_id] = agent.dict()
        data_store.metrics["agents_created"] += 1

if __name__ == "__main__":
    port = int(os.getenv("SERVICE_PORT", "8081"))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_config={
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                },
            },
            "handlers": {
                "default": {
                    "formatter": "default",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                },
            },
            "root": {
                "level": os.getenv("LOG_LEVEL", "INFO"),
                "handlers": ["default"],
            },
        }
    )