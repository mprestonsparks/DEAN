"""Enhanced DEAN Orchestration Server with ServiceRegistry integration.

This module provides the complete orchestration server with service discovery,
health monitoring, and circuit breaker integration.
"""

from fastapi import FastAPI, HTTPException, Depends, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Dict, List, Optional, Any, Union
import os
import logging
import asyncio
from datetime import datetime
from contextlib import asynccontextmanager
from pathlib import Path

from .service_registry import (
    ServiceRegistry, ServiceMetadata, ServiceEndpoint, ServiceStatus,
    ServiceNotFoundError
)
from .circuit_breaker import CircuitBreakerError
from .workflow_coordinator import WorkflowCoordinator
from .workflow_models import WorkflowStatus
from .evolution_trials import EvolutionTrialManager, EvolutionTrial, TrialStatus
from ..auth.dependencies import get_current_user, require_admin

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global instances
service_registry: Optional[ServiceRegistry] = None
workflow_coordinator: Optional[WorkflowCoordinator] = None
evolution_manager: Optional[EvolutionTrialManager] = None


# Pydantic models
class ServiceRegistrationRequest(BaseModel):
    """Service registration request."""
    name: str
    host: str
    port: int
    version: str
    metadata: Optional[Dict[str, Any]] = None
    health_endpoint: Optional[Dict[str, Any]] = None


class ServiceStatusResponse(BaseModel):
    """Service status response."""
    name: str
    host: str
    port: int
    version: str
    status: str
    last_health_check: Optional[str] = None
    last_error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class WorkflowRequest(BaseModel):
    """Workflow execution request."""
    workflow_type: str
    parameters: Dict[str, Any]


class AgentRequest(BaseModel):
    """Agent creation request."""
    goal: str
    token_budget: int = 1000
    diversity_weight: float = 0.3


class EvolutionTrialRequest(BaseModel):
    """Evolution trial configuration."""
    population_size: int = 10
    generations: int = 50
    token_budget: int = 100000
    diversity_threshold: float = 0.3


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    global service_registry, workflow_coordinator, evolution_manager
    
    # Startup
    logger.info("Starting DEAN Orchestration Server")
    
    # Initialize service registry
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    service_registry = ServiceRegistry(
        redis_url=redis_url,
        health_check_interval=30.0,
        enable_persistence=True
    )
    await service_registry.start()
    
    # Initialize workflow coordinator
    workflow_templates_path = os.getenv("WORKFLOW_TEMPLATES_PATH", "docs/workflow_examples")
    workflow_coordinator = WorkflowCoordinator(
        service_registry=service_registry,
        redis_url=redis_url,
        enable_persistence=True,
        workflow_templates_path=workflow_templates_path
    )
    await workflow_coordinator.start()
    
    # Initialize evolution trial manager
    evolution_manager = EvolutionTrialManager(workflow_coordinator)
    
    # Register known services automatically
    await auto_register_services()
    
    yield
    
    # Shutdown
    logger.info("Shutting down DEAN Orchestration Server")
    if workflow_coordinator:
        await workflow_coordinator.stop()
    if service_registry:
        await service_registry.stop()


