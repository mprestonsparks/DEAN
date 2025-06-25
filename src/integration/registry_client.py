"""Service Registry Client for DEAN services to self-register.

This module provides a client that services can use to register themselves
with the DEAN orchestration service registry.
"""

import asyncio
import socket
import httpx
import logging
from typing import Optional, Dict, List, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class ServiceRegistryClient:
    """Client for services to interact with the DEAN service registry."""
    
    def __init__(
        self,
        registry_url: str,
        service_name: str,
        service_port: int,
        service_version: str,
        service_host: Optional[str] = None,
        api_key: Optional[str] = None,
        heartbeat_interval: float = 25.0
    ):
        """Initialize registry client.
        
        Args:
            registry_url: Base URL of DEAN orchestration server
            service_name: Name of this service
            service_port: Port this service is running on
            service_version: Version of this service
            service_host: Hostname (auto-detected if not provided)
            api_key: API key for authentication
            heartbeat_interval: Seconds between heartbeats
        """
        self.registry_url = registry_url.rstrip('/')
        self.service_name = service_name
        self.service_port = service_port
        self.service_version = service_version
        self.service_host = service_host or self._get_hostname()
        self.api_key = api_key
        self.heartbeat_interval = heartbeat_interval
        
        self._http_client: Optional[httpx.AsyncClient] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._running = False
        
    def _get_hostname(self) -> str:
        """Get hostname of current machine."""
        try:
            # Try to get the hostname that's accessible from other containers
            hostname = socket.gethostname()
            # In Docker, this might be the container ID, so try to get IP
            try:
                # Get IP address
                import subprocess
                result = subprocess.run(
                    ['hostname', '-i'],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                if result.returncode == 0:
                    return result.stdout.strip().split()[0]
            except:
                pass
            return hostname
        except:
            return "localhost"
            
    async def start(
        self,
        metadata: Optional[Dict[str, Any]] = None,
        health_endpoint: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Start the registry client and register with DEAN.
        
        Args:
            metadata: Service metadata (type, capabilities, etc.)
            health_endpoint: Health check endpoint configuration
            
        Returns:
            True if registration successful
        """
        if self._running:
            return True
            
        self._http_client = httpx.AsyncClient(timeout=10.0)
        
        # Prepare headers
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
            
        # Register with the registry
        try:
            registration_data = {
                "name": self.service_name,
                "host": self.service_host,
                "port": self.service_port,
                "version": self.service_version
            }
            
            if metadata:
                registration_data["metadata"] = metadata
                
            if health_endpoint:
                registration_data["health_endpoint"] = health_endpoint
            else:
                # Default health endpoint
                registration_data["health_endpoint"] = {
                    "protocol": "http",
                    "path": "/health",
                    "timeout": 5.0,
                    "method": "GET"
                }
                
            response = await self._http_client.post(
                f"{self.registry_url}/api/v1/registry/register",
                json=registration_data,
                headers=headers
            )
            
            if response.status_code == 200:
                self._running = True
                # Start heartbeat task
                self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
                logger.info(f"Successfully registered service '{self.service_name}' with DEAN")
                return True
            else:
                logger.error(
                    f"Failed to register service: {response.status_code} - {response.text}"
                )
                return False
                
        except Exception as e:
            logger.error(f"Failed to register with DEAN: {e}")
            return False
            
    async def stop(self) -> None:
        """Stop the registry client and deregister from DEAN."""
        if not self._running:
            return
            
        self._running = False
        
        # Cancel heartbeat task
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
                
        # Deregister from DEAN
        try:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
                
            response = await self._http_client.delete(
                f"{self.registry_url}/api/v1/registry/services/{self.service_name}",
                headers=headers
            )
            
            if response.status_code == 200:
                logger.info(f"Successfully deregistered service '{self.service_name}'")
            else:
                logger.warning(
                    f"Failed to deregister service: {response.status_code}"
                )
                
        except Exception as e:
            logger.error(f"Error during deregistration: {e}")
            
        # Close HTTP client
        if self._http_client:
            await self._http_client.aclose()
            
    async def update_metadata(self, metadata: Dict[str, Any]) -> bool:
        """Update service metadata in the registry.
        
        Args:
            metadata: Updated metadata
            
        Returns:
            True if update successful
        """
        if not self._running:
            logger.warning("Registry client not running")
            return False
            
        try:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
                
            response = await self._http_client.patch(
                f"{self.registry_url}/api/v1/registry/services/{self.service_name}/metadata",
                json=metadata,
                headers=headers
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Failed to update metadata: {e}")
            return False
            
    async def discover_service(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Discover another service by name.
        
        Args:
            service_name: Name of service to discover
            
        Returns:
            Service info if found
        """
        try:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
                
            response = await self._http_client.get(
                f"{self.registry_url}/api/v1/registry/services/{service_name}",
                headers=headers
            )
            
            if response.status_code == 200:
                return response.json()
            return None
            
        except Exception as e:
            logger.error(f"Failed to discover service '{service_name}': {e}")
            return None
            
    async def discover_services_by_type(self, service_type: str) -> List[Dict[str, Any]]:
        """Discover services by type.
        
        Args:
            service_type: Type of services to find
            
        Returns:
            List of matching services
        """
        try:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
                
            response = await self._http_client.get(
                f"{self.registry_url}/api/v1/registry/services",
                params={"type": service_type},
                headers=headers
            )
            
            if response.status_code == 200:
                return response.json().get("services", [])
            return []
            
        except Exception as e:
            logger.error(f"Failed to discover services by type '{service_type}': {e}")
            return []
            
    async def get_service_url(self, service_name: str) -> Optional[str]:
        """Get the base URL for a service.
        
        Args:
            service_name: Name of service
            
        Returns:
            Service base URL if found
        """
        service_info = await self.discover_service(service_name)
        if service_info:
            host = service_info.get("host")
            port = service_info.get("port")
            protocol = service_info.get("health_endpoint", {}).get("protocol", "http")
            return f"{protocol}://{host}:{port}"
        return None
        
    async def call_service(
        self,
        service_name: str,
        endpoint: str,
        method: str = "GET",
        **kwargs
    ) -> Optional[httpx.Response]:
        """Call another service through the registry.
        
        Args:
            service_name: Name of service to call
            endpoint: API endpoint path
            method: HTTP method
            **kwargs: Additional arguments for request
            
        Returns:
            HTTP response if successful
        """
        try:
            # Get service URL
            base_url = await self.get_service_url(service_name)
            if not base_url:
                logger.error(f"Service '{service_name}' not found")
                return None
                
            # Make request
            url = f"{base_url}{endpoint}"
            response = await self._http_client.request(method, url, **kwargs)
            return response
            
        except Exception as e:
            logger.error(f"Failed to call service '{service_name}': {e}")
            return None
            
    async def _heartbeat_loop(self) -> None:
        """Send periodic heartbeats to maintain registration."""
        while self._running:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                
                # Send heartbeat
                headers = {}
                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"
                    
                response = await self._http_client.post(
                    f"{self.registry_url}/api/v1/registry/services/{self.service_name}/heartbeat",
                    headers=headers
                )
                
                if response.status_code != 200:
                    logger.warning(
                        f"Heartbeat failed: {response.status_code} - {response.text}"
                    )
                    # Re-register if heartbeat fails
                    await self.start()
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
                await asyncio.sleep(5)  # Brief pause before retrying
                

class ServiceRegistryContextManager:
    """Context manager for automatic service registration/deregistration."""
    
    def __init__(self, *args, **kwargs):
        """Initialize with same arguments as ServiceRegistryClient."""
        self.client = ServiceRegistryClient(*args, **kwargs)
        self.metadata = kwargs.get('metadata')
        self.health_endpoint = kwargs.get('health_endpoint')
        
    async def __aenter__(self) -> ServiceRegistryClient:
        """Register service on enter."""
        await self.client.start(
            metadata=self.metadata,
            health_endpoint=self.health_endpoint
        )
        return self.client
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Deregister service on exit."""
        await self.client.stop()
        

def create_registry_client(
    service_name: str,
    service_port: int,
    service_version: str,
    registry_url: Optional[str] = None,
    **kwargs
) -> ServiceRegistryClient:
    """Factory function to create a registry client.
    
    Args:
        service_name: Name of the service
        service_port: Port the service runs on
        service_version: Service version
        registry_url: DEAN orchestration URL (from env if not provided)
        **kwargs: Additional arguments for ServiceRegistryClient
        
    Returns:
        ServiceRegistryClient instance
    """
    import os
    
    registry_url = registry_url or os.getenv(
        "DEAN_ORCHESTRATION_URL",
        "http://dean-orchestration:8082"
    )
    
    return ServiceRegistryClient(
        registry_url=registry_url,
        service_name=service_name,
        service_port=service_port,
        service_version=service_version,
        **kwargs
    )