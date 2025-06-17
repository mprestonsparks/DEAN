"""
Authentication middleware for FastAPI.
"""

from typing import Optional, List, Callable
from functools import wraps

from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.security.utils import get_authorization_scheme_param
import structlog

from .auth_models import User, UserRole, TokenData
from .auth_utils import verify_token, extract_token_from_header
from .auth_manager import get_auth_manager

# Configure logging
logger = structlog.get_logger()

# Security scheme
security = HTTPBearer(auto_error=False)


class AuthMiddleware:
    """Authentication middleware for FastAPI."""
    
    def __init__(self, auth_manager=None):
        """Initialize authentication middleware."""
        self.auth_manager = auth_manager or get_auth_manager()
    
    async def __call__(self, request: Request, call_next):
        """Process request with authentication."""
        # Skip authentication for certain paths
        if self._should_skip_auth(request.url.path):
            return await call_next(request)
        
        # Try to authenticate
        try:
            user = await self.authenticate_request(request)
            if user:
                # Add user to request state
                request.state.user = user
                logger.info("Request authenticated",
                          method=request.method,
                          path=request.url.path,
                          username=user.username,
                          roles=[r.value for r in user.roles])
            else:
                # No authentication provided for protected route
                logger.warning("Unauthenticated request to protected route",
                             method=request.method,
                             path=request.url.path)
        except HTTPException:
            # Authentication failed
            logger.warning("Authentication failed",
                         method=request.method,
                         path=request.url.path)
            raise
        except Exception as e:
            logger.error("Authentication error",
                        method=request.method,
                        path=request.url.path,
                        error=str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication error"
            )
        
        # Process request
        response = await call_next(request)
        return response
    
    def _should_skip_auth(self, path: str) -> bool:
        """Check if authentication should be skipped for a path."""
        # Public paths that don't require authentication
        public_paths = [
            "/health",
            "/api/health",
            "/docs",
            "/openapi.json",
            "/redoc",
            "/auth/login",
            "/auth/refresh",
            "/favicon.ico"
        ]
        
        return any(path.startswith(p) for p in public_paths)
    
    async def authenticate_request(self, request: Request) -> Optional[User]:
        """Authenticate a request using JWT or API key."""
        # Try JWT authentication first
        authorization = request.headers.get("Authorization")
        if authorization:
            user = await self._authenticate_jwt(authorization)
            if user:
                return user
        
        # Try API key authentication
        api_key = request.headers.get(self.auth_manager.config.api_key_header_name)
        if api_key and self.auth_manager.config.allow_api_key_auth:
            user = await self._authenticate_api_key(api_key)
            if user:
                return user
        
        return None
    
    async def _authenticate_jwt(self, authorization: str) -> Optional[User]:
        """Authenticate using JWT token."""
        token = extract_token_from_header(authorization)
        if not token:
            return None
        
        # Verify token
        token_data = verify_token(
            token,
            secret_key=self.auth_manager.config.jwt_secret_key,
            algorithm=self.auth_manager.config.jwt_algorithm,
            token_type="access"
        )
        
        if not token_data:
            return None
        
        # Get user
        user = self.auth_manager.get_user_by_id(token_data.user_id)
        if not user or not user.is_active:
            return None
        
        return user
    
    async def _authenticate_api_key(self, api_key: str) -> Optional[User]:
        """Authenticate using API key."""
        key_obj = self.auth_manager.validate_api_key(api_key)
        if not key_obj:
            return None
        
        # Create a pseudo-user for API key
        user = User(
            id=key_obj.key_id,
            username=f"api-key-{key_obj.name}",
            email=None,
            full_name=key_obj.name,
            roles=key_obj.roles,
            is_active=True,
            created_at=key_obj.created_at,
            last_login=key_obj.last_used
        )
        
        return user


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """Get the current authenticated user from JWT token."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    auth_manager = get_auth_manager()
    
    # Verify token
    token_data = verify_token(
        credentials.credentials,
        secret_key=auth_manager.config.jwt_secret_key,
        algorithm=auth_manager.config.jwt_algorithm,
        token_type="access"
    )
    
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user
    user = auth_manager.get_user_by_id(token_data.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    
    return user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[User]:
    """Get the current user if authenticated, otherwise None."""
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None


def require_auth(func: Callable) -> Callable:
    """Decorator to require authentication for a route."""
    @wraps(func)
    async def wrapper(*args, current_user: User = Depends(get_current_user), **kwargs):
        # Add user to kwargs if the function accepts it
        import inspect
        sig = inspect.signature(func)
        if "current_user" in sig.parameters:
            kwargs["current_user"] = current_user
        return await func(*args, **kwargs)
    return wrapper


def require_role(roles: List[UserRole]):
    """Decorator to require specific roles for a route."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, current_user: User = Depends(get_current_user), **kwargs):
            # Check if user has required role
            if not any(role in current_user.roles for role in roles):
                logger.warning("Access denied - insufficient roles",
                             username=current_user.username,
                             user_roles=[r.value for r in current_user.roles],
                             required_roles=[r.value for r in roles])
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions"
                )
            
            # Add user to kwargs if the function accepts it
            import inspect
            sig = inspect.signature(func)
            if "current_user" in sig.parameters:
                kwargs["current_user"] = current_user
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_api_key(func: Callable) -> Callable:
    """Decorator to require API key authentication."""
    @wraps(func)
    async def wrapper(
        request: Request,
        *args,
        **kwargs
    ):
        auth_manager = get_auth_manager()
        
        # Get API key from header
        api_key = request.headers.get(auth_manager.config.api_key_header_name)
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key required",
                headers={"WWW-Authenticate": "ApiKey"},
            )
        
        # Validate API key
        key_obj = auth_manager.validate_api_key(api_key)
        if not key_obj:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key"
            )
        
        # Add API key info to kwargs
        kwargs["api_key"] = key_obj
        
        return await func(*args, **kwargs)
    return wrapper