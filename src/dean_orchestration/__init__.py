"""DEAN Orchestration - Distributed Evolutionary Agent Network Orchestration Layer.

This package provides orchestration capabilities for the DEAN system,
coordinating between IndexAgent, Airflow, and infrastructure services.
"""

__version__ = "0.1.0"
__author__ = "DEAN Development Team"

# Import main components for easier access
from ..orchestration.deployment.system_deployer import SystemDeployer
from ..orchestration.coordination.evolution_trial import EvolutionTrialCoordinator
from ..integration.service_adapters import ServicePool, create_service_pool

__all__ = [
    "SystemDeployer",
    "EvolutionTrialCoordinator", 
    "ServicePool",
    "create_service_pool",
    "__version__",
]