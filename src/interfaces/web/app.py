"""DEAN Web Dashboard Application.

Provides a web interface for monitoring and controlling the DEAN system.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pathlib import Path
import json
import asyncio
from typing import Dict, List, Optional
from datetime import datetime
from structlog import get_logger

from ...integration import create_service_pool
from ...orchestration.config_loader import load_config

logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title="DEAN Orchestration Dashboard",
    description="Web interface for the Distributed Evolutionary Agent Network",
    version="0.1.0"
)

# Mount static files
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# WebSocket connection manager
class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("WebSocket client connected", total_connections=len(self.active_connections))
        
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info("WebSocket client disconnected", total_connections=len(self.active_connections))
        
    async def broadcast(self, message: dict):
        """Send message to all connected clients."""
        if not self.active_connections:
            return
            
        message_json = json.dumps(message)
        disconnected = []
        
        for connection in self.active_connections:
            try:
                await connection.send_text(message_json)
            except Exception:
                disconnected.append(connection)
                
        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection)


manager = ConnectionManager()


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Serve the main dashboard page."""
    index_file = static_dir / "index.html"
    
    if not index_file.exists():
        return HTMLResponse(content="""
        <html>
            <head>
                <title>DEAN Dashboard</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 40px; }
                    .error { color: red; }
                </style>
            </head>
            <body>
                <h1>DEAN Dashboard</h1>
                <p class="error">Dashboard HTML file not found. Please run the build process.</p>
            </body>
        </html>
        """)
        
    return HTMLResponse(content=index_file.read_text())


@app.get("/api/system/status")
async def get_system_status():
    """Get current system status."""
    async with create_service_pool() as pool:
        # Check health of all services
        health = await pool.health.check_all_services()
        
        # Get agent counts
        try:
            agents = await pool.indexagent.list_agents()
            agent_count = len(agents)
        except Exception:
            agent_count = 0
            
        # Get recent evolution trials
        try:
            trials = await pool.evolution.get_evolution_results(limit=5)
            recent_trials = len(trials)
        except Exception:
            recent_trials = 0
            
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "status": health["status"],
            "services": health["services"],
            "metrics": {
                "active_agents": agent_count,
                "recent_trials": recent_trials,
                "system_health": 1.0 if health["status"] == "healthy" else 0.5
            }
        }


@app.get("/api/evolution/trials")
async def get_evolution_trials(limit: int = 10, offset: int = 0):
    """Get evolution trial history."""
    async with create_service_pool() as pool:
        try:
            trials = await pool.evolution.get_evolution_results(
                limit=limit,
                offset=offset
            )
            
            return {
                "trials": trials,
                "total": len(trials),
                "limit": limit,
                "offset": offset
            }
        except Exception as e:
            logger.error("Failed to fetch evolution trials", error=str(e))
            return {
                "trials": [],
                "total": 0,
                "limit": limit,
                "offset": offset,
                "error": str(e)
            }


@app.get("/api/agents")
async def get_agents(repository: Optional[str] = None):
    """Get active agents."""
    async with create_service_pool() as pool:
        try:
            agents = await pool.indexagent.list_agents()
            
            # Filter by repository if specified
            if repository:
                agents = [a for a in agents if a.get("repository") == repository]
                
            return {
                "agents": agents,
                "total": len(agents),
                "repository": repository
            }
        except Exception as e:
            logger.error("Failed to fetch agents", error=str(e))
            return {
                "agents": [],
                "total": 0,
                "error": str(e)
            }


@app.get("/api/patterns")
async def get_patterns(pattern_type: Optional[str] = None):
    """Get discovered patterns."""
    async with create_service_pool() as pool:
        try:
            patterns = await pool.evolution.get_patterns()
            
            # Filter by type if specified
            if pattern_type:
                patterns = [p for p in patterns if p.get("type") == pattern_type]
                
            return {
                "patterns": patterns,
                "total": len(patterns),
                "pattern_type": pattern_type
            }
        except Exception as e:
            logger.error("Failed to fetch patterns", error=str(e))
            return {
                "patterns": [],
                "total": 0,
                "error": str(e)
            }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await manager.connect(websocket)
    
    try:
        # Send initial status
        status = await get_system_status()
        await websocket.send_json({
            "type": "status_update",
            "data": status
        })
        
        # Keep connection alive and send periodic updates
        while True:
            try:
                # Wait for any message from client (ping/pong)
                message = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0
                )
                
                # Echo back for ping/pong
                if message == "ping":
                    await websocket.send_text("pong")
                    
            except asyncio.TimeoutError:
                # Send periodic status update
                try:
                    status = await get_system_status()
                    await websocket.send_json({
                        "type": "status_update",
                        "data": status
                    })
                except Exception as e:
                    logger.error("Failed to send status update", error=str(e))
                    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error("WebSocket error", error=str(e))
        manager.disconnect(websocket)


@app.post("/api/evolution/start")
async def start_evolution_trial(repository: str, generations: int = 10, population_size: int = 20):
    """Start a new evolution trial."""
    from ...orchestration import EvolutionTrialCoordinator
    
    try:
        coordinator = EvolutionTrialCoordinator()
        
        # Start trial asynchronously
        asyncio.create_task(run_trial_async(
            coordinator, repository, generations, population_size
        ))
        
        # Broadcast to connected clients
        await manager.broadcast({
            "type": "trial_started",
            "data": {
                "repository": repository,
                "generations": generations,
                "population_size": population_size,
                "timestamp": datetime.utcnow().isoformat()
            }
        })
        
        return {
            "status": "started",
            "repository": repository,
            "generations": generations,
            "population_size": population_size
        }
        
    except Exception as e:
        logger.error("Failed to start evolution trial", error=str(e))
        return {
            "status": "error",
            "error": str(e)
        }


async def run_trial_async(coordinator, repository: str, generations: int, population_size: int):
    """Run evolution trial asynchronously and broadcast updates."""
    try:
        async with coordinator:
            result = await coordinator.run_trial(
                repository,
                config_overrides={
                    'generations': generations,
                    'population_size': population_size
                }
            )
            
            # Broadcast completion
            await manager.broadcast({
                "type": "trial_completed",
                "data": {
                    "trial_id": result.trial_id,
                    "status": result.status,
                    "improvements": len(result.improvements),
                    "timestamp": datetime.utcnow().isoformat()
                }
            })
            
    except Exception as e:
        logger.error("Evolution trial failed", error=str(e))
        
        # Broadcast failure
        await manager.broadcast({
            "type": "trial_failed",
            "data": {
                "repository": repository,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        })


# Add CORS middleware for development
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8082)