# Create FastAPI app with lifespan
app = FastAPI(
    title="DEAN Orchestration Server",
    description="Distributed Evolutionary Agent Network - Primary Orchestration Layer with ServiceRegistry",
    version="0.2.0",
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

# Mount static files for web dashboard
web_path = Path(__file__).parent.parent.parent / "web"
if web_path.exists():
    app.mount("/static", StaticFiles(directory=str(web_path)), name="static")


async def auto_register_services():
    """Auto-register known services from environment."""
    services = [
        {
            "name": "IndexAgent",
            "host": os.getenv("INDEXAGENT_HOST", "indexagent"),
            "port": int(os.getenv("INDEXAGENT_PORT", "8081")),
            "version": "1.0.0",
            "metadata": {
                "service_type": "agent-management",
                "api_version": "v1",
                "capabilities": ["agent-creation", "agent-evolution", "pattern-detection"],
                "endpoints": {
                    "agents": "/api/v1/agents",
                    "patterns": "/api/v1/patterns"
                }
            }
        },
        {
            "name": "Airflow",
            "host": os.getenv("AIRFLOW_HOST", "airflow-service"),
            "port": int(os.getenv("AIRFLOW_PORT", "8080")),
            "version": "3.0.0",
            "metadata": {
                "service_type": "workflow-orchestration",
                "api_version": "v1",
                "capabilities": ["dag-execution", "task-scheduling"],
                "endpoints": {
                    "dags": "/api/v1/dags",
                    "dag_runs": "/api/v1/dag_runs"
                }
            }
        },
        {
            "name": "EvolutionAPI",
            "host": os.getenv("EVOLUTION_API_HOST", "agent-evolution"),
            "port": int(os.getenv("EVOLUTION_API_PORT", "8090")),
            "version": "1.0.0",
            "metadata": {
                "service_type": "evolution-engine",
                "api_version": "v1",
                "capabilities": ["genetic-algorithms", "diversity-management", "token-economy"],
                "endpoints": {
                    "evolution": "/api/v1/evolution",
                    "metrics": "/api/v1/metrics"
                }
            }
        }
    ]
    
    for service_config in services:
        try:
            await service_registry.register_service(
                name=service_config["name"],
                host=service_config["host"],
                port=service_config["port"],
                version=service_config["version"],
                metadata=ServiceMetadata(**service_config["metadata"])
            )
            logger.info(f"Auto-registered service: {service_config['name']}")
        except Exception as e:
            logger.error(f"Failed to auto-register {service_config['name']}: {e}")


# API Endpoints

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "DEAN Orchestration Server",
        "version": "0.2.0",
        "status": "operational",
        "features": ["service-registry", "health-monitoring", "circuit-breaker", "web-dashboard"],
        "documentation": "/docs",
        "dashboard": "/dashboard"
    }


@app.get("/dashboard")
async def dashboard():
    """Serve the web dashboard."""
    web_file = Path(__file__).parent.parent.parent / "web" / "index.html"
    if web_file.exists():
        return FileResponse(str(web_file))
    else:
        raise HTTPException(status_code=404, detail="Dashboard not found")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    registry_status = "healthy" if service_registry and service_registry._running else "unhealthy"
    
    return {
        "status": "healthy",
        "service": "DEAN Orchestration Server",
        "version": "0.2.0",
        "port": 8082,
        "registry_status": registry_status,
        "timestamp": datetime.utcnow().isoformat()
    }


# Service Registry endpoints

@app.post("/api/v1/registry/register", response_model=ServiceStatusResponse)
async def register_service(request: ServiceRegistrationRequest):
    """Register a new service with the registry."""
    try:
        metadata = None
        if request.metadata:
            metadata = ServiceMetadata(**request.metadata)
            
        health_endpoint = None
        if request.health_endpoint:
            health_endpoint = ServiceEndpoint(**request.health_endpoint)
            
        service = await service_registry.register_service(
            name=request.name,
            host=request.host,
            port=request.port,
            version=request.version,
            metadata=metadata,
            health_endpoint=health_endpoint
        )
        
        return ServiceStatusResponse(
            name=service.name,
            host=service.host,
            port=service.port,
            version=service.version,
            status=service.status.value,
            last_health_check=service.last_health_check.isoformat() if service.last_health_check else None,
            last_error=service.last_error,
            metadata=request.metadata
        )
    except Exception as e:
        logger.error(f"Service registration failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/v1/registry/services/{service_name}")
async def deregister_service(service_name: str):
    """Remove a service from the registry."""
    removed = await service_registry.deregister_service(service_name)
    if not removed:
        raise HTTPException(status_code=404, detail=f"Service '{service_name}' not found")
    return {"message": f"Service '{service_name}' deregistered successfully"}


@app.get("/api/v1/registry/services", response_model=List[ServiceStatusResponse])
async def list_services(service_type: Optional[str] = None, capability: Optional[str] = None):
    """List all registered services with optional filtering."""
    if service_type:
        services = await service_registry.discover_services_by_type(service_type)
    elif capability:
        services = await service_registry.discover_services_by_capability(capability)
    else:
        services = list((await service_registry.get_all_services()).values())
        
    return [
        ServiceStatusResponse(
            name=s.name,
            host=s.host,
            port=s.port,
            version=s.version,
            status=s.status.value,
            last_health_check=s.last_health_check.isoformat() if s.last_health_check else None,
            last_error=s.last_error,
            metadata=s.metadata.__dict__ if s.metadata else None
        )
        for s in services
    ]


