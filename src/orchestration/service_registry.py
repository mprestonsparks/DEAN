"""Service Registry for DEAN orchestration system.

This module provides service discovery, health monitoring, and circuit breaker
integration for managing the distributed DEAN system services.
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Any, Set, Callable
from datetime import datetime, timedelta
from enum import Enum
import logging
import httpx
import redis.asyncio as redis
from dataclasses import dataclass, asdict, field
from prometheus_client import Counter, Gauge, Histogram

from .circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitBreakerRegistry

logger = logging.getLogger(__name__)

# Prometheus metrics
service_health_gauge = Gauge(
    'dean_service_health',
    'Service health status (1=healthy, 0=unhealthy)',
    ['service_name']
)
circuit_breaker_state = Gauge(
    'dean_circuit_breaker_state',
    'Circuit breaker state (0=closed, 1=open, 2=half-open)',
    ['service_name']
)
health_check_duration = Histogram(
    'dean_health_check_duration_seconds',
    'Duration of health check requests',
    ['service_name']
)
service_registration_total = Counter(
    'dean_service_registration_total',
    'Total number of service registrations',
    ['service_name']
)


class ServiceStatus(Enum):
    """Service health status."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
    DEGRADED = "degraded"


@dataclass
class ServiceEndpoint:
    """Service endpoint configuration."""
    protocol: str = "http"  # http, https, grpc
    path: str = "/health"
    timeout: float = 5.0
    method: str = "GET"


@dataclass
class ServiceMetadata:
    """Service metadata and capabilities."""
    service_type: str
    api_version: str
    endpoints: Dict[str, str] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class ServiceInfo:
    """Complete service information."""
    name: str
    host: str
    port: int
    version: str
    status: ServiceStatus = ServiceStatus.UNKNOWN
    metadata: Optional[ServiceMetadata] = None
    health_endpoint: Optional[ServiceEndpoint] = None
    last_health_check: Optional[datetime] = None
    last_error: Optional[str] = None
    registration_time: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def base_url(self) -> str:
        """Get base URL for service."""
        protocol = self.health_endpoint.protocol if self.health_endpoint else "http"
        return f"{protocol}://{self.host}:{self.port}"
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data['status'] = self.status.value
        if self.last_health_check:
            data['last_health_check'] = self.last_health_check.isoformat()
        data['registration_time'] = self.registration_time.isoformat()
        return data
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ServiceInfo':
        """Create from dictionary."""
        data = data.copy()
        data['status'] = ServiceStatus(data.get('status', 'unknown'))
        if data.get('last_health_check'):
            data['last_health_check'] = datetime.fromisoformat(data['last_health_check'])
        if data.get('registration_time'):
            data['registration_time'] = datetime.fromisoformat(data['registration_time'])
        if data.get('metadata'):
            data['metadata'] = ServiceMetadata(**data['metadata'])
        if data.get('health_endpoint'):
            data['health_endpoint'] = ServiceEndpoint(**data['health_endpoint'])
        return cls(**data)


