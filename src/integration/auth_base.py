"""
Authentication-aware base service client.

Extends the base service client with JWT and API key authentication support.
"""

import asyncio
from typing import Optional, Dict, Any, Union
from datetime import datetime, timedelta
import structlog

from .base import ServiceClient, ServiceError
from ..auth import TokenResponse, TokenRefreshRequest, get_auth_manager

# Configure logging
logger = structlog.get_logger(__name__)


class AuthenticationError(ServiceError):
    """Raised when authentication fails."""
    pass


class AuthenticatedServiceClient(ServiceClient):
    """Service client with authentication support.
    
    Extends the base ServiceClient with:
    - JWT token authentication
    - Automatic token refresh
    - API key authentication fallback
    - Authentication header management
    """
    
    def __init__(
        self,
        base_url: str,
        service_name: str,
        timeout: int = 30,
        max_retries: int = 3,
        pool_size: int = 10,
        # Authentication parameters
        auth_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        api_key: Optional[str] = None,
        auth_endpoint: Optional[str] = None,
        auto_refresh: bool = True
    ):
        """Initialize authenticated service client.
        
        Args:
            base_url: Base URL for the service
            service_name: Name of the service for logging
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            pool_size: Connection pool size
            auth_token: JWT access token
            refresh_token: JWT refresh token
            api_key: API key for fallback authentication
            auth_endpoint: URL for token refresh (if different from base)
            auto_refresh: Automatically refresh expired tokens
        """
        super().__init__(base_url, service_name, timeout, max_retries, pool_size)
        
        self.auth_token = auth_token
        self.refresh_token = refresh_token
        self.api_key = api_key
        self.auth_endpoint = auth_endpoint or base_url
        self.auto_refresh = auto_refresh
        self.token_expires_at: Optional[datetime] = None
        
        # Update session headers with authentication
        self._update_auth_headers()
        
    def _update_auth_headers(self):
        """Update session headers with current authentication."""
        if self.auth_token:
            self._session.headers['Authorization'] = f'Bearer {self.auth_token}'
        elif self.api_key:
            self._session.headers['X-API-Key'] = self.api_key
        else:
            # Remove auth headers if no credentials
            self._session.headers.pop('Authorization', None)
            self._session.headers.pop('X-API-Key', None)
    
    async def set_auth_token(self, token: str, expires_in: Optional[int] = None):
        """Set the authentication token.
        
        Args:
            token: JWT access token
            expires_in: Token expiration time in seconds
        """
        self.auth_token = token
        
        if expires_in:
            self.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        else:
            self.token_expires_at = None
            
        self._update_auth_headers()
        
        self.logger.info(
            "auth_token_updated",
            has_expiry=bool(expires_in)
        )
    
    async def set_api_key(self, api_key: str):
        """Set the API key for authentication.
        
        Args:
            api_key: API key
        """
        self.api_key = api_key
        self.auth_token = None  # Clear JWT if using API key
        self._update_auth_headers()
        
        self.logger.info("api_key_updated")
    
    async def refresh_auth_token(self) -> bool:
        """Refresh the authentication token.
        
        Returns:
            True if refresh successful, False otherwise
        """
        if not self.refresh_token:
            self.logger.warning("no_refresh_token_available")
            return False
            
        try:
            # Create refresh request
            refresh_request = TokenRefreshRequest(refresh_token=self.refresh_token)
            
            # Call auth endpoint
            async with self._session.post(
                f"{self.auth_endpoint}/auth/refresh",
                json=refresh_request.dict()
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    token_response = TokenResponse(**data)
                    
                    # Update tokens
                    self.auth_token = token_response.access_token
                    self.refresh_token = token_response.refresh_token
                    await self.set_auth_token(
                        token_response.access_token,
                        token_response.expires_in
                    )
                    
                    self.logger.info("token_refreshed_successfully")
                    return True
                else:
                    self.logger.error(
                        "token_refresh_failed",
                        status=response.status
                    )
                    return False
                    
        except Exception as e:
            self.logger.error(
                "token_refresh_error",
                error=str(e)
            )
            return False
    
    def _should_refresh_token(self) -> bool:
        """Check if token should be refreshed.
        
        Returns:
            True if token should be refreshed
        """
        if not self.auto_refresh or not self.auth_token or not self.refresh_token:
            return False
            
        if not self.token_expires_at:
            return False
            
        # Refresh if token expires in less than 5 minutes
        time_until_expiry = self.token_expires_at - datetime.utcnow()
        return time_until_expiry.total_seconds() < 300
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> Union[Dict[str, Any], list, None]:
        """Execute HTTP request with authentication handling.
        
        Overrides base _request to handle authentication:
        - Automatic token refresh
        - 401 response handling
        - Fallback to API key
        """
        # Check if token needs refresh
        if self._should_refresh_token():
            await self.refresh_auth_token()
        
        # First attempt
        try:
            return await super()._request(method, endpoint, **kwargs)
        except ServiceError as e:
            # Check if it's an authentication error
            if hasattr(e, 'details') and e.details.get('status') == 401:
                self.logger.warning(
                    "authentication_failed",
                    endpoint=endpoint
                )
                
                # Try to refresh token if we have a refresh token
                if self.refresh_token and await self.refresh_auth_token():
                    # Retry request with new token
                    self.logger.info("retrying_with_refreshed_token")
                    return await super()._request(method, endpoint, **kwargs)
                
                # If refresh failed or no refresh token, raise auth error
                raise AuthenticationError(
                    "Authentication failed",
                    self.service_name,
                    {"endpoint": endpoint, "method": method}
                )
            else:
                # Re-raise non-auth errors
                raise
    
    async def authenticate_with_credentials(
        self,
        username: str,
        password: str
    ) -> bool:
        """Authenticate using username and password.
        
        Args:
            username: Username
            password: Password
            
        Returns:
            True if authentication successful
        """
        try:
            response = await self._session.post(
                f"{self.auth_endpoint}/auth/login",
                json={"username": username, "password": password}
            )
            
            if response.status == 200:
                data = await response.json()
                token_response = TokenResponse(**data)
                
                # Store tokens
                self.auth_token = token_response.access_token
                self.refresh_token = token_response.refresh_token
                await self.set_auth_token(
                    token_response.access_token,
                    token_response.expires_in
                )
                
                self.logger.info(
                    "authenticated_successfully",
                    username=username
                )
                return True
            else:
                self.logger.error(
                    "authentication_failed",
                    username=username,
                    status=response.status
                )
                return False
                
        except Exception as e:
            self.logger.error(
                "authentication_error",
                username=username,
                error=str(e)
            )
            return False


class TokenManager:
    """Manages authentication tokens for multiple services.
    
    Centralizes token management for the service pool:
    - Stores tokens per service
    - Handles token refresh
    - Provides token to service clients
    """
    
    def __init__(self):
        """Initialize token manager."""
        self.tokens: Dict[str, Dict[str, Any]] = {}
        self.auth_manager = get_auth_manager()
        self.logger = logger.bind(component="token_manager")
    
    async def authenticate_user(self, username: str, password: str) -> Optional[TokenResponse]:
        """Authenticate user and store tokens.
        
        Args:
            username: Username
            password: Password
            
        Returns:
            TokenResponse if successful, None otherwise
        """
        from ..auth import UserCredentials
        
        credentials = UserCredentials(username=username, password=password)
        user = self.auth_manager.authenticate_user(credentials)
        
        if user:
            token_response = self.auth_manager.create_token_response(user)
            
            # Store tokens for all services
            self.tokens["global"] = {
                "access_token": token_response.access_token,
                "refresh_token": token_response.refresh_token,
                "expires_at": datetime.utcnow() + timedelta(seconds=token_response.expires_in),
                "user_id": user.id,
                "username": user.username,
                "roles": [r.value for r in user.roles]
            }
            
            self.logger.info(
                "user_authenticated",
                username=username,
                roles=self.tokens["global"]["roles"]
            )
            
            return token_response
        
        return None
    
    def get_token_for_service(self, service_name: str) -> Optional[str]:
        """Get authentication token for a service.
        
        Args:
            service_name: Name of the service
            
        Returns:
            Access token if available
        """
        # Check service-specific token first
        if service_name in self.tokens:
            return self.tokens[service_name].get("access_token")
        
        # Fall back to global token
        if "global" in self.tokens:
            return self.tokens["global"].get("access_token")
        
        return None
    
    def get_refresh_token_for_service(self, service_name: str) -> Optional[str]:
        """Get refresh token for a service.
        
        Args:
            service_name: Name of the service
            
        Returns:
            Refresh token if available
        """
        # Check service-specific token first
        if service_name in self.tokens:
            return self.tokens[service_name].get("refresh_token")
        
        # Fall back to global token
        if "global" in self.tokens:
            return self.tokens["global"].get("refresh_token")
        
        return None
    
    async def refresh_token_for_service(self, service_name: str) -> bool:
        """Refresh token for a service.
        
        Args:
            service_name: Name of the service
            
        Returns:
            True if refresh successful
        """
        refresh_token = self.get_refresh_token_for_service(service_name)
        if not refresh_token:
            return False
        
        try:
            from ..auth import TokenRefreshRequest
            
            refresh_request = TokenRefreshRequest(refresh_token=refresh_token)
            token_response = self.auth_manager.refresh_access_token(refresh_request)
            
            # Update stored tokens
            token_data = {
                "access_token": token_response.access_token,
                "refresh_token": token_response.refresh_token,
                "expires_at": datetime.utcnow() + timedelta(seconds=token_response.expires_in)
            }
            
            # Preserve other data if updating global token
            if service_name == "global" and "global" in self.tokens:
                token_data.update({
                    "user_id": self.tokens["global"].get("user_id"),
                    "username": self.tokens["global"].get("username"),
                    "roles": self.tokens["global"].get("roles")
                })
            
            self.tokens[service_name] = token_data
            
            self.logger.info(
                "token_refreshed",
                service=service_name
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "token_refresh_failed",
                service=service_name,
                error=str(e)
            )
            return False
    
    def clear_tokens(self):
        """Clear all stored tokens."""
        self.tokens.clear()
        self.logger.info("all_tokens_cleared")