#!/usr/bin/env python3
"""
Unified orchestration server for DEAN system.

Combines orchestration API, web dashboard, WebSocket support,
and authentication into a single deployable server.
"""

import os
import sys
from pathlib import Path
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
import uvicorn

from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import structlog

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from auth import (
    AuthManager, AuthMiddleware, get_auth_manager,
    UserCredentials, TokenResponse, TokenRefreshRequest,
    User, UserRole, require_auth, require_role, get_current_user
)
from integration import create_authenticated_service_pool
from ..interfaces.web.websocket_handler import WebSocketManager

# Configure logging
logger = structlog.get_logger()

# Global instances
service_pool = None
websocket_manager = None
auth_manager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    global service_pool, websocket_manager, auth_manager
    
    logger.info("Starting DEAN orchestration server...")
    
    # Initialize authentication manager
    auth_manager = get_auth_manager()
    logger.info("Authentication manager initialized")
    
    # Create authenticated service pool
    # Use orchestration server's own credentials for service-to-service auth
    service_pool = await create_authenticated_service_pool(
        api_key=os.getenv("DEAN_SERVICE_API_KEY")
    )
    app.state.service_pool = service_pool
    logger.info("Authenticated service pool created")
    
    # Initialize WebSocket manager
    websocket_manager = WebSocketManager()
    app.state.websocket_manager = websocket_manager
    logger.info("WebSocket manager initialized")
    
    # Log startup information
    logger.info("DEAN orchestration server started",
               host=os.getenv("DEAN_SERVER_HOST", "0.0.0.0"),
               port=int(os.getenv("DEAN_SERVER_PORT", "8082")),
               environment=os.getenv("DEAN_ENV", "development"))
    
    yield
    
    # Cleanup
    logger.info("Shutting down DEAN orchestration server...")
    if service_pool:
        await service_pool.close()
    logger.info("DEAN orchestration server stopped")


# Create FastAPI app
app = FastAPI(
    title="DEAN Orchestration API",
    description="Unified API for DEAN orchestration system",
    version="1.0.0",
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=os.getenv("ALLOWED_HOSTS", "*").split(",")
)

# Add authentication middleware
auth_middleware = AuthMiddleware()
app.middleware("http")(auth_middleware)


# Authentication endpoints
@app.post("/auth/login", response_model=TokenResponse)
async def login(credentials: UserCredentials):
    """Authenticate user and return tokens."""
    user = auth_manager.authenticate_user(credentials)
    if not user:
        logger.warning("Login failed", username=credentials.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    token_response = auth_manager.create_token_response(user)
    logger.info("Login successful", username=user.username, user_id=user.id)
    
    return token_response


@app.post("/auth/refresh", response_model=TokenResponse)
async def refresh_token(refresh_request: TokenRefreshRequest):
    """Refresh access token using refresh token."""
    try:
        token_response = auth_manager.refresh_access_token(refresh_request)
        return token_response
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Token refresh error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )


@app.get("/auth/me", response_model=User)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information."""
    return current_user


# Health endpoints
@app.get("/health")
@app.get("/api/health")
async def health_check():
    """Health check endpoint (no auth required)."""
    return {
        "status": "healthy",
        "service": "dean-orchestration",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }


# System status endpoint
@app.get("/api/system/status")
@require_auth
async def get_system_status(current_user: User = Depends(get_current_user)):
    """Get system status including all services."""
    logger.info("System status requested", username=current_user.username)
    
    # Check service health
    service_status = {}
    
    try:
        # Check IndexAgent
        indexagent_health = await service_pool.indexagent.health_check()
        service_status["indexagent"] = {
            "status": "healthy" if indexagent_health else "unhealthy",
            "url": service_pool.indexagent.base_url
        }
    except Exception as e:
        service_status["indexagent"] = {
            "status": "error",
            "error": str(e)
        }
    
    try:
        # Check Airflow
        airflow_health = await service_pool.airflow.health_check()
        service_status["airflow"] = {
            "status": "healthy" if airflow_health else "unhealthy",
            "url": service_pool.airflow.base_url
        }
    except Exception as e:
        service_status["airflow"] = {
            "status": "error",
            "error": str(e)
        }
    
    try:
        # Check Evolution API
        evolution_health = await service_pool.evolution.health_check()
        service_status["evolution"] = {
            "status": "healthy" if evolution_health else "unhealthy",
            "url": service_pool.evolution.base_url
        }
    except Exception as e:
        service_status["evolution"] = {
            "status": "error",
            "error": str(e)
        }
    
    return {
        "status": "operational",
        "services": service_status,
        "websocket_connections": len(websocket_manager.active_connections) if websocket_manager else 0,
        "timestamp": datetime.utcnow().isoformat()
    }


# Evolution endpoints
@app.post("/api/evolution/trials")
@require_role([UserRole.ADMIN, UserRole.USER])
async def start_evolution_trial(
    request: dict,
    current_user: User = Depends(get_current_user)
):
    """Start a new evolution trial."""
    logger.info("Evolution trial requested",
               username=current_user.username,
               repository=request.get("repository"))
    
    try:
        # Forward to Evolution API
        result = await service_pool.evolution.start_evolution(request)
        
        # Broadcast to WebSocket clients
        await websocket_manager.broadcast({
            "type": "evolution_started",
            "data": result,
            "user": current_user.username,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return result
    except Exception as e:
        logger.error("Failed to start evolution trial", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start evolution trial: {str(e)}"
        )


@app.get("/api/evolution/trials")
@require_auth
async def list_evolution_trials(
    repository: str = None,
    status: str = None,
    limit: int = 100,
    offset: int = 0,
    current_user: User = Depends(get_current_user)
):
    """List evolution trials."""
    try:
        params = {
            "limit": limit,
            "offset": offset
        }
        if repository:
            params["repository"] = repository
        if status:
            params["status"] = status
            
        result = await service_pool.evolution.list_trials(**params)
        return result
    except Exception as e:
        logger.error("Failed to list evolution trials", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list trials: {str(e)}"
        )


@app.get("/api/evolution/trials/{trial_id}")
@require_auth
async def get_evolution_trial(
    trial_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get evolution trial details."""
    try:
        result = await service_pool.evolution.get_trial_status(trial_id)
        return result
    except Exception as e:
        logger.error("Failed to get evolution trial", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get trial: {str(e)}"
        )


