"""
Authentication models for DEAN orchestration system.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field, EmailStr


class UserRole(str, Enum):
    """User roles for access control."""
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"


class UserCredentials(BaseModel):
    """User login credentials."""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)


class TokenResponse(BaseModel):
    """Authentication token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Access token expiration in seconds")
    scope: str = Field(default="", description="Space-separated list of scopes")


class TokenRefreshRequest(BaseModel):
    """Token refresh request."""
    refresh_token: str


class TokenData(BaseModel):
    """Data extracted from JWT token."""
    username: str
    user_id: str
    roles: List[UserRole]
    exp: Optional[int] = None
    iat: Optional[int] = None
    scope: Optional[str] = None


class User(BaseModel):
    """User model."""
    id: str
    username: str
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    roles: List[UserRole] = Field(default_factory=lambda: [UserRole.USER])
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    
    # Password hash is not included in the model for security
    # It's stored separately in the user store
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class UserCreate(BaseModel):
    """User creation request."""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    roles: List[UserRole] = Field(default_factory=lambda: [UserRole.USER])


class UserUpdate(BaseModel):
    """User update request."""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    roles: Optional[List[UserRole]] = None
    is_active: Optional[bool] = None


class PasswordChange(BaseModel):
    """Password change request."""
    current_password: str
    new_password: str = Field(..., min_length=6)


class APIKey(BaseModel):
    """API key model for service-to-service auth."""
    key_id: str
    key_hash: str  # Hashed API key
    name: str
    description: Optional[str] = None
    roles: List[UserRole] = Field(default_factory=lambda: [UserRole.USER])
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    last_used: Optional[datetime] = None
    is_active: bool = True


class AuthConfig(BaseModel):
    """Authentication configuration."""
    # JWT settings
    jwt_secret_key: str = Field(..., description="Secret key for JWT signing")
    jwt_algorithm: str = Field(default="HS256", description="JWT signing algorithm")
    access_token_expire_minutes: int = Field(default=30, description="Access token expiration time")
    refresh_token_expire_days: int = Field(default=7, description="Refresh token expiration time")
    
    # Security settings
    password_min_length: int = Field(default=6, ge=6)
    password_require_uppercase: bool = Field(default=False)
    password_require_lowercase: bool = Field(default=True)
    password_require_digits: bool = Field(default=False)
    password_require_special: bool = Field(default=False)
    
    # Session settings
    max_login_attempts: int = Field(default=5, description="Max failed login attempts before lockout")
    lockout_duration_minutes: int = Field(default=15, description="Account lockout duration")
    
    # API key settings
    api_key_header_name: str = Field(default="X-API-Key")
    allow_api_key_auth: bool = Field(default=True)
    
    # CORS settings
    cors_origins: List[str] = Field(default_factory=lambda: ["*"])
    cors_allow_credentials: bool = Field(default=True)
    cors_allow_methods: List[str] = Field(default_factory=lambda: ["*"])
    cors_allow_headers: List[str] = Field(default_factory=lambda: ["*"])