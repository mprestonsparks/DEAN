"""Service integration layer for DEAN orchestration.

This module provides client implementations for integrating with external services:
- IndexAgent API (Port 8081)
- Airflow API (Port 8080)  
- Evolution API (Port 8090)
- Infrastructure services (PostgreSQL, Redis)
"""

from .base import ServiceClient, ServiceError, ServiceTimeout, ServiceConnectionError
from .indexagent_client import IndexAgentClient
from .airflow_client import AirflowClient
from .infra_client import EvolutionAPIClient, InfrastructureClient
from .service_adapters import ServicePool, create_service_pool
from .auth_base import AuthenticatedServiceClient, TokenManager
from .auth_service_pool import AuthenticatedServicePool, create_authenticated_service_pool

__all__ = [
    "ServiceClient",
    "ServiceError", 
    "ServiceTimeout",
    "ServiceConnectionError",
    "IndexAgentClient",
    "AirflowClient",
    "EvolutionAPIClient",
    "InfrastructureClient",
    "ServicePool",
    "create_service_pool",
    # Authentication-aware versions
    "AuthenticatedServiceClient",
    "TokenManager",
    "AuthenticatedServicePool",
    "create_authenticated_service_pool",
]