@app.get("/api/v1/registry/services/{service_name}", response_model=ServiceStatusResponse)
async def get_service(service_name: str):
    """Get details of a specific service."""
    service = await service_registry.discover_service(service_name)
    if not service:
        raise HTTPException(status_code=404, detail=f"Service '{service_name}' not found")
        
    return ServiceStatusResponse(
        name=service.name,
        host=service.host,
        port=service.port,
        version=service.version,
        status=service.status.value,
        last_health_check=service.last_health_check.isoformat() if service.last_health_check else None,
        last_error=service.last_error,
        metadata=service.metadata.__dict__ if service.metadata else None
    )


@app.post("/api/v1/registry/services/{service_name}/heartbeat")
async def service_heartbeat(service_name: str):
    """Receive heartbeat from a service."""
    service = await service_registry.discover_service(service_name)
    if not service:
        raise HTTPException(status_code=404, detail=f"Service '{service_name}' not found")
        
    # Update last health check time
    service.last_health_check = datetime.utcnow()
    service.status = ServiceStatus.HEALTHY
    
    return {"message": "Heartbeat received"}


@app.patch("/api/v1/registry/services/{service_name}/metadata")
async def update_service_metadata(service_name: str, metadata: Dict[str, Any]):
    """Update service metadata."""
    service = await service_registry.discover_service(service_name)
    if not service:
        raise HTTPException(status_code=404, detail=f"Service '{service_name}' not found")
        
    service.metadata = ServiceMetadata(**metadata)
    return {"message": f"Metadata updated for service '{service_name}'"}


# Service orchestration endpoints

@app.get("/api/v1/services/status")
async def get_services_status():
    """Get status of all services using ServiceRegistry."""
    services = await service_registry.get_all_services()
    
    return {
        "services": [
            {
                "name": service.name,
                "url": service.base_url,
                "status": service.status.value,
                "last_check": service.last_health_check.isoformat() if service.last_health_check else None,
                "version": service.version,
                "health": service.status == ServiceStatus.HEALTHY
            }
            for service in services.values()
        ]
    }


@app.post("/api/v1/agents/create")
async def create_agent(request: AgentRequest):
    """Create a new agent via IndexAgent using ServiceRegistry."""
    try:
        response = await service_registry.call_service(
            "IndexAgent",
            "/api/v1/agents",
            method="POST",
            json={
                "goal": request.goal,
                "token_budget": request.token_budget,
                "diversity_weight": request.diversity_weight
            }
        )
        return response.json()
    except ServiceNotFoundError:
        raise HTTPException(status_code=503, detail="IndexAgent service not available")
    except CircuitBreakerError as e:
        raise HTTPException(status_code=503, detail=f"IndexAgent service temporarily unavailable: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to create agent: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create agent: {str(e)}")


@app.post("/api/v1/workflows/execute")
async def execute_workflow(request: WorkflowRequest):
    """Execute a workflow coordinating multiple services."""
    workflow_id = f"workflow_{datetime.utcnow().timestamp()}"
    
    # In a full implementation, this would coordinate with Airflow
    # For now, return a placeholder response
    return {
        "workflow_id": workflow_id,
        "status": "accepted",
        "workflow_type": request.workflow_type,
        "message": "Workflow execution initiated",
        "registry_status": "using_service_registry"
    }


@app.get("/api/v1/evolution/status")
async def get_evolution_status():
    """Get current evolution trial status from Evolution API."""
    try:
        response = await service_registry.call_service(
            "EvolutionAPI",
            "/api/v1/evolution/status",
            method="GET"
        )
        return response.json()
    except ServiceNotFoundError:
        # Return default if service not available
        return {
            "active_trials": 0,
            "total_agents": 0,
            "generation": 1,
            "fitness_average": 0.0,
            "diversity_score": 0.0,
            "service_status": "unavailable"
        }
    except Exception as e:
        logger.error(f"Failed to get evolution status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/orchestration/evolution/start")
