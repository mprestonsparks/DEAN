"""
Authentication manager for DEAN orchestration system.
"""

import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from uuid import uuid4

import structlog
from fastapi import HTTPException, status

from .auth_models import (
    User, UserRole, UserCredentials, TokenResponse,
    TokenRefreshRequest, APIKey, AuthConfig
)
from .auth_utils import (
    hash_password, verify_password, create_access_token,
    create_refresh_token, verify_token, create_token_response,
    generate_api_key, hash_api_key, verify_api_key
)

# Configure logging
logger = structlog.get_logger()


class AuthManager:
    """Manages authentication and user operations."""
    
    def __init__(self, config: Optional[AuthConfig] = None):
        """Initialize authentication manager."""
        self.config = config or self._get_default_config()
        
        # In-memory user store for development
        # In production, this should be replaced with a database
        self.users: Dict[str, Dict[str, Any]] = {}
        self.api_keys: Dict[str, APIKey] = {}
        self.refresh_tokens: Dict[str, Dict[str, Any]] = {}  # Track refresh tokens
        self.failed_attempts: Dict[str, List[datetime]] = {}  # Track failed login attempts
        
        # Initialize default users
        self._initialize_default_users()
        
        logger.info("AuthManager initialized", 
                   users_count=len(self.users),
                   api_keys_count=len(self.api_keys))
    
    def _get_default_config(self) -> AuthConfig:
        """Get default authentication configuration."""
        return AuthConfig(
            jwt_secret_key=os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production"),
            jwt_algorithm="HS256",
            access_token_expire_minutes=30,
            refresh_token_expire_days=7,
            password_min_length=6,
            max_login_attempts=5,
            lockout_duration_minutes=15
        )
    
    def _initialize_default_users(self):
        """Initialize default users for development."""
        default_users = [
            {
                "username": "admin",
                "password": "admin123",
                "roles": [UserRole.ADMIN],
                "full_name": "Admin User",
                "email": "admin@dean.local"
            },
            {
                "username": "user",
                "password": "user123",
                "roles": [UserRole.USER],
                "full_name": "Regular User",
                "email": "user@dean.local"
            },
            {
                "username": "viewer",
                "password": "viewer123",
                "roles": [UserRole.VIEWER],
                "full_name": "Viewer User",
                "email": "viewer@dean.local"
            }
        ]
        
        for user_data in default_users:
            user_id = str(uuid4())
            self.users[user_id] = {
                "id": user_id,
                "username": user_data["username"],
                "password_hash": hash_password(user_data["password"]),
                "email": user_data["email"],
                "full_name": user_data["full_name"],
                "roles": user_data["roles"],
                "is_active": True,
                "created_at": datetime.utcnow(),
                "last_login": None
            }
            
        logger.info("Default users initialized", count=len(default_users))
    
    def authenticate_user(self, credentials: UserCredentials) -> Optional[User]:
        """Authenticate a user with username and password."""
        # Check if account is locked
        if self._is_account_locked(credentials.username):
            logger.warning("Login attempt on locked account", username=credentials.username)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is locked due to too many failed attempts"
            )
        
        # Find user by username
        user_data = None
        for uid, udata in self.users.items():
            if udata["username"] == credentials.username:
                user_data = udata
                break
        
        if not user_data:
            self._record_failed_attempt(credentials.username)
            logger.warning("Authentication failed - user not found", username=credentials.username)
            return None
        
        # Verify password
        if not verify_password(credentials.password, user_data["password_hash"]):
            self._record_failed_attempt(credentials.username)
            logger.warning("Authentication failed - invalid password", username=credentials.username)
            return None
        
        # Check if user is active
        if not user_data["is_active"]:
            logger.warning("Authentication failed - user inactive", username=credentials.username)
            return None
        
        # Clear failed attempts on successful login
        self._clear_failed_attempts(credentials.username)
        
        # Update last login
        user_data["last_login"] = datetime.utcnow()
        
        # Create user object
        user = User(
            id=user_data["id"],
            username=user_data["username"],
            email=user_data["email"],
            full_name=user_data["full_name"],
            roles=user_data["roles"],
            is_active=user_data["is_active"],
            created_at=user_data["created_at"],
            last_login=user_data["last_login"]
        )
        
        logger.info("User authenticated successfully", 
                   username=credentials.username,
                   user_id=user.id,
                   roles=[r.value for r in user.roles])
        
        return user
    
    def create_token_response(self, user: User) -> TokenResponse:
        """Create token response for authenticated user."""
        # Create access and refresh tokens
        token_dict = create_token_response(
            user_id=user.id,
            username=user.username,
            roles=user.roles,
            access_token_expires=timedelta(minutes=self.config.access_token_expire_minutes),
            refresh_token_expires=timedelta(days=self.config.refresh_token_expire_days),
            secret_key=self.config.jwt_secret_key,
            algorithm=self.config.jwt_algorithm
        )
        
        # Store refresh token info
        refresh_token = token_dict["refresh_token"]
        self.refresh_tokens[refresh_token] = {
            "user_id": user.id,
            "username": user.username,
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(days=self.config.refresh_token_expire_days)
        }
        
        return TokenResponse(**token_dict)
    
    def refresh_access_token(self, refresh_request: TokenRefreshRequest) -> TokenResponse:
        """Refresh access token using refresh token."""
        # Verify refresh token
        token_data = verify_token(
            refresh_request.refresh_token,
            secret_key=self.config.jwt_secret_key,
            algorithm=self.config.jwt_algorithm,
            token_type="refresh"
        )
        
        if not token_data:
            logger.warning("Invalid refresh token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Check if refresh token is in our store
        if refresh_request.refresh_token not in self.refresh_tokens:
            logger.warning("Refresh token not found in store")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Get user
        user_data = self.users.get(token_data.user_id)
        if not user_data or not user_data["is_active"]:
            logger.warning("User not found or inactive for refresh", user_id=token_data.user_id)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        # Create new user object
        user = User(
            id=user_data["id"],
            username=user_data["username"],
            email=user_data["email"],
            full_name=user_data["full_name"],
            roles=user_data["roles"],
            is_active=user_data["is_active"],
            created_at=user_data["created_at"],
            last_login=user_data["last_login"]
        )
        
        # Remove old refresh token
        del self.refresh_tokens[refresh_request.refresh_token]
        
        # Create new tokens
        logger.info("Refreshing access token", username=user.username)
        return self.create_token_response(user)
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        user_data = self.users.get(user_id)
        if not user_data:
            return None
        
        return User(
            id=user_data["id"],
            username=user_data["username"],
            email=user_data["email"],
            full_name=user_data["full_name"],
            roles=user_data["roles"],
            is_active=user_data["is_active"],
            created_at=user_data["created_at"],
            last_login=user_data["last_login"]
        )
    
    def create_api_key(self, name: str, description: str = "", roles: List[UserRole] = None) -> tuple[str, APIKey]:
        """Create a new API key."""
        if roles is None:
            roles = [UserRole.USER]
        
        # Generate key
        plain_key = generate_api_key()
        key_hash = hash_api_key(plain_key)
        key_id = str(uuid4())
        
        # Create API key object
        api_key = APIKey(
            key_id=key_id,
            key_hash=key_hash,
            name=name,
            description=description,
            roles=roles,
            created_at=datetime.utcnow(),
            is_active=True
        )
        
        # Store API key
        self.api_keys[key_id] = api_key
        
        logger.info("API key created", key_id=key_id, name=name, roles=[r.value for r in roles])
        
        # Return plain key (only shown once) and API key object
        return plain_key, api_key
    
    def validate_api_key(self, api_key: str) -> Optional[APIKey]:
        """Validate an API key."""
        # Try to find matching API key
        for key_id, key_obj in self.api_keys.items():
            if verify_api_key(api_key, key_obj.key_hash):
                if not key_obj.is_active:
                    logger.warning("Inactive API key used", key_id=key_id)
                    return None
                
                # Check expiration
                if key_obj.expires_at and key_obj.expires_at < datetime.utcnow():
                    logger.warning("Expired API key used", key_id=key_id)
                    return None
                
                # Update last used
                key_obj.last_used = datetime.utcnow()
                
                logger.info("API key validated", key_id=key_id, name=key_obj.name)
                return key_obj
        
        logger.warning("Invalid API key")
        return None
    
    def _is_account_locked(self, username: str) -> bool:
        """Check if account is locked due to failed attempts."""
        if username not in self.failed_attempts:
            return False
        
        # Remove old attempts
        cutoff_time = datetime.utcnow() - timedelta(minutes=self.config.lockout_duration_minutes)
        self.failed_attempts[username] = [
            attempt for attempt in self.failed_attempts[username]
            if attempt > cutoff_time
        ]
        
        # Check if locked
        return len(self.failed_attempts[username]) >= self.config.max_login_attempts
    
    def _record_failed_attempt(self, username: str):
        """Record a failed login attempt."""
        if username not in self.failed_attempts:
            self.failed_attempts[username] = []
        
        self.failed_attempts[username].append(datetime.utcnow())
        
        # Check if account should be locked
        if len(self.failed_attempts[username]) >= self.config.max_login_attempts:
            logger.warning("Account locked due to failed attempts", 
                         username=username,
                         attempts=len(self.failed_attempts[username]))
    
    def _clear_failed_attempts(self, username: str):
        """Clear failed login attempts for a user."""
        if username in self.failed_attempts:
            del self.failed_attempts[username]


# Singleton instance
_auth_manager: Optional[AuthManager] = None


def get_auth_manager(config: Optional[AuthConfig] = None) -> AuthManager:
    """Get or create the authentication manager singleton."""
    global _auth_manager
    
    if _auth_manager is None:
        _auth_manager = AuthManager(config)
    
    return _auth_manager