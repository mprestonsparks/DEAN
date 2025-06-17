"""Base service client implementation with common functionality."""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Union
from datetime import datetime
import aiohttp
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)
import structlog

# Configure structured logging
logger = structlog.get_logger(__name__)


class ServiceError(Exception):
    """Base exception for service-related errors."""
    
    def __init__(self, message: str, service: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.service = service
        self.details = details or {}
        self.timestamp = datetime.utcnow().isoformat()


class ServiceTimeout(ServiceError):
    """Raised when a service request times out."""
    pass


class ServiceConnectionError(ServiceError):
    """Raised when unable to connect to a service."""
    pass


class ServiceClient(ABC):
    """Abstract base class for service clients.
    
    Provides common functionality for all service integrations including:
    - Retry logic with exponential backoff
    - Connection pooling
    - Structured logging
    - Error handling
    - Health checking
    """
    
    def __init__(
        self,
        base_url: str,
        service_name: str,
        timeout: int = 30,
        max_retries: int = 3,
        pool_size: int = 10,
    ):
        """Initialize service client.
        
        Args:
            base_url: Base URL for the service
            service_name: Name of the service for logging
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            pool_size: Connection pool size
        """
        self.base_url = base_url.rstrip('/')
        self.service_name = service_name
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.max_retries = max_retries
        
        # Connection pool configuration
        connector = aiohttp.TCPConnector(
            limit=pool_size,
            limit_per_host=pool_size,
        )
        
        # Create session with default configuration
        self._session = aiohttp.ClientSession(
            connector=connector,
            timeout=self.timeout,
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json',
            }
        )
        
        self.logger = logger.bind(service=service_name)
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - close session."""
        await self.close()
    
    async def close(self):
        """Close the HTTP session."""
        await self._session.close()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> Union[Dict[str, Any], list, None]:
        """Execute HTTP request with retry logic.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (relative to base_url)
            **kwargs: Additional arguments for aiohttp request
            
        Returns:
            Parsed JSON response or None
            
        Raises:
            ServiceTimeout: On request timeout
            ServiceConnectionError: On connection failure
            ServiceError: On other errors
        """
        url = f"{self.base_url}{endpoint}"
        
        self.logger.debug(
            "service_request",
            method=method,
            url=url,
            kwargs=kwargs,
        )
        
        try:
            async with self._session.request(method, url, **kwargs) as response:
                response_data = None
                if response.content_type == 'application/json':
                    response_data = await response.json()
                
                self.logger.debug(
                    "service_response",
                    status=response.status,
                    response_data=response_data,
                )
                
                if response.status >= 400:
                    error_msg = f"{self.service_name} returned {response.status}"
                    if response_data and isinstance(response_data, dict):
                        error_msg = response_data.get('message', error_msg)
                    
                    raise ServiceError(
                        error_msg,
                        self.service_name,
                        {
                            'status_code': response.status,
                            'response': response_data,
                        }
                    )
                
                return response_data
                
        except asyncio.TimeoutError as e:
            self.logger.error("service_timeout", url=url)
            raise ServiceTimeout(
                f"Request to {self.service_name} timed out",
                self.service_name,
                {'url': url}
            ) from e
            
        except aiohttp.ClientConnectionError as e:
            self.logger.error("service_connection_error", url=url, error=str(e))
            raise ServiceConnectionError(
                f"Failed to connect to {self.service_name}",
                self.service_name,
                {'url': url, 'error': str(e)}
            ) from e
            
        except aiohttp.ClientError as e:
            self.logger.error("service_client_error", url=url, error=str(e))
            raise ServiceError(
                f"Error communicating with {self.service_name}",
                self.service_name,
                {'url': url, 'error': str(e)}
            ) from e
    
    async def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Execute GET request."""
        return await self._request('GET', endpoint, params=params)
    
    async def post(self, endpoint: str, json: Optional[Dict[str, Any]] = None) -> Any:
        """Execute POST request."""
        return await self._request('POST', endpoint, json=json)
    
    async def put(self, endpoint: str, json: Optional[Dict[str, Any]] = None) -> Any:
        """Execute PUT request."""
        return await self._request('PUT', endpoint, json=json)
    
    async def patch(self, endpoint: str, json: Optional[Dict[str, Any]] = None) -> Any:
        """Execute PATCH request."""
        return await self._request('PATCH', endpoint, json=json)
    
    async def delete(self, endpoint: str) -> Any:
        """Execute DELETE request."""
        return await self._request('DELETE', endpoint)
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Check service health.
        
        Returns:
            Health status dictionary
        """
        pass
    
    async def validate_connection(self) -> bool:
        """Validate service connection.
        
        Returns:
            True if service is reachable and healthy
        """
        try:
            health = await self.health_check()
            return health.get('status') == 'healthy'
        except Exception:
            return False