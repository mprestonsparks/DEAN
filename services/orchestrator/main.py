#!/usr/bin/env python3
"""
DEAN Orchestrator Service - Complete Implementation
Coordinates all DEAN system components with full functionality
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Set
from contextlib import asynccontextmanager

import aioredis
import httpx
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Service URLs
INDEXAGENT_URL = "http://localhost:8081"
EVOLUTION_API_URL = "http://localhost:8091"
AIRFLOW_URL = "http://localhost:8080"

# Global connections
redis_client: Optional[aioredis.Redis] = None
http_client: Optional[httpx.AsyncClient] = None
active_websockets: Set[WebSocket] = set()

# Request/Response Models
class AgentSpawnRequest(BaseModel):
    """Request to spawn new agents"""
    population_size: int = Field(ge=1, le=50)
    genome_template: str = "default"
    token_budget: int = Field(ge=100, le=50000)
    goals: List[str] = Field(default_factory=list)
    diversity_target: float = Field(default=0.35, ge=0.1, le=1.0)

class AgentSpawnResponse(BaseModel):
    """Response from agent spawn operation"""
    agent_ids: List[str]
    initial_diversity: float
    tokens_allocated: int
    spawn_timestamp: datetime

class EvolutionOrchestrationRequest(BaseModel):
    """Request to orchestrate evolution across agents"""
    population_ids: List[str]
    generations: int = Field(ge=1, le=100)
    token_budget: int = Field(ge=1000, le=100000)
    ca_rules: List[int] = Field(default=[110, 30, 90, 184])
    diversity_threshold: float = Field(default=0.3)
    pattern_sharing: bool = True

class PopulationStatus(BaseModel):
    """Aggregated population status"""
    total_agents: int
    active_agents: int
    total_patterns: int
    average_fitness: float
    population_diversity: float
    token_usage: Dict[str, int]
    top_performers: List[Dict]
    discovered_patterns: List[Dict]

class PatternPropagationRequest(BaseModel):
    """Request to propagate patterns across agents"""
    pattern_ids: List[str]
    target_agent_ids: Optional[List[str]] = None
    propagation_strategy: str = Field(default="fitness_weighted")
    max_recipients: int = Field(default=10)

# Circuit Breaker Implementation
class CircuitBreaker:
    """Circuit breaker for service resilience"""
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
    
    async def call(self, func, *args, **kwargs):
        if self.state == "open":
            if (datetime.now() - self.last_failure_time).seconds > self.recovery_timeout:
                self.state = "half-open"
            else:
                raise HTTPException(status_code=503, detail="Service circuit breaker is open")
        
        try:
            result = await func(*args, **kwargs)
            if self.state == "half-open":
                self.state = "closed"
                self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = datetime.now()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "open"
                logger.error(f"Circuit breaker opened after {self.failure_count} failures")
            
            raise e

# Service circuit breakers
indexagent_breaker = CircuitBreaker()
evolution_breaker = CircuitBreaker()
airflow_breaker = CircuitBreaker()

# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    global redis_client, http_client
    
    # Startup
    logger.info("Starting DEAN Orchestrator...")
    
    # Initialize Redis
    redis_client = await aioredis.create_redis_pool('redis://localhost:6379')
    
    # Initialize HTTP client
    http_client = httpx.AsyncClient(timeout=30.0)
    
    # Start event listeners
    asyncio.create_task(evolution_event_listener())
    asyncio.create_task(pattern_event_listener())
    
    yield
    
    # Shutdown
    logger.info("Shutting down DEAN Orchestrator...")
    
    if redis_client:
        redis_client.close()
        await redis_client.wait_closed()
    
    if http_client:
        await http_client.aclose()

# Create FastAPI app
app = FastAPI(
    title="DEAN Orchestrator",
    description="Central orchestration service for DEAN system",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check with dependency status"""
    dependencies = {}
    
    # Check IndexAgent
    try:
        response = await http_client.get(f"{INDEXAGENT_URL}/health")
        dependencies["indexagent"] = "healthy" if response.status_code == 200 else "unhealthy"
    except:
        dependencies["indexagent"] = "unreachable"
    
    # Check Evolution API
    try:
        response = await http_client.get(f"{EVOLUTION_API_URL}/health")
        dependencies["evolution_api"] = "healthy" if response.status_code == 200 else "unhealthy"
    except:
        dependencies["evolution_api"] = "unreachable"
    
    # Check Redis
    try:
        await redis_client.ping()
        dependencies["redis"] = "healthy"
    except:
        dependencies["redis"] = "unhealthy"
    
    overall_health = "healthy" if all(v == "healthy" for v in dependencies.values()) else "degraded"
    
    return {
        "status": overall_health,
        "service": "DEAN Orchestrator",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "dependencies": dependencies
    }

