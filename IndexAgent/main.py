"""IndexAgent Service - Main Entry Point."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import os
import logging
from datetime import datetime
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="IndexAgent Service",
    description="Agent management and code analysis service for DEAN",
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
class AgentConfig(BaseModel):
    goal: str
    token_budget: int = 4096
    diversity_weight: float = 0.3

class Agent(BaseModel):
    id: str
    goal: str
    token_budget: int
    diversity_weight: float
    status: str = "active"
    created_at: datetime
    fitness_score: float = 0.0
    tokens_consumed: int = 0

class PopulationRequest(BaseModel):
    size: int
    diversity_threshold: float = 0.3

# In-memory storage (replace with database in production)
agents: Dict[str, Agent] = {}

# API Endpoints

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "IndexAgent",
        "version": "1.0.0",
        "status": "operational"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "IndexAgent",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/api/v1/agents", response_model=Agent)
async def create_agent(config: AgentConfig):
    """Create a new agent."""
    agent_id = str(uuid.uuid4())
    agent = Agent(
        id=agent_id,
        goal=config.goal,
        token_budget=config.token_budget,
        diversity_weight=config.diversity_weight,
        created_at=datetime.utcnow()
    )
    agents[agent_id] = agent
    logger.info(f"Created agent {agent_id} with goal: {config.goal}")
    return agent

@app.get("/api/v1/agents", response_model=List[Agent])
async def list_agents():
    """List all agents."""
    return list(agents.values())

@app.get("/api/v1/agents/{agent_id}", response_model=Agent)
async def get_agent(agent_id: str):
    """Get agent details."""
    if agent_id not in agents:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agents[agent_id]

@app.post("/api/v1/agents/population/initialize")
async def initialize_population(request: PopulationRequest):
    """Initialize agent population."""
    agent_ids = []
    for i in range(request.size):
        config = AgentConfig(
            goal=f"Agent {i} - Optimize code efficiency",
            token_budget=4096,
            diversity_weight=request.diversity_threshold
        )
        agent = await create_agent(config)
        agent_ids.append(agent.id)
    
    return {
        "agent_ids": agent_ids,
        "population_size": request.size,
        "diversity_threshold": request.diversity_threshold
    }

@app.get("/api/v1/patterns/discovered")
async def list_patterns():
    """List discovered patterns."""
    # Mock implementation
    return {
        "patterns": [
            {
                "id": "pattern-1",
                "type": "optimization",
                "effectiveness": 0.85,
                "discovered_at": datetime.utcnow().isoformat()
            }
        ]
    }

@app.get("/metrics")
async def prometheus_metrics():
    """Prometheus metrics endpoint."""
    total_agents = len(agents)
    active_agents = sum(1 for a in agents.values() if a.status == "active")
    
    metrics = f"""# HELP indexagent_total_agents Total number of agents
# TYPE indexagent_total_agents gauge
indexagent_total_agents {total_agents}

# HELP indexagent_active_agents Number of active agents
# TYPE indexagent_active_agents gauge
indexagent_active_agents {active_agents}

# HELP indexagent_health_status Service health status
# TYPE indexagent_health_status gauge
indexagent_health_status 1
"""
    return metrics

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("INDEXAGENT_PORT", "8081"))
    uvicorn.run(app, host="0.0.0.0", port=port)