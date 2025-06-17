"""
Authenticated service pool for DEAN orchestration.

Extends the service pool with authentication support.
"""

import os
from typing import Optional
import structlog

from .auth_base import AuthenticatedServiceClient, TokenManager
from .service_adapters import ServicePool

# Configure logging
logger = structlog.get_logger(__name__)


class AuthenticatedIndexAgentClient(AuthenticatedServiceClient):
    """IndexAgent client with authentication."""
    
    async def list_agents(self, limit: int = 100, offset: int = 0):
        """List agents with pagination."""
        return await self.get("/agents", params={"limit": limit, "offset": offset})
    
    async def create_agent(self, agent_config: dict):
        """Create a new agent."""
        return await self.post("/agents", json=agent_config)
    
    async def get_agent(self, agent_id: str):
        """Get a specific agent."""
        return await self.get(f"/agents/{agent_id}")
    
    async def delete_agent(self, agent_id: str):
        """Delete an agent."""
        return await self.delete(f"/agents/{agent_id}")
    
    async def get_patterns(self, **params):
        """Get discovered patterns."""
        return await self.get("/patterns", params=params)
    
    async def search(self, query: dict):
        """Search for code patterns."""
        return await self.post("/search", json=query)
    
    async def get_metrics(self):
        """Get service metrics."""
        return await self.get("/metrics")


class AuthenticatedAirflowClient(AuthenticatedServiceClient):
    """Airflow client with authentication."""
    
    def __init__(self, *args, **kwargs):
        """Initialize with Airflow-specific auth."""
        super().__init__(*args, **kwargs)
        
        # Airflow uses basic auth for API
        self.airflow_username = os.getenv("AIRFLOW_USERNAME", "airflow")
        self.airflow_password = os.getenv("AIRFLOW_PASSWORD", "airflow")
        
        # Set basic auth header
        import base64
        credentials = f"{self.airflow_username}:{self.airflow_password}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        self._session.headers["Authorization"] = f"Basic {encoded_credentials}"
    
    async def list_dags(self, **params):
        """List DAGs."""
        return await self.get("/api/v1/dags", params=params)
    
    async def trigger_dag(self, dag_id: str, conf: dict = None):
        """Trigger a DAG run."""
        payload = {"conf": conf or {}}
        return await self.post(f"/api/v1/dags/{dag_id}/dagRuns", json=payload)
    
    async def get_dag_run(self, dag_id: str, dag_run_id: str):
        """Get DAG run status."""
        return await self.get(f"/api/v1/dags/{dag_id}/dagRuns/{dag_run_id}")


class AuthenticatedEvolutionClient(AuthenticatedServiceClient):
    """Evolution API client with authentication."""
    
    async def start_evolution(self, config: dict):
        """Start an evolution trial."""
        return await self.post("/evolution/start", json=config)
    
    async def get_trial_status(self, trial_id: str):
        """Get evolution trial status."""
        return await self.get(f"/evolution/{trial_id}/status")
    
    async def list_trials(self, **params):
        """List evolution trials."""
        return await self.get("/evolution/trials", params=params)
    
    async def get_patterns(self, **params):
        """Get discovered patterns."""
        return await self.get("/patterns", params=params)
    
    async def get_metrics(self):
        """Get evolution metrics."""
        return await self.get("/evolution/metrics")


class AuthenticatedServicePool(ServicePool):
    """Service pool with authentication support.
    
    Manages authenticated connections to all services with:
    - Centralized token management
    - Automatic token refresh
    - Service-specific authentication
    """
    
    def __init__(self):
        """Initialize authenticated service pool."""
        super().__init__()
        
        # Initialize token manager
        self.token_manager = TokenManager()
        
        # Service URLs from environment
        indexagent_url = os.getenv("INDEXAGENT_API_URL", "http://localhost:8081")
        airflow_url = os.getenv("AIRFLOW_API_URL", "http://localhost:8080")
        evolution_url = os.getenv("EVOLUTION_API_URL", "http://localhost:8083")
        auth_url = os.getenv("DEAN_ORCHESTRATION_URL", "http://localhost:8082")
        
        # Create authenticated clients
        self.indexagent = AuthenticatedIndexAgentClient(
            base_url=indexagent_url,
            service_name="indexagent",
            auth_endpoint=auth_url
        )
        
        self.airflow = AuthenticatedAirflowClient(
            base_url=airflow_url,
            service_name="airflow",
            auth_endpoint=auth_url
        )
        
        self.evolution = AuthenticatedEvolutionClient(
            base_url=evolution_url,
            service_name="evolution",
            auth_endpoint=auth_url
        )
        
        logger.info(
            "authenticated_service_pool_initialized",
            services={
                "indexagent": indexagent_url,
                "airflow": airflow_url,
                "evolution": evolution_url,
                "auth": auth_url
            }
        )
    
    async def authenticate(self, username: str, password: str) -> bool:
        """Authenticate and set tokens for all services.
        
        Args:
            username: Username
            password: Password
            
        Returns:
            True if authentication successful
        """
        # Authenticate with token manager
        token_response = await self.token_manager.authenticate_user(username, password)
        
        if token_response:
            # Set tokens for all services
            for service in [self.indexagent, self.evolution]:
                await service.set_auth_token(
                    token_response.access_token,
                    token_response.expires_in
                )
                service.refresh_token = token_response.refresh_token
            
            logger.info(
                "service_pool_authenticated",
                username=username
            )
            return True
        
        logger.error(
            "service_pool_authentication_failed",
            username=username
        )
        return False
    
    async def set_api_key(self, api_key: str):
        """Set API key for all services.
        
        Args:
            api_key: API key to use
        """
        for service in [self.indexagent, self.evolution]:
            await service.set_api_key(api_key)
        
        logger.info("api_key_set_for_all_services")
    
    async def refresh_tokens(self) -> bool:
        """Refresh tokens for all services.
        
        Returns:
            True if all refreshes successful
        """
        success = True
        
        for service_name, service in [
            ("indexagent", self.indexagent),
            ("evolution", self.evolution)
        ]:
            if not await service.refresh_auth_token():
                logger.error(
                    "token_refresh_failed",
                    service=service_name
                )
                success = False
        
        return success
    
    async def close(self):
        """Close all service connections."""
        await self.indexagent.close()
        await self.airflow.close()
        await self.evolution.close()
        
        logger.info("authenticated_service_pool_closed")


async def create_authenticated_service_pool(
    username: Optional[str] = None,
    password: Optional[str] = None,
    api_key: Optional[str] = None
) -> AuthenticatedServicePool:
    """Create and configure an authenticated service pool.
    
    Args:
        username: Username for authentication
        password: Password for authentication
        api_key: API key for authentication (alternative to username/password)
        
    Returns:
        Configured AuthenticatedServicePool
    """
    pool = AuthenticatedServicePool()
    
    # Authenticate if credentials provided
    if username and password:
        if not await pool.authenticate(username, password):
            logger.warning("service_pool_authentication_failed")
    elif api_key:
        await pool.set_api_key(api_key)
    else:
        # Try to get credentials from environment
        env_username = os.getenv("DEAN_USERNAME")
        env_password = os.getenv("DEAN_PASSWORD")
        env_api_key = os.getenv("DEAN_API_KEY")
        
        if env_username and env_password:
            await pool.authenticate(env_username, env_password)
        elif env_api_key:
            await pool.set_api_key(env_api_key)
        else:
            logger.warning("no_authentication_credentials_provided")
    
    return pool