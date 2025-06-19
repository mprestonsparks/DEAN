# CLAUDE.md - DEAN Repository

This file provides repository-specific guidance for the DEAN orchestration system.

## Repository Purpose
DEAN serves as the primary orchestration layer for the distributed agent evolution system, providing:
- Unified authentication and authorization
- Service coordination and health monitoring
- Workflow orchestration across services
- Real-time monitoring via WebSocket

## Critical Implementation Requirements

### NO MOCK IMPLEMENTATIONS

When implementing any feature in this codebase, Claude Code MUST create actual, working code. The following are STRICTLY PROHIBITED:
- Mock implementations or stub functions presented as complete
- Placeholder code with TODO comments in "finished" work
- Simulated test results or hypothetical outputs
- Documentation of what "would" happen instead of what "does" happen
- Pseudocode or conceptual implementations claimed as functional

### REAL CODE ONLY

Every implementation in this project MUST:
- Be fully functional and executable with proper error handling
- Work with actual services and dependencies
- Be tested with real commands showing actual output
- Include complete implementations of all code paths

## DEAN-Specific Guidelines

### Service Integration
- All service communication must go through the ServicePool
- Use circuit breakers for fault tolerance
- Implement health checks for all external services
- Log all service interactions for debugging

### API Development
- All endpoints must have authentication (except /health)
- Use FastAPI dependency injection for services
- Implement proper error responses with status codes
- Include request validation using Pydantic models

### Testing Requirements
- Test service integration with actual running services
- Verify WebSocket functionality with real connections
- Test authentication flows end-to-end
- Validate circuit breaker behavior

## Common Commands
- Start server: `python -m dean_orchestration.server`
- Run tests: `pytest tests/ -v`
- Check health: `curl http://localhost:8082/health`
- Build Docker image: `docker build -t dean-orchestration .`

## Project Structure
```
src/
├── auth/                 # Authentication system
├── dean_orchestration/   # Main server entry point
├── integration/          # Service adapters and clients
├── interfaces/          # CLI and web interfaces
└── orchestration/       # Workflow coordination
```

## Service Dependencies
- PostgreSQL: Connection pool for authentication data
- Redis: Session management and caching
- External Services: IndexAgent, Airflow, Evolution API

## Environment Variables
```bash
DEAN_SERVER_HOST=0.0.0.0
DEAN_SERVER_PORT=8082
DEAN_SERVICE_API_KEY=your-service-key
JWT_SECRET_KEY=your-secret-key
DEAN_ENV=development
```

## Error Handling
- Use HTTPException for API errors
- Log all errors with context
- Return consistent error response format
- Implement retry logic for external services

## Security Requirements
- All endpoints require authentication except /health
- Use JWT tokens with expiration
- Implement role-based access control
- Validate all input data
- Never log sensitive information