# Agent Spawn Endpoint
@app.post("/api/v1/agents/spawn", response_model=AgentSpawnResponse)
async def spawn_agents(request: AgentSpawnRequest):
    """Spawn new agents with orchestrated initialization"""
    try:
        # Step 1: Check token budget availability
        budget_response = await evolution_breaker.call(
            http_client.get,
            f"{EVOLUTION_API_URL}/api/v1/economy/budget"
        )
        budget_data = budget_response.json()
        
        total_requested = request.population_size * request.token_budget
        if total_requested > budget_data["available"]:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient token budget. Requested: {total_requested}, Available: {budget_data['available']}"
            )
        
        # Step 2: Create agents via IndexAgent
        agent_ids = []
        goals = request.goals or [f"Optimize code pattern {i}" for i in range(request.population_size)]
        
        for i in range(request.population_size):
            goal = goals[i % len(goals)]
            
            agent_data = {
                "goal": goal,
                "token_budget": request.token_budget,
                "diversity_weight": request.diversity_target,
                "specialized_domain": "code_optimization",
                "agent_metadata": {
                    "spawn_batch": str(uuid.uuid4()),
                    "genome_template": request.genome_template,
                    "orchestrated": True
                }
            }
            
            response = await indexagent_breaker.call(
                http_client.post,
                f"{INDEXAGENT_URL}/api/v1/agents",
                json=agent_data
            )
            
            if response.status_code == 200:
                agent_info = response.json()
                agent_ids.append(agent_info["id"])
                
                # Publish agent creation event
                await redis_client.publish(
                    "dean:events:agent_created",
                    json.dumps({
                        "agent_id": agent_info["id"],
                        "goal": goal,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                )
            else:
                logger.error(f"Failed to create agent: {response.text}")
        
        # Step 3: Calculate initial diversity
        if len(agent_ids) > 1:
            diversity_response = await indexagent_breaker.call(
                http_client.post,
                f"{INDEXAGENT_URL}/api/v1/diversity/population",
                json={"population_ids": agent_ids}
            )
            initial_diversity = diversity_response.json().get("diversity_score", 0.0)
        else:
            initial_diversity = 1.0
        
        # Step 4: Allocate tokens via Evolution API
        for agent_id in agent_ids:
            allocation_data = {
                "agent_id": agent_id,
                "requested_tokens": request.token_budget,
                "priority": "normal"
            }
            
            await evolution_breaker.call(
                http_client.post,
                f"{EVOLUTION_API_URL}/api/v1/economy/allocate",
                json=allocation_data
            )
        
        # Step 5: Broadcast spawn completion
        await broadcast_websocket_message({
            "event": "agents_spawned",
            "data": {
                "agent_ids": agent_ids,
                "count": len(agent_ids),
                "diversity": initial_diversity,
                "timestamp": datetime.utcnow().isoformat()
            }
        })
        
        return AgentSpawnResponse(
            agent_ids=agent_ids,
            initial_diversity=initial_diversity,
            tokens_allocated=total_requested,
            spawn_timestamp=datetime.utcnow()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error spawning agents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Evolution Orchestration Endpoint
@app.post("/api/v1/evolution/orchestrate")
async def orchestrate_evolution(request: EvolutionOrchestrationRequest):
    """Orchestrate evolution across multiple agents"""
    try:
        # Step 1: Validate population exists
        agent_states = []
        for agent_id in request.population_ids:
            response = await indexagent_breaker.call(
                http_client.get,
                f"{INDEXAGENT_URL}/api/v1/agents/{agent_id}"
            )
            if response.status_code == 200:
                agent_states.append(response.json())
            else:
                raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
        
        # Step 2: Check diversity and inject mutations if needed
        diversity_response = await indexagent_breaker.call(
            http_client.post,
            f"{INDEXAGENT_URL}/api/v1/diversity/population",
            json={"population_ids": request.population_ids}
        )
        current_diversity = diversity_response.json()["diversity_score"]
        
        if current_diversity < request.diversity_threshold:
            logger.warning(f"Low diversity detected: {current_diversity}")
            # Trigger diversity injection
            await redis_client.publish(
                "dean:events:diversity_alert",
                json.dumps({
                    "population_ids": request.population_ids,
                    "current_diversity": current_diversity,
                    "threshold": request.diversity_threshold
                })
            )
        
        # Step 3: Start evolution via Evolution API
        evolution_data = {
            "population_ids": request.population_ids,
            "generations": request.generations,
            "ca_rules": request.ca_rules,
            "token_budget": request.token_budget
        }
        
        evolution_response = await evolution_breaker.call(
            http_client.post,
            f"{EVOLUTION_API_URL}/api/v1/evolution/start",
            json=evolution_data
        )
        evolution_cycle = evolution_response.json()
        
        # Step 4: Trigger evolution for each agent
        evolution_tasks = []
        for agent_id in request.population_ids:
            evolution_params = {
                "generations": request.generations,
                "mutation_rate": 0.1 if current_diversity > 0.4 else 0.2,
                "crossover_rate": 0.25,
                "ca_rules": request.ca_rules,
                "elitism_rate": 0.1,
                "tournament_size": 3
            }
            
            task = indexagent_breaker.call(
                http_client.post,
                f"{INDEXAGENT_URL}/api/v1/agents/{agent_id}/evolve",
                json=evolution_params
            )
            evolution_tasks.append(task)
        
        # Execute evolutions concurrently
        evolution_results = await asyncio.gather(*evolution_tasks, return_exceptions=True)
        
        # Step 5: Harvest patterns if sharing enabled
        if request.pattern_sharing:
            pattern_response = await indexagent_breaker.call(
                http_client.get,
                f"{INDEXAGENT_URL}/api/v1/patterns/discovered"
            )
            patterns = pattern_response.json()["patterns"]
            
            if patterns:
                # Propagate high-value patterns
                await propagate_patterns_internal(
                    pattern_ids=[p["id"] for p in patterns[:5]],
                    target_agent_ids=request.population_ids
                )
        
        # Step 6: Create Airflow DAG run for monitoring
        if AIRFLOW_URL:
            try:
                dag_trigger = {
                    "dag_run_id": f"evolution_{evolution_cycle['cycle_id']}",
                    "conf": {
                        "cycle_id": evolution_cycle["cycle_id"],
                        "population_ids": request.population_ids,
                        "generations": request.generations
                    }
                }
                await airflow_breaker.call(
                    http_client.post,
                    f"{AIRFLOW_URL}/api/v1/dags/dean_evolution_monitor/dagRuns",
                    json=dag_trigger,
                    auth=("admin", "admin")
                )
            except Exception as e:
                logger.warning(f"Failed to trigger Airflow DAG: {e}")
        
        # Step 7: Broadcast evolution start
        await broadcast_websocket_message({
            "event": "evolution_started",
            "data": {
                "cycle_id": evolution_cycle["cycle_id"],
                "population_size": len(request.population_ids),
                "generations": request.generations,
                "timestamp": datetime.utcnow().isoformat()
            }
        })
        
        return {
            "cycle_id": evolution_cycle["cycle_id"],
            "status": "orchestrating",
            "population_size": len(request.population_ids),
            "initial_diversity": current_diversity,
            "evolution_tasks": len(evolution_results),
            "successful_starts": sum(1 for r in evolution_results if not isinstance(r, Exception))
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error orchestrating evolution: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Population Status Endpoint
@app.get("/api/v1/population/status", response_model=PopulationStatus)
async def get_population_status():
    """Get aggregated status of entire population"""
    try:
        # Get all agents from IndexAgent
        agents_response = await indexagent_breaker.call(
            http_client.get,
            f"{INDEXAGENT_URL}/api/v1/agents"
        )
        agents = agents_response.json().get("agents", [])
        
        # Get token economy status
        budget_response = await evolution_breaker.call(
            http_client.get,
            f"{EVOLUTION_API_URL}/api/v1/economy/budget"
        )
        budget_data = budget_response.json()
        
        # Get patterns
        patterns_response = await indexagent_breaker.call(
            http_client.get,
            f"{INDEXAGENT_URL}/api/v1/patterns/discovered"
        )
        patterns = patterns_response.json()
        
        # Get efficiency metrics
        metrics_response = await indexagent_breaker.call(
            http_client.get,
            f"{INDEXAGENT_URL}/api/v1/metrics/efficiency"
        )
        metrics = metrics_response.json()
        
        # Calculate population diversity if multiple agents
        population_diversity = 0.0
        if len(agents) > 1:
            agent_ids = [a["id"] for a in agents if a["status"] == "active"]
            if agent_ids:
                diversity_response = await indexagent_breaker.call(
                    http_client.post,
                    f"{INDEXAGENT_URL}/api/v1/diversity/population",
                    json={"population_ids": agent_ids[:50]}  # Limit to 50 for performance
                )
                population_diversity = diversity_response.json()["diversity_score"]
        
        # Get top performers
        active_agents = [a for a in agents if a["status"] == "active"]
        top_performers = sorted(
            active_agents,
            key=lambda a: a.get("fitness_score", 0),
            reverse=True
        )[:5]
        
        # Format top performers
        top_performers_data = [
            {
                "id": agent["id"],
                "name": agent["name"],
                "fitness_score": agent.get("fitness_score", 0),
                "patterns_discovered": len(agent.get("emergent_patterns", [])),
                "token_efficiency": agent.get("token_budget", {}).get("efficiency_score", 0)
            }
            for agent in top_performers
        ]
        
        return PopulationStatus(
            total_agents=len(agents),
            active_agents=len(active_agents),
            total_patterns=patterns["total"],
            average_fitness=metrics["metrics"]["agent_performance"]["average_fitness"],
            population_diversity=population_diversity,
            token_usage={
                "allocated": budget_data["allocated"],
                "consumed": budget_data["consumed"],
                "available": budget_data["available"],
                "efficiency": budget_data["efficiency_score"]
            },
            top_performers=top_performers_data,
            discovered_patterns=patterns["patterns"][:10]  # Latest 10 patterns
        )
        
    except Exception as e:
        logger.error(f"Error getting population status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Pattern Propagation Endpoint
@app.post("/api/v1/patterns/propagate")
async def propagate_patterns(request: PatternPropagationRequest):
    """Propagate discovered patterns to agents"""
    try:
        result = await propagate_patterns_internal(
            pattern_ids=request.pattern_ids,
            target_agent_ids=request.target_agent_ids,
            strategy=request.propagation_strategy,
            max_recipients=request.max_recipients
        )
        return result
    except Exception as e:
        logger.error(f"Error propagating patterns: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Internal pattern propagation logic
async def propagate_patterns_internal(
    pattern_ids: List[str],
    target_agent_ids: Optional[List[str]] = None,
    strategy: str = "fitness_weighted",
    max_recipients: int = 10
):
    """Internal logic for pattern propagation"""
    # Get pattern details
    patterns_response = await indexagent_breaker.call(
        http_client.get,
        f"{INDEXAGENT_URL}/api/v1/patterns/discovered"
    )
    all_patterns = patterns_response.json()["patterns"]
    
    # Filter requested patterns
    patterns_to_propagate = [
        p for p in all_patterns 
        if p.get("id") in pattern_ids or str(p.get("pattern_id")) in pattern_ids
    ]
    
    if not patterns_to_propagate:
        raise HTTPException(status_code=404, detail="No valid patterns found")
    
    # Determine target agents
    if not target_agent_ids:
        # Get all active agents
        agents_response = await indexagent_breaker.call(
            http_client.get,
            f"{INDEXAGENT_URL}/api/v1/agents"
        )
        all_agents = agents_response.json()["agents"]
        active_agents = [a for a in all_agents if a["status"] == "active"]
        
        # Select targets based on strategy
        if strategy == "fitness_weighted":
            # Prefer lower fitness agents (they need help)
            targets = sorted(active_agents, key=lambda a: a.get("fitness_score", 0))[:max_recipients]
        elif strategy == "random":
            import random
            targets = random.sample(active_agents, min(max_recipients, len(active_agents)))
        else:
            targets = active_agents[:max_recipients]
        
        target_agent_ids = [t["id"] for t in targets]
    
    # Propagate patterns via Redis events
    propagation_count = 0
    for pattern in patterns_to_propagate:
        for agent_id in target_agent_ids:
            await redis_client.publish(
                f"dean:agent:{agent_id}:pattern",
                json.dumps({
                    "pattern": pattern,
                    "source": "orchestrator",
                    "timestamp": datetime.utcnow().isoformat()
                })
            )
            propagation_count += 1
    
    # Broadcast propagation event
    await broadcast_websocket_message({
        "event": "patterns_propagated",
        "data": {
            "pattern_count": len(patterns_to_propagate),
            "recipient_count": len(target_agent_ids),
            "total_propagations": propagation_count,
            "timestamp": datetime.utcnow().isoformat()
        }
    })
    
    return {
        "patterns_propagated": len(patterns_to_propagate),
        "recipients": len(target_agent_ids),
        "total_propagations": propagation_count,
        "strategy": strategy
    }

# WebSocket endpoint for real-time monitoring
@app.websocket("/ws/evolution/monitor")
async def websocket_evolution_monitor(websocket: WebSocket):
    """WebSocket for real-time evolution monitoring"""
    await websocket.accept()
    active_websockets.add(websocket)
    
    try:
        # Send initial connection message
        await websocket.send_json({
            "event": "connected",
            "data": {
                "message": "Connected to DEAN evolution monitor",
                "timestamp": datetime.utcnow().isoformat()
            }
        })
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                data = await websocket.receive_json()
                
                # Handle subscription requests
                if data.get("action") == "subscribe":
                    agent_id = data.get("agent_id")
                    if agent_id:
                        # Subscribe to agent-specific events
                        await redis_client.sadd(f"dean:ws:{websocket}:agents", agent_id)
                        await websocket.send_json({
                            "event": "subscribed",
                            "data": {"agent_id": agent_id}
                        })
                
                # Handle status requests
                elif data.get("action") == "get_status":
                    status = await get_population_status()
                    await websocket.send_json({
                        "event": "status_update",
                        "data": status.dict()
                    })
                    
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                break
                
    finally:
        active_websockets.remove(websocket)
        # Clean up subscriptions
        await redis_client.delete(f"dean:ws:{websocket}:agents")

# Broadcast message to all WebSocket connections
async def broadcast_websocket_message(message: dict):
    """Broadcast message to all connected WebSocket clients"""
    disconnected = set()
    
    for websocket in active_websockets:
        try:
            await websocket.send_json(message)
        except:
            disconnected.add(websocket)
    
    # Remove disconnected websockets
    active_websockets.difference_update(disconnected)

# Event Listeners
async def evolution_event_listener():
    """Listen for evolution events from Redis"""
    while True:
        try:
            # Subscribe to evolution events
            pubsub = redis_client.pubsub()
            await pubsub.subscribe("dean:events:evolution:*")
            
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        event_data = json.loads(message["data"])
                        
                        # Broadcast to WebSocket clients
                        await broadcast_websocket_message({
                            "event": "evolution_update",
                            "data": event_data
                        })
                    except Exception as e:
                        logger.error(f"Error processing evolution event: {e}")
                        
        except Exception as e:
            logger.error(f"Evolution event listener error: {e}")
            await asyncio.sleep(5)  # Retry after 5 seconds

async def pattern_event_listener():
    """Listen for pattern discovery events"""
    while True:
        try:
            pubsub = redis_client.pubsub()
            await pubsub.subscribe("dean:events:pattern:*")
            
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        event_data = json.loads(message["data"])
                        
                        # Auto-propagate high-value patterns
                        if event_data.get("effectiveness", 0) > 0.8:
                            await propagate_patterns_internal(
                                pattern_ids=[event_data["pattern_id"]],
                                strategy="fitness_weighted",
                                max_recipients=5
                            )
                            
                    except Exception as e:
                        logger.error(f"Error processing pattern event: {e}")
                        
        except Exception as e:
            logger.error(f"Pattern event listener error: {e}")
            await asyncio.sleep(5)

# Service Discovery Endpoint
@app.get("/api/v1/services/status")
async def get_services_status():
    """Get status of all DEAN services"""
    services = []
    
    # Check each service
    service_configs = [
        {"name": "IndexAgent", "url": f"{INDEXAGENT_URL}/health", "breaker": indexagent_breaker},
        {"name": "Evolution API", "url": f"{EVOLUTION_API_URL}/health", "breaker": evolution_breaker},
        {"name": "Airflow", "url": f"{AIRFLOW_URL}/health", "breaker": airflow_breaker}
    ]
    
    for config in service_configs:
        try:
            response = await config["breaker"].call(
                http_client.get,
                config["url"],
                timeout=5.0
            )
            
            service_data = {
                "name": config["name"],
                "url": config["url"].replace("/health", ""),
                "status": "healthy" if response.status_code == 200 else "unhealthy",
                "last_check": datetime.utcnow().isoformat(),
                "details": response.json() if response.status_code == 200 else {}
            }
        except:
            service_data = {
                "name": config["name"],
                "url": config["url"].replace("/health", ""),
                "status": "unreachable",
                "last_check": datetime.utcnow().isoformat(),
                "details": {"error": "Circuit breaker open or connection failed"}
            }
        
        services.append(service_data)
    
    return {"services": services, "timestamp": datetime.utcnow().isoformat()}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8082,
        reload=False,
        log_level="info"
    )