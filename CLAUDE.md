# CLAUDE.md - DEAN Repository

This file provides repository-specific guidance for the DEAN orchestration system.

## Repository Context

DEAN (Distributed Evolutionary Agent Network) serves as the primary orchestration layer that coordinates multiple Claude Code instances as autonomous agents. This repository implements the central control plane that manages agent lifecycles, orchestrates workflows, and provides unified monitoring across the distributed system.

## CRITICAL: This is Part of a Distributed System

<distributed_system_warning>
⚠️ **WARNING: The DEAN system spans FOUR repositories** ⚠️

This repository contains ONLY the orchestration layer. Other components are located in:
- **IndexAgent**: Core agent logic, evolution algorithms (Port 8081)
- **infra**: Docker configs, database schemas, deployment scripts
- **airflow-hub**: DAGs, operators, workflow orchestration (Port 8080)

**Specification Documents Location**: DEAN/specifications/ (read-only)

Always check all repositories before implementing features!
</distributed_system_warning>

## Available MCP Tools

### remote_exec
- **Location**: `/Users/preston/dev/mcp-tools/remote_exec/remote_exec_launcher.sh`
- **Purpose**: Execute PowerShell commands on Windows deployment PC (10.7.0.2)
- **Usage**: The remote_exec tool allows execution of PowerShell scripts on the remote Windows deployment server
- **SSH Key**: `~/.ssh/claude_remote_exec`
- **Target**: `deployer@10.7.0.2`
- **Configuration**: MCP configuration is in `.mcp.json` in the project root

This tool is essential for automated deployment operations on the Windows production server.

## Critical Implementation Requirements

### NO MOCK IMPLEMENTATIONS

<implementation_standards>
When implementing any feature in this codebase, Claude Code MUST create actual, working code. The following are STRICTLY PROHIBITED:
- Mock implementations or stub functions presented as complete
- Placeholder code with TODO comments in "finished" work
- Simulated test results or hypothetical outputs
- Documentation of what "would" happen instead of what "does" happen
- Pseudocode or conceptual implementations claimed as functional

Every implementation MUST:
- Be fully functional and executable with proper error handling
- Work with actual services and dependencies
- Be tested with real commands showing actual output
- Include complete implementations of all code paths
</implementation_standards>

## DEAN-Specific Architecture

### Core Responsibilities
- **Agent Orchestration**: Managing lifecycle of Claude Code agent instances
- **Service Coordination**: Integrating IndexAgent (via https://github.com/mprestonsparks/IndexAgent.git), Airflow (via https://github.com/mprestonsparks/airflow-hub.git), and infrastructure services (via https://github.com/mprestonsparks/infra.git)
- **Authentication & Authorization**: Unified access control across the system
- **Health Monitoring**: Real-time status tracking via WebSocket connections
- **Resource Management**: Token allocation and budget enforcement for agents

### What This Repository Does NOT Contain
- **Agent Evolution Logic**: Located in IndexAgent/indexagent/agents/evolution/
- **DAG Definitions**: Located in airflow-hub/dags/dean/
- **Docker Configurations**: Located in infra/docker-compose.dean.yml
- **Database Schemas**: Located in infra/database/init_agent_evolution.sql

### Service Integration Requirements

<service_rules>
<rule context="api_communication">
All service communication MUST go through the ServicePool with circuit breakers.
Never make direct HTTP calls without proper error handling and retries.
</rule>

<rule context="health_checks">
Implement health check endpoints for all services following the pattern:
- Path: /health
- Response: {"status": "healthy", "version": "x.y.z", "services": {...}}
- Include dependency health in response
</rule>

<rule context="authentication">
All endpoints except /health require JWT authentication.
Use FastAPI dependency injection for auth validation.
Never expose internal service tokens in logs or responses.
</rule>
</service_rules>

### API Development Standards

```python
# REQUIRED: Complete implementation pattern for DEAN APIs
from fastapi import Depends, HTTPException
from typing import Optional

async def get_authenticated_agent(
    token: str = Depends(oauth2_scheme)
) -> Agent:
    """Full implementation with error handling"""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
        agent_id = payload.get("agent_id")
        if not agent_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        agent = await agent_service.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        return agent
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

## Project Structure

```
src/
├── auth/                 # JWT-based authentication system
├── dean_orchestration/   # Main FastAPI server entry point
├── integration/          # Service adapters with circuit breakers
│   ├── indexagent.py    # IndexAgent service client
│   ├── airflow.py       # Airflow DAG management
│   └── evolution.py     # Agent evolution API client
├── interfaces/          # User-facing interfaces
│   ├── cli/            # Command-line tools
│   └── websocket/      # Real-time monitoring
└── orchestration/       # Core workflow coordination
    ├── agent_manager.py # Agent lifecycle management
    └── token_economy.py # Resource allocation logic

specifications/           # System specification documents (read-only)
├── 1-software-design-document.md
├── 2-software-requirements-specification.md
├── 3-architectural-design-document.md
├── 4-test-plan.md
├── 5-user-documentation.md
└── 6-maintenance-documentation.md
```

## Testing Requirements

<testing_standards>
- Unit tests must cover service mocking scenarios
- Integration tests must use actual running services
- WebSocket tests must verify real-time event propagation
- Circuit breaker tests must validate fault tolerance
- Performance tests must measure actual latencies
</testing_standards>

## Common Commands

```bash
# Development
python -m dean_orchestration.server  # Start FastAPI server
pytest tests/ -v --cov=src          # Run tests with coverage
docker build -t dean-orchestration . # Build container

# Validation
curl http://localhost:8082/health    # Check service health
python -m dean_orchestration.cli agents list  # List active agents
docker-compose logs dean-orchestration -f     # Monitor logs
```

## Environment Configuration

```bash
# Required environment variables
DEAN_SERVER_HOST=0.0.0.0
DEAN_SERVER_PORT=8082
DEAN_SERVICE_API_KEY=<service-key>
JWT_SECRET_KEY=<secret-key>
DEAN_ENV=development

# Service dependencies
INDEXAGENT_URL=http://indexagent:8081
AIRFLOW_URL=http://airflow:8080
EVOLUTION_API_URL=http://agent-evolution:8090
REDIS_URL=redis://redis:6379
DATABASE_URL=postgresql://user:pass@postgres:5432/dean
```

## Error Handling Patterns

```python
# REQUIRED: Consistent error responses
class ErrorResponse(BaseModel):
    error: str
    detail: str
    timestamp: datetime
    request_id: str

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.__class__.__name__,
            detail=exc.detail,
            timestamp=datetime.utcnow(),
            request_id=request.headers.get("X-Request-ID", "unknown")
        ).dict()
    )
```

## Security Requirements

<security_rules>
- Implement rate limiting on all public endpoints
- Use role-based access control (RBAC) for agent permissions
- Sanitize all input data before processing
- Never log sensitive tokens or credentials
- Rotate JWT keys according to security policy
- Implement audit logging for all state changes
</security_rules>

