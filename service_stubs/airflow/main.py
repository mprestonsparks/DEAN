#!/usr/bin/env python3
"""
Airflow API Stub

Provides a minimal implementation of the Airflow v2 REST API for development.
Implements basic authentication and DAG management.
"""

import asyncio
import os
import random
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import uuid4
from enum import Enum

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import structlog
import uvicorn
import secrets

# Configure logging
logger = structlog.get_logger()

# Create FastAPI app
app = FastAPI(
    title="Airflow Stub API",
    description="Mock Airflow service for DEAN development",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBasic()

def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    """Verify HTTP Basic authentication.
    
    Note: Airflow uses Basic Auth by default. In production, it can be configured
    to use OAuth, LDAP, or other authentication backends. This stub maintains
    compatibility with standard Airflow authentication.
    
    The DEAN orchestrator should use these credentials when making service-to-service
    calls to Airflow.
    """
    correct_username = os.getenv("AIRFLOW_USERNAME", "airflow")
    correct_password = os.getenv("AIRFLOW_PASSWORD", "airflow")
    
    is_correct_username = secrets.compare_digest(
        credentials.username.encode("utf8"),
        correct_username.encode("utf8")
    )
    is_correct_password = secrets.compare_digest(
        credentials.password.encode("utf8"),
        correct_password.encode("utf8")
    )
    
    if not (is_correct_username and is_correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    return credentials.username

# Enums
class DagState(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"

class DagRunState(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"

class TaskState(str, Enum):
    NONE = "none"
    SCHEDULED = "scheduled"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    UPSTREAM_FAILED = "upstream_failed"
    SKIPPED = "skipped"

# In-memory storage
class AirflowDataStore:
    def __init__(self):
        self.dags = self._create_mock_dags()
        self.dag_runs: Dict[str, List[Dict]] = {}
        self.task_instances: Dict[str, List[Dict]] = {}
        
    def _create_mock_dags(self) -> Dict[str, Dict]:
        """Create mock DAGs including DEAN evolution DAGs."""
        dags = {
            "evolution_workflow": {
                "dag_id": "evolution_workflow",
                "description": "DEAN Evolution Trial Workflow",
                "file_token": "evolution_workflow.py",
                "fileloc": "/opt/airflow/dags/evolution_workflow.py",
                "is_paused": False,
                "is_active": True,
                "is_subdag": False,
                "owners": ["dean"],
                "schedule_interval": None,
                "tags": ["evolution", "dean"],
                "tasks": [
                    "initialize_population",
                    "run_evolution",
                    "extract_patterns",
                    "persist_results"
                ]
            },
            "pattern_propagation": {
                "dag_id": "pattern_propagation",
                "description": "Propagate discovered patterns across repositories",
                "file_token": "pattern_propagation.py",
                "fileloc": "/opt/airflow/dags/pattern_propagation.py",
                "is_paused": False,
                "is_active": True,
                "is_subdag": False,
                "owners": ["dean"],
                "schedule_interval": "@daily",
                "tags": ["patterns", "dean"],
                "tasks": [
                    "fetch_patterns",
                    "validate_patterns",
                    "apply_patterns",
                    "report_results"
                ]
            },
            "system_monitoring": {
                "dag_id": "system_monitoring",
                "description": "Monitor DEAN system health",
                "file_token": "system_monitoring.py",
                "fileloc": "/opt/airflow/dags/system_monitoring.py",
                "is_paused": False,
                "is_active": True,
                "is_subdag": False,
                "owners": ["dean"],
                "schedule_interval": "*/5 * * * *",  # Every 5 minutes
                "tags": ["monitoring", "dean"],
                "tasks": [
                    "check_services",
                    "collect_metrics",
                    "alert_on_issues"
                ]
            }
        }
        return dags

# Initialize data store
data_store = AirflowDataStore()

# Pydantic models
class DagRunRequest(BaseModel):
    conf: Optional[Dict[str, Any]] = Field(default_factory=dict)
    execution_date: Optional[str] = None
    logical_date: Optional[str] = None
    note: Optional[str] = None

class DagRun(BaseModel):
    dag_run_id: str
    dag_id: str
    logical_date: str
    execution_date: str
    start_date: Optional[str]
    end_date: Optional[str]
    state: DagRunState
    external_trigger: bool = True
    conf: Dict[str, Any] = Field(default_factory=dict)
    note: Optional[str] = None

# Health endpoint (no auth required)
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "airflow-stub",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime_seconds": int(time.time() - app.state.start_time)
    }

# DAG endpoints
@app.get("/api/v1/dags", dependencies=[Depends(verify_credentials)])
async def list_dags(
    limit: int = 100,
    offset: int = 0,
    tags: Optional[str] = None,
    only_active: bool = True
):
    """List all DAGs."""
    dags = list(data_store.dags.values())
    
    # Filter by active status
    if only_active:
        dags = [d for d in dags if d["is_active"]]
    
    # Filter by tags
    if tags:
        tag_list = tags.split(",")
        dags = [d for d in dags if any(tag in d["tags"] for tag in tag_list)]
    
    # Paginate
    total = len(dags)
    dags = dags[offset:offset + limit]
    
    return {
        "dags": dags,
        "total_entries": total
    }

@app.get("/api/v1/dags/{dag_id}", dependencies=[Depends(verify_credentials)])
async def get_dag(dag_id: str):
    """Get a specific DAG."""
    if dag_id not in data_store.dags:
        raise HTTPException(status_code=404, detail="DAG not found")
    
    return data_store.dags[dag_id]

@app.patch("/api/v1/dags/{dag_id}", dependencies=[Depends(verify_credentials)])
async def update_dag(dag_id: str, is_paused: bool):
    """Update a DAG (pause/unpause)."""
    if dag_id not in data_store.dags:
        raise HTTPException(status_code=404, detail="DAG not found")
    
    data_store.dags[dag_id]["is_paused"] = is_paused
    logger.info("DAG updated", dag_id=dag_id, is_paused=is_paused)
    
    return data_store.dags[dag_id]

# DAG Run endpoints
@app.post("/api/v1/dags/{dag_id}/dagRuns", dependencies=[Depends(verify_credentials)])
async def trigger_dag(dag_id: str, dag_run_request: DagRunRequest):
    """Trigger a new DAG run."""
    if dag_id not in data_store.dags:
        raise HTTPException(status_code=404, detail="DAG not found")
    
    if data_store.dags[dag_id]["is_paused"]:
        raise HTTPException(status_code=409, detail="DAG is paused")
    
    # Create DAG run
    run_id = f"manual__{datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')}__1"
    execution_date = dag_run_request.execution_date or datetime.utcnow().isoformat()
    
    dag_run = DagRun(
        dag_run_id=run_id,
        dag_id=dag_id,
        logical_date=execution_date,
        execution_date=execution_date,
        start_date=datetime.utcnow().isoformat(),
        end_date=None,
        state=DagRunState.RUNNING,
        external_trigger=True,
        conf=dag_run_request.conf,
        note=dag_run_request.note
    )
    
    # Store the run
    if dag_id not in data_store.dag_runs:
        data_store.dag_runs[dag_id] = []
    data_store.dag_runs[dag_id].append(dag_run.dict())
    
    # Simulate task execution
    asyncio.create_task(simulate_dag_execution(dag_id, run_id))
    
    logger.info("DAG triggered", dag_id=dag_id, run_id=run_id)
    return dag_run

async def simulate_dag_execution(dag_id: str, run_id: str):
    """Simulate DAG execution with state transitions."""
    # Wait a bit
    await asyncio.sleep(random.uniform(2, 5))
    
    # Find the run
    for run in data_store.dag_runs.get(dag_id, []):
        if run["dag_run_id"] == run_id:
            # Simulate success or failure
            if random.random() > 0.1:  # 90% success rate
                run["state"] = DagRunState.SUCCESS
                run["end_date"] = datetime.utcnow().isoformat()
                logger.info("DAG run completed", dag_id=dag_id, run_id=run_id, state="success")
            else:
                run["state"] = DagRunState.FAILED
                run["end_date"] = datetime.utcnow().isoformat()
                logger.info("DAG run failed", dag_id=dag_id, run_id=run_id, state="failed")
            break

@app.get("/api/v1/dags/{dag_id}/dagRuns", dependencies=[Depends(verify_credentials)])
async def list_dag_runs(
    dag_id: str,
    limit: int = 100,
    offset: int = 0,
    state: Optional[List[DagRunState]] = None
):
    """List DAG runs."""
    if dag_id not in data_store.dags:
        raise HTTPException(status_code=404, detail="DAG not found")
    
    runs = data_store.dag_runs.get(dag_id, [])
    
    # Filter by state
    if state:
        runs = [r for r in runs if r["state"] in state]
    
    # Sort by execution date descending
    runs.sort(key=lambda r: r["execution_date"], reverse=True)
    
    # Paginate
    total = len(runs)
    runs = runs[offset:offset + limit]
    
    return {
        "dag_runs": runs,
        "total_entries": total
    }

@app.get("/api/v1/dags/{dag_id}/dagRuns/{dag_run_id}", dependencies=[Depends(verify_credentials)])
async def get_dag_run(dag_id: str, dag_run_id: str):
    """Get a specific DAG run."""
    if dag_id not in data_store.dags:
        raise HTTPException(status_code=404, detail="DAG not found")
    
    runs = data_store.dag_runs.get(dag_id, [])
    for run in runs:
        if run["dag_run_id"] == dag_run_id:
            return run
    
    raise HTTPException(status_code=404, detail="DAG run not found")

# Task Instance endpoints
@app.get("/api/v1/dags/{dag_id}/dagRuns/{dag_run_id}/taskInstances", 
         dependencies=[Depends(verify_credentials)])
async def list_task_instances(dag_id: str, dag_run_id: str):
    """List task instances for a DAG run."""
    if dag_id not in data_store.dags:
        raise HTTPException(status_code=404, detail="DAG not found")
    
    # Create mock task instances based on DAG tasks
    tasks = data_store.dags[dag_id].get("tasks", [])
    task_instances = []
    
    # Get the DAG run to check its state
    dag_run = None
    for run in data_store.dag_runs.get(dag_id, []):
        if run["dag_run_id"] == dag_run_id:
            dag_run = run
            break
    
    if not dag_run:
        raise HTTPException(status_code=404, detail="DAG run not found")
    
    # Create task instances
    for i, task_id in enumerate(tasks):
        state = TaskState.SUCCESS if dag_run["state"] == DagRunState.SUCCESS else TaskState.RUNNING
        if dag_run["state"] == DagRunState.FAILED and i == len(tasks) - 1:
            state = TaskState.FAILED
            
        task_instances.append({
            "task_id": task_id,
            "dag_id": dag_id,
            "dag_run_id": dag_run_id,
            "execution_date": dag_run["execution_date"],
            "start_date": dag_run["start_date"],
            "end_date": dag_run["end_date"] if state == TaskState.SUCCESS else None,
            "duration": random.uniform(1, 10) if state == TaskState.SUCCESS else None,
            "state": state,
            "try_number": 1,
            "max_tries": 3,
            "operator": "PythonOperator",
            "pool": "default_pool",
            "queue": "default"
        })
    
    return {
        "task_instances": task_instances,
        "total_entries": len(task_instances)
    }

# Additional endpoints for compatibility
@app.get("/api/v1/pools", dependencies=[Depends(verify_credentials)])
async def list_pools():
    """List pools."""
    return {
        "pools": [
            {
                "name": "default_pool",
                "slots": 128,
                "occupied_slots": random.randint(0, 64),
                "running_slots": random.randint(0, 32),
                "queued_slots": random.randint(0, 16),
                "open_slots": 64
            }
        ],
        "total_entries": 1
    }

@app.get("/api/v1/variables", dependencies=[Depends(verify_credentials)])
async def list_variables():
    """List Airflow variables."""
    return {
        "variables": [
            {"key": "dean_orchestration_url", "value": "http://localhost:8082"},
            {"key": "indexagent_url", "value": "http://localhost:8081"},
            {"key": "evolution_api_url", "value": "http://localhost:8083"}
        ],
        "total_entries": 3
    }

# Metrics endpoint
@app.get("/api/v1/metrics", dependencies=[Depends(verify_credentials)])
async def get_metrics():
    """Get Airflow metrics."""
    total_runs = sum(len(runs) for runs in data_store.dag_runs.values())
    successful_runs = sum(
        1 for runs in data_store.dag_runs.values() 
        for run in runs if run["state"] == DagRunState.SUCCESS
    )
    
    return {
        "dags_count": len(data_store.dags),
        "dags_running": len([d for d in data_store.dags.values() if not d["is_paused"]]),
        "dag_runs_total": total_runs,
        "dag_runs_successful": successful_runs,
        "dag_runs_failed": total_runs - successful_runs,
        "executor_slots_available": 16,
        "executor_slots_used": random.randint(0, 8)
    }

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize the service."""
    app.state.start_time = time.time()
    logger.info("Airflow stub started", port=8080)

if __name__ == "__main__":
    port = int(os.getenv("SERVICE_PORT", "8080"))
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