async def start_evolution_trial(request: EvolutionTrialRequest):
    """Start a new evolution trial orchestrating multiple services."""
    trial_id = f"trial_{datetime.utcnow().timestamp()}"
    
    try:
        # Step 1: Initialize population in IndexAgent
        indexagent_response = await service_registry.call_service(
            "IndexAgent",
            "/api/v1/agents/population/initialize",
            method="POST",
            json={
                "size": request.population_size,
                "diversity_threshold": request.diversity_threshold
            }
        )
        population_data = indexagent_response.json()
        
        # Step 2: Start evolution in Evolution API
        evolution_response = await service_registry.call_service(
            "EvolutionAPI",
            "/api/v1/evolution/start",
            method="POST",
            json={
                "population_ids": population_data.get("agent_ids", []),
                "generations": request.generations,
                "token_budget": request.token_budget
            }
        )
        evolution_data = evolution_response.json()
        
        # Step 3: Trigger Airflow DAG
        airflow_response = await service_registry.call_service(
            "Airflow",
            "/api/v1/dags/agent_evolution_trial/dagRuns",
            method="POST",
            json={
                "conf": {
                    "trial_id": trial_id,
                    "evolution_job_id": evolution_data.get("job_id")
                }
            }
        )
        
        return {
            "trial_id": trial_id,
            "status": "started",
            "population_size": request.population_size,
            "evolution_job_id": evolution_data.get("job_id"),
            "dag_run_id": airflow_response.json().get("dag_run_id"),
            "message": "Evolution trial initiated successfully across all services"
        }
        
    except ServiceNotFoundError as e:
        raise HTTPException(status_code=503, detail=f"Required service not available: {str(e)}")
    except CircuitBreakerError as e:
        raise HTTPException(status_code=503, detail=f"Service temporarily unavailable: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to start evolution trial: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start evolution trial: {str(e)}")


# Workflow Management endpoints

@app.post("/api/v1/workflows")
async def create_workflow(workflow_def: Union[Dict[str, Any], str]):
    """Create a new workflow definition.
    
    Accepts workflow definition as JSON object or YAML string.
    """
    try:
        workflow = await workflow_coordinator.create_workflow(workflow_def)
        return {
            "id": workflow.id,
            "name": workflow.name,
            "version": workflow.version,
            "steps": len(workflow.steps),
            "message": "Workflow created successfully"
        }
    except Exception as e:
        logger.error(f"Failed to create workflow: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/workflows/{workflow_id}/execute")