# Agent endpoints
@app.get("/api/agents")
@require_auth
async def list_agents(
    limit: int = 100,
    offset: int = 0,
    current_user: User = Depends(get_current_user)
):
    """List agents."""
    logger.info("Agent list requested", username=current_user.username)
    
    try:
        result = await service_pool.indexagent.list_agents(limit=limit, offset=offset)
        return result
    except Exception as e:
        logger.error("Failed to list agents", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list agents: {str(e)}"
        )


@app.post("/api/agents")
@require_role([UserRole.ADMIN, UserRole.USER])
async def create_agent(
    agent_config: dict,
    current_user: User = Depends(get_current_user)
):
    """Create a new agent."""
    logger.info("Agent creation requested",
               username=current_user.username,
               agent_name=agent_config.get("name"))
    
    try:
        result = await service_pool.indexagent.create_agent(agent_config)
        return result
    except Exception as e:
        logger.error("Failed to create agent", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create agent: {str(e)}"
        )


# Pattern endpoints
@app.get("/api/patterns")
@require_auth
async def list_patterns(
    pattern_type: str = None,
    min_confidence: float = 0.0,
    limit: int = 100,
    current_user: User = Depends(get_current_user)
):
    """List discovered patterns."""
    try:
        params = {
            "limit": limit,
            "min_confidence": min_confidence
        }
        if pattern_type:
            params["pattern_type"] = pattern_type
            
        result = await service_pool.indexagent.get_patterns(**params)
        return result
    except Exception as e:
        logger.error("Failed to list patterns", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list patterns: {str(e)}"
        )


# Metrics endpoint
@app.get("/api/system/metrics")
@require_auth
async def get_system_metrics(current_user: User = Depends(get_current_user)):
    """Get system metrics from all services."""
    metrics = {
        "timestamp": datetime.utcnow().isoformat(),
        "services": {}
    }
    
    # Collect metrics from each service
    try:
        indexagent_metrics = await service_pool.indexagent.get_metrics()
        metrics["services"]["indexagent"] = indexagent_metrics
    except Exception as e:
        metrics["services"]["indexagent"] = {"error": str(e)}
    
    try:
        evolution_metrics = await service_pool.evolution.get_metrics()
        metrics["services"]["evolution"] = evolution_metrics
    except Exception as e:
        metrics["services"]["evolution"] = {"error": str(e)}
    
    return metrics


# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket, current_user: User = Depends(get_current_user)):
    """WebSocket endpoint for real-time updates."""
    await websocket_manager.connect(websocket)
    
    try:
        # Send initial connection message
        await websocket.send_json({
            "type": "connection",
            "message": "Connected to DEAN orchestration WebSocket",
            "user": current_user.username,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Keep connection alive
        while True:
            data = await websocket.receive_text()
            
            # Handle ping/pong
            if data == "ping":
                await websocket.send_text("pong")
            else:
                # Broadcast message to all clients
                await websocket_manager.broadcast({
                    "type": "message",
                    "user": current_user.username,
                    "data": data,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
    except Exception as e:
        logger.error("WebSocket error", error=str(e))
    finally:
        websocket_manager.disconnect(websocket)


# Static file serving for web dashboard
static_dir = Path(__file__).parent.parent / "interfaces" / "web" / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    
    @app.get("/")
    async def serve_dashboard():
        """Serve the main dashboard."""
        index_file = static_dir / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        else:
            return JSONResponse(
                {"error": "Dashboard not found"},
                status_code=404
            )
else:
    logger.warning("Static directory not found", path=str(static_dir))


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    logger.warning("HTTP exception",
                  method=request.method,
                  path=request.url.path,
                  status_code=exc.status_code,
                  detail=exc.detail)
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.error("Unhandled exception",
                method=request.method,
                path=request.url.path,
                error=str(exc))
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "status_code": 500,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


def main():
    """Run the unified orchestration server."""
    host = os.getenv("DEAN_SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("DEAN_SERVER_PORT", "8082"))
    reload = os.getenv("DEAN_ENV", "development") == "development"
    
    logger.info("Starting unified orchestration server",
               host=host,
               port=port,
               reload=reload)
    
    uvicorn.run(
        "unified_server:app",
        host=host,
        port=port,
        reload=reload,
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


if __name__ == "__main__":
    main()