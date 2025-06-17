"""
Authentication module for DEAN orchestration system.

Provides JWT-based authentication with role-based access control.
"""

from .auth_manager import AuthManager, get_auth_manager
from .auth_middleware import AuthMiddleware, require_auth, require_role
from .auth_models import (
    UserCredentials,
    TokenResponse,
    TokenRefreshRequest,
    User,
    UserRole
)
from .auth_utils import (
    create_access_token,
    create_refresh_token,
    verify_token,
    hash_password,
    verify_password
)

__all__ = [
    "AuthManager",
    "get_auth_manager",
    "AuthMiddleware",
    "require_auth",
    "require_role",
    "UserCredentials",
    "TokenResponse",
    "TokenRefreshRequest",
    "User",
    "UserRole",
    "create_access_token",
    "create_refresh_token",
    "verify_token",
    "hash_password",
    "verify_password"
]