class ServiceRegistry:
    """Service registry with health monitoring and circuit breaker integration."""
    
    def __init__(
        self,
        redis_url: Optional[str] = None,
        health_check_interval: float = 30.0,
        enable_persistence: bool = True
    ):
        """Initialize service registry.
        
        Args:
            redis_url: Redis connection URL for persistence
            health_check_interval: Seconds between health checks
            enable_persistence: Enable Redis persistence
        """
        self._services: Dict[str, ServiceInfo] = {}
        self._circuit_breakers = CircuitBreakerRegistry()
        self._health_check_interval = health_check_interval
        self._enable_persistence = enable_persistence
        self._redis_url = redis_url
        self._redis: Optional[redis.Redis] = None
        self._health_check_task: Optional[asyncio.Task] = None
        self._running = False
        self._lock = asyncio.Lock()
        self._http_client: Optional[httpx.AsyncClient] = None
        
    async def start(self) -> None:
        """Start the service registry and health monitoring."""
        if self._running:
            return
            
        self._running = True
        self._http_client = httpx.AsyncClient(timeout=10.0)
        
        # Initialize Redis connection if persistence is enabled
        if self._enable_persistence and self._redis_url:
            try:
                self._redis = redis.from_url(self._redis_url)
                await self._redis.ping()
                await self._load_from_redis()
                logger.info("Connected to Redis for service registry persistence")
            except Exception as e:
                logger.warning(f"Redis connection failed, continuing without persistence: {e}")
                self._redis = None
                
        # Start health check task
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        logger.info("Service registry started")
        
    async def stop(self) -> None:
        """Stop the service registry."""
        self._running = False
        
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
                
        if self._http_client:
            await self._http_client.aclose()
            
        if self._redis:
            await self._redis.close()
            
        logger.info("Service registry stopped")
        
    async def register_service(
        self,
        name: str,
        host: str,
        port: int,
        version: str,
        metadata: Optional[ServiceMetadata] = None,
        health_endpoint: Optional[ServiceEndpoint] = None
    ) -> ServiceInfo:
        """Register a new service or update existing one.
        
        Args:
            name: Service name
            host: Service host
            port: Service port
            version: Service version
            metadata: Service metadata and capabilities
            health_endpoint: Health check endpoint configuration
            
        Returns:
            ServiceInfo object
        """
        async with self._lock:
            service = ServiceInfo(
                name=name,
                host=host,
                port=port,
                version=version,
                metadata=metadata,
                health_endpoint=health_endpoint or ServiceEndpoint()
            )
            
            self._services[name] = service
            service_registration_total.labels(service_name=name).inc()
            
            # Create circuit breaker for this service
            await self._circuit_breakers.register(
                name,
                CircuitBreakerConfig(
                    failure_threshold=3,
                    success_threshold=2,
                    timeout=60.0
                ),
                self._on_circuit_breaker_state_change
            )
            
            # Persist to Redis
            await self._persist_service(name, service)
            
            # Perform initial health check
            asyncio.create_task(self._check_service_health(name))
            
            logger.info(f"Registered service: {name} at {host}:{port}")
            return service
            
    async def deregister_service(self, name: str) -> bool:
        """Remove a service from the registry.
        
        Args:
            name: Service name to remove
            
        Returns:
            True if removed, False if not found
        """
        async with self._lock:
            if name in self._services:
                del self._services[name]
                
                # Remove from Redis
                if self._redis:
                    try:
                        await self._redis.hdel("dean:services", name)
                    except Exception as e:
                        logger.error(f"Failed to remove service from Redis: {e}")
                        
                logger.info(f"Deregistered service: {name}")
                return True
            return False
            
    async def discover_service(self, name: str) -> Optional[ServiceInfo]:
        """Discover a service by name.
        
        Args:
            name: Service name
            
        Returns:
            ServiceInfo if found, None otherwise
        """
        return self._services.get(name)
        
    async def discover_services_by_type(self, service_type: str) -> List[ServiceInfo]:
        """Discover services by type.
        
        Args:
            service_type: Service type to filter by
            
        Returns:
            List of matching services
        """
        return [
            service for service in self._services.values()
            if service.metadata and service.metadata.service_type == service_type
        ]
        
    async def discover_services_by_capability(self, capability: str) -> List[ServiceInfo]:
        """Discover services by capability.
        
        Args:
            capability: Required capability
            
        Returns:
            List of services with the capability
        """
        return [
            service for service in self._services.values()
            if service.metadata and capability in service.metadata.capabilities
        ]
        
    async def get_service_status(self, name: str) -> Optional[ServiceStatus]:
        """Get current status of a service.
        
        Args:
            name: Service name
            
        Returns:
            ServiceStatus if found, None otherwise
        """
        service = self._services.get(name)
        return service.status if service else None
        
    async def get_all_services(self) -> Dict[str, ServiceInfo]:
        """Get all registered services.
        
        Returns:
            Dictionary of all services
        """
        return self._services.copy()
        
    async def get_healthy_services(self) -> List[ServiceInfo]:
        """Get all healthy services.
        
        Returns:
            List of healthy services
        """
        return [
            service for service in self._services.values()
            if service.status == ServiceStatus.HEALTHY
        ]
        
    async def call_service(
        self,
        name: str,
        endpoint: str,
        method: str = "GET",
        **kwargs
    ) -> httpx.Response:
        """Call a service through its circuit breaker.
        
        Args:
            name: Service name
            endpoint: API endpoint path
            method: HTTP method
            **kwargs: Additional arguments for httpx request
            
        Returns:
            HTTP response
            
        Raises:
            ServiceNotFoundError: If service not registered
            CircuitBreakerError: If circuit is open
        """
        service = self._services.get(name)
        if not service:
            raise ServiceNotFoundError(f"Service '{name}' not found")
            
        circuit_breaker = self._circuit_breakers.get(name)
        if not circuit_breaker:
            raise RuntimeError(f"No circuit breaker for service '{name}'")
            
        url = f"{service.base_url}{endpoint}"
        
        async def make_request():
            return await self._http_client.request(method, url, **kwargs)
            
        return await circuit_breaker.call(make_request)
        
    async def _health_check_loop(self) -> None:
        """Background task for periodic health checks."""
        while self._running:
            try:
                # Check all services
                tasks = [
                    self._check_service_health(name)
                    for name in list(self._services.keys())
                ]
                await asyncio.gather(*tasks, return_exceptions=True)
                
                # Wait for next interval
                await asyncio.sleep(self._health_check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                await asyncio.sleep(5)  # Brief pause before retrying
                
    async def _check_service_health(self, name: str) -> None:
        """Check health of a specific service."""
        service = self._services.get(name)
        if not service:
            return
            
        start_time = time.time()
        
        try:
            # Perform health check
            health_url = f"{service.base_url}{service.health_endpoint.path}"
            
            response = await self._http_client.request(
                service.health_endpoint.method,
                health_url,
                timeout=service.health_endpoint.timeout
            )
            
            # Check response
            if response.status_code == 200:
                health_data = response.json()
                if health_data.get("status") == "healthy":
                    await self._update_service_status(name, ServiceStatus.HEALTHY)
                else:
                    await self._update_service_status(
                        name,
                        ServiceStatus.DEGRADED,
                        f"Service reported: {health_data.get('status', 'unknown')}"
                    )
            else:
                await self._update_service_status(
                    name,
                    ServiceStatus.UNHEALTHY,
                    f"Health check returned {response.status_code}"
                )
                
        except httpx.TimeoutException:
            await self._update_service_status(
                name,
                ServiceStatus.UNHEALTHY,
                "Health check timeout"
            )
        except Exception as e:
            await self._update_service_status(
                name,
                ServiceStatus.UNHEALTHY,
                f"Health check failed: {str(e)}"
            )
        finally:
            # Record metrics
            duration = time.time() - start_time
            health_check_duration.labels(service_name=name).observe(duration)
            
    async def _update_service_status(
        self,
        name: str,
        status: ServiceStatus,
        error: Optional[str] = None
    ) -> None:
        """Update service status and metrics."""
        async with self._lock:
            service = self._services.get(name)
            if not service:
                return
                
            service.status = status
            service.last_health_check = datetime.utcnow()
            service.last_error = error
            
            # Update metrics
            service_health_gauge.labels(service_name=name).set(
                1 if status == ServiceStatus.HEALTHY else 0
            )
            
            # Persist to Redis
            await self._persist_service(name, service)
            
    def _on_circuit_breaker_state_change(
        self,
        name: str,
        old_state: Any,
        new_state: Any
    ) -> None:
        """Handle circuit breaker state changes."""
        # Map states to numeric values for Prometheus
        state_map = {"closed": 0, "open": 1, "half_open": 2}
        numeric_state = state_map.get(new_state.value, -1)
        circuit_breaker_state.labels(service_name=name).set(numeric_state)
        
        logger.info(f"Circuit breaker for '{name}' changed: {old_state.value} -> {new_state.value}")
        
    async def _persist_service(self, name: str, service: ServiceInfo) -> None:
        """Persist service info to Redis."""
        if not self._redis:
            return
            
        try:
            service_data = json.dumps(service.to_dict())
            await self._redis.hset("dean:services", name, service_data)
        except Exception as e:
            logger.error(f"Failed to persist service to Redis: {e}")
            
    async def _load_from_redis(self) -> None:
        """Load services from Redis on startup."""
        if not self._redis:
            return
            
        try:
            services_data = await self._redis.hgetall("dean:services")
            for name, data in services_data.items():
                try:
                    service_dict = json.loads(data)
                    service = ServiceInfo.from_dict(service_dict)
                    self._services[name.decode()] = service
                    
                    # Create circuit breaker
                    await self._circuit_breakers.register(
                        name.decode(),
                        CircuitBreakerConfig(),
                        self._on_circuit_breaker_state_change
                    )
                except Exception as e:
                    logger.error(f"Failed to load service '{name}' from Redis: {e}")
                    
            logger.info(f"Loaded {len(self._services)} services from Redis")
            
        except Exception as e:
            logger.error(f"Failed to load services from Redis: {e}")
            
    def get_metrics(self) -> Dict[str, Any]:
        """Get registry metrics for monitoring."""
        return {
            "total_services": len(self._services),
            "healthy_services": len([s for s in self._services.values() if s.status == ServiceStatus.HEALTHY]),
            "unhealthy_services": len([s for s in self._services.values() if s.status == ServiceStatus.UNHEALTHY]),
            "circuit_breakers": self._circuit_breakers.get_all_metrics()
        }


class ServiceNotFoundError(Exception):
    """Raised when a requested service is not found."""
    pass