async def execute_workflow(workflow_id: str, context: Optional[Dict[str, Any]] = None):
    """Execute a workflow by ID."""
    try:
        instance = await workflow_coordinator.start_workflow(workflow_id, context)
        return {
            "instance_id": instance.id,
            "workflow_id": instance.workflow_id,
            "workflow_name": instance.workflow_name,
            "status": instance.status.value,
            "started_at": instance.started_at.isoformat() if instance.started_at else None,
            "context": instance.context
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to execute workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/workflows/templates/{template_name}/execute")
async def execute_workflow_template(template_name: str, context: Optional[Dict[str, Any]] = None):
    """Execute a workflow from a template."""
    try:
        instance = await workflow_coordinator.create_workflow_from_template(template_name, context)
        return {
            "instance_id": instance.id,
            "workflow_id": instance.workflow_id,
            "workflow_name": instance.workflow_name,
            "status": instance.status.value,
            "template": template_name,
            "message": "Workflow started from template"
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to execute workflow template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/workflows/instances")
async def list_workflow_instances(
    status: Optional[str] = None,
    limit: int = 100
):
    """List workflow instances with optional filtering."""
    try:
        status_filter = WorkflowStatus(status) if status else None
        instances = await workflow_coordinator.list_workflows(status_filter, limit)
        
        return {
            "instances": [
                {
                    "id": inst.id,
                    "workflow_id": inst.workflow_id,
                    "workflow_name": inst.workflow_name,
                    "status": inst.status.value,
                    "created_at": inst.created_at.isoformat(),
                    "started_at": inst.started_at.isoformat() if inst.started_at else None,
                    "completed_at": inst.completed_at.isoformat() if inst.completed_at else None
                }
                for inst in instances
            ],
            "total": len(instances)
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid status: {str(e)}")


@app.get("/api/v1/workflows/instances/{instance_id}")
async def get_workflow_instance(instance_id: str):
    """Get detailed information about a workflow instance."""
    instance = await workflow_coordinator.get_workflow_status(instance_id)
    if not instance:
        raise HTTPException(status_code=404, detail=f"Workflow instance '{instance_id}' not found")
    
    # Get workflow definition for step details
    workflow = workflow_coordinator._workflows.get(instance.workflow_id)
    
    return {
        "id": instance.id,
        "workflow_id": instance.workflow_id,
        "workflow_name": instance.workflow_name,
        "workflow_version": instance.workflow_version,
        "status": instance.status.value,
        "context": instance.context,
        "current_steps": instance.current_steps,
        "created_at": instance.created_at.isoformat(),
        "started_at": instance.started_at.isoformat() if instance.started_at else None,
        "completed_at": instance.completed_at.isoformat() if instance.completed_at else None,
        "error": instance.error,
        "failed_step_id": instance.failed_step_id,
        "steps": [
            {
                "id": step.id,
                "name": step.name,
                "type": step.type.value,
                "status": step.status.value,
                "start_time": step.start_time.isoformat() if step.start_time else None,
                "end_time": step.end_time.isoformat() if step.end_time else None,
                "error": step.error,
                "attempts": step.attempts
            }
            for step in (workflow.steps if workflow else [])
        ] if workflow else None
    }


@app.post("/api/v1/workflows/instances/{instance_id}/cancel")
async def cancel_workflow_instance(instance_id: str):
    """Cancel a running workflow instance."""
    cancelled = await workflow_coordinator.cancel_workflow(instance_id)
    if not cancelled:
        raise HTTPException(
            status_code=404,
            detail=f"Workflow instance '{instance_id}' not found or not running"
        )
    
    return {"message": f"Workflow instance '{instance_id}' cancelled successfully"}


@app.post("/api/v1/workflows/instances/{instance_id}/resume")
async def resume_workflow_instance(instance_id: str):
    """Resume a failed or cancelled workflow instance."""
    try:
        instance = await workflow_coordinator.resume_workflow(instance_id)
        return {
            "instance_id": instance.id,
            "status": instance.status.value,
            "message": "Workflow resumed successfully"
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to resume workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/workflows/metrics")
async def get_workflow_metrics():
    """Get workflow coordinator metrics."""
    metrics = workflow_coordinator.get_workflow_metrics()
    return metrics


@app.websocket("/ws/workflows/{instance_id}")
async def workflow_websocket(websocket: WebSocket, instance_id: str):
    """WebSocket endpoint for real-time workflow monitoring."""
    await websocket.accept()
    
    try:
        # Send initial status
        instance = await workflow_coordinator.get_workflow_status(instance_id)
        if instance:
            await websocket.send_json({
                "type": "status",
                "instance_id": instance_id,
                "status": instance.status.value,
                "current_steps": instance.current_steps
            })
        
        # Monitor workflow events
        # In a full implementation, this would subscribe to workflow events
        while True:
            await asyncio.sleep(1)
            
            # Check instance status
            instance = await workflow_coordinator.get_workflow_status(instance_id)
            if instance:
                await websocket.send_json({
                    "type": "update",
                    "instance_id": instance_id,
                    "status": instance.status.value,
                    "current_steps": instance.current_steps,
                    "context": instance.context
                })
                
                # Exit if workflow completed
                if instance.status in [WorkflowStatus.COMPLETED, WorkflowStatus.FAILED, WorkflowStatus.CANCELLED]:
                    await websocket.send_json({
                        "type": "complete",
                        "instance_id": instance_id,
                        "status": instance.status.value,
                        "error": instance.error
                    })
                    break
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for workflow {instance_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close()


@app.get("/metrics")
async def prometheus_metrics(response: Response):
    """Prometheus metrics endpoint with ServiceRegistry metrics."""
    response.headers["Content-Type"] = "text/plain; version=0.0.4"
    
    # Get registry metrics
    registry_metrics = service_registry.get_metrics() if service_registry else {}
    
    # Get workflow metrics
    workflow_metrics = workflow_coordinator.get_workflow_metrics() if workflow_coordinator else {}
    
    # Get evolution metrics
    evolution_metrics = {
        "active_trials": len([t for t in evolution_manager.trials.values() if t.status == TrialStatus.RUNNING]) if evolution_manager else 0,
        "total_trials": len(evolution_manager.trials) if evolution_manager else 0
    }
    
    metrics = f"""# HELP dean_orchestrator_requests_total Total requests
# TYPE dean_orchestrator_requests_total counter
dean_orchestrator_requests_total 0

# HELP dean_orchestrator_active_workflows Active workflows
# TYPE dean_orchestrator_active_workflows gauge
dean_orchestrator_active_workflows {workflow_metrics.get('running_instances', 0)}

# HELP dean_orchestrator_service_health Service health status
# TYPE dean_orchestrator_service_health gauge
dean_orchestrator_service_health 1

# HELP dean_registered_services_total Total registered services
# TYPE dean_registered_services_total gauge
dean_registered_services_total {registry_metrics.get('total_services', 0)}

# HELP dean_healthy_services_total Total healthy services
# TYPE dean_healthy_services_total gauge
dean_healthy_services_total {registry_metrics.get('healthy_services', 0)}

# HELP dean_unhealthy_services_total Total unhealthy services
# TYPE dean_unhealthy_services_total gauge
dean_unhealthy_services_total {registry_metrics.get('unhealthy_services', 0)}

# HELP dean_workflow_definitions_total Total workflow definitions
# TYPE dean_workflow_definitions_total gauge
dean_workflow_definitions_total {workflow_metrics.get('total_workflows', 0)}

# HELP dean_workflow_instances_total Total workflow instances
# TYPE dean_workflow_instances_total gauge
dean_workflow_instances_total {workflow_metrics.get('total_instances', 0)}

# HELP dean_workflow_templates_loaded Total workflow templates loaded
# TYPE dean_workflow_templates_loaded gauge
dean_workflow_templates_loaded {workflow_metrics.get('templates_loaded', 0)}

# HELP dean_evolution_trials_active Active evolution trials
# TYPE dean_evolution_trials_active gauge
dean_evolution_trials_active {evolution_metrics['active_trials']}

# HELP dean_evolution_trials_total Total evolution trials
# TYPE dean_evolution_trials_total gauge
dean_evolution_trials_total {evolution_metrics['total_trials']}
"""
    
    return metrics


# Evolution Trial endpoints

@app.post("/api/v1/orchestration/evolution/start")
async def start_evolution_trial_v2(
    request: EvolutionTrialRequest,
    auth_token: Optional[str] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Start a new evolution trial using the workflow-based system.
    
    This endpoint creates an evolution trial and executes it using the
    Evolution Trial workflow template with proper authentication propagation.
    """
    try:
        # Create the trial
        trial = await evolution_manager.create_trial(
            name=f"Evolution Trial {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}",
            population_size=request.population_size,
            generations=request.generations,
            mutation_rate=0.1,  # Default mutation rate
            crossover_rate=0.7,  # Default crossover rate
            token_budget=request.token_budget,
            diversity_threshold=request.diversity_threshold,
            auth_token=auth_token
        )
        
        # Start the trial (which starts the workflow)
        await evolution_manager.start_trial(trial.id, auth_token=auth_token)
        
        return {
            "trial_id": trial.id,
            "workflow_instance_id": trial.workflow_instance_id,
            "status": trial.status,
            "parameters": {
                "population_size": trial.population_size,
                "generations": trial.generations,
                "token_budget": trial.token_budget,
                "diversity_threshold": trial.diversity_threshold
            },
            "message": "Evolution trial started successfully",
            "websocket_url": f"/ws/evolution/{trial.id}"
        }
        
    except Exception as e:
        logger.error(f"Failed to start evolution trial: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/orchestration/evolution/{trial_id}/status")
async def get_evolution_trial_status(
    trial_id: str,
    auth_token: Optional[str] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get detailed status of an evolution trial.
    
    Returns comprehensive trial information including progress, metrics,
    and discovered patterns.
    """
    trial = await evolution_manager.get_trial(trial_id)
    if not trial:
        raise HTTPException(status_code=404, detail=f"Trial {trial_id} not found")
        
    # Get summary with progress information
    summary = evolution_manager.get_trial_metrics_summary(trial_id)
    
    return {
        "trial_id": trial.id,
        "name": trial.name,
        "status": trial.status,
        "workflow_instance_id": trial.workflow_instance_id,
        "parameters": {
            "population_size": trial.population_size,
            "generations": trial.generations,
            "token_budget": trial.token_budget,
            "diversity_threshold": trial.diversity_threshold
        },
        "progress": summary["progress"],
        "resource_usage": summary["resource_usage"],
        "performance": summary["performance"],
        "timing": summary["timing"],
        "generation_metrics": [m.dict() for m in trial.generation_metrics[-10:]],  # Last 10 generations
        "agent_count": len(trial.agent_metrics),
        "best_agent": {
            "id": trial.best_agent_id,
            "fitness": trial.best_fitness_score
        } if trial.best_agent_id else None,
        "error": trial.error_message
    }


@app.get("/api/v1/orchestration/evolution/list")
async def list_evolution_trials(
    status: Optional[TrialStatus] = None,
    limit: int = 100,
    auth_token: Optional[str] = Depends(get_current_user)
) -> Dict[str, Any]:
    """List evolution trials with optional filtering.
    
    Returns a list of trials with summary information.
    """
    trials = await evolution_manager.list_trials(status=status, limit=limit)
    
    return {
        "trials": [
            {
                "trial_id": trial.id,
                "name": trial.name,
                "status": trial.status,
                "created_at": trial.created_at.isoformat(),
                "started_at": trial.started_at.isoformat() if trial.started_at else None,
                "completed_at": trial.completed_at.isoformat() if trial.completed_at else None,
                "population_size": trial.population_size,
                "generations": trial.generations,
                "current_generation": trial.current_generation,
                "best_fitness": trial.best_fitness_score,
                "tokens_used": trial.total_tokens_used,
                "patterns_discovered": len(trial.discovered_patterns)
            }
            for trial in trials
        ],
        "total": len(trials)
    }


@app.post("/api/v1/orchestration/evolution/{trial_id}/cancel")
async def cancel_evolution_trial(
    trial_id: str,
    auth_token: Optional[str] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Cancel a running evolution trial.
    
    Cancels the trial workflow and performs cleanup.
    """
    cancelled = await evolution_manager.cancel_trial(trial_id)
    
    if not cancelled:
        raise HTTPException(
            status_code=404,
            detail=f"Trial {trial_id} not found or not cancellable"
        )
        
    return {
        "trial_id": trial_id,
        "status": "cancelled",
        "message": "Evolution trial cancelled successfully"
    }


@app.websocket("/ws/evolution/{trial_id}")
async def evolution_trial_websocket(websocket: WebSocket, trial_id: str):
    """WebSocket endpoint for real-time evolution trial monitoring.
    
    Streams updates including generation progress, agent metrics,
    pattern discoveries, and resource usage.
    """
    await websocket.accept()
    
    # Subscribe to trial updates
    update_queue = await evolution_manager.subscribe_to_trial(trial_id)
    
    try:
        while True:
            # Get update from queue
            update = await update_queue.get()
            
            # Send to client
            await websocket.send_json(update)
            
            # Check if trial completed
            if update.get("type") == "update":
                status = update.get("status")
                if status in [TrialStatus.COMPLETED, TrialStatus.FAILED, TrialStatus.CANCELLED]:
                    # Send final message
                    await websocket.send_json({
                        "type": "complete",
                        "trial_id": trial_id,
                        "status": status,
                        "message": f"Trial {status.lower()}"
                    })
                    break
                    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for evolution trial {trial_id}")
    except Exception as e:
        logger.error(f"WebSocket error for evolution trial {trial_id}: {e}")
        await websocket.close()
    finally:
        # Unsubscribe from updates
        await evolution_manager.unsubscribe_from_trial(trial_id, update_queue)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8082)