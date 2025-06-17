"""
Authentication utilities for DEAN orchestration system.
"""

import os
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from jose import JWTError, jwt
from passlib.context import CryptContext
import structlog

from .auth_models import TokenData, UserRole

# Configure logging
logger = structlog.get_logger()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Default JWT settings (can be overridden by config)
DEFAULT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
DEFAULT_ALGORITHM = "HS256"
DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES = 30
DEFAULT_REFRESH_TOKEN_EXPIRE_DAYS = 7


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error("Password verification error", error=str(e))
        return False


def create_access_token(
    data: Dict[str, Any],
    secret_key: str = DEFAULT_SECRET_KEY,
    algorithm: str = DEFAULT_ALGORITHM,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    })
    
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=algorithm)
    
    logger.info("Access token created", 
                username=data.get("sub"),
                expires_in_minutes=expires_delta.total_seconds() / 60 if expires_delta else DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES)
    
    return encoded_jwt


def create_refresh_token(
    data: Dict[str, Any],
    secret_key: str = DEFAULT_SECRET_KEY,
    algorithm: str = DEFAULT_ALGORITHM,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create a JWT refresh token."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=DEFAULT_REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh",
        "jti": secrets.token_urlsafe(32)  # Unique token ID for refresh tokens
    })
    
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=algorithm)
    
    logger.info("Refresh token created", 
                username=data.get("sub"),
                expires_in_days=expires_delta.total_seconds() / 86400 if expires_delta else DEFAULT_REFRESH_TOKEN_EXPIRE_DAYS)
    
    return encoded_jwt


def verify_token(
    token: str,
    secret_key: str = DEFAULT_SECRET_KEY,
    algorithm: str = DEFAULT_ALGORITHM,
    token_type: Optional[str] = None
) -> Optional[TokenData]:
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        
        # Check token type if specified
        if token_type and payload.get("type") != token_type:
            logger.warning("Invalid token type", 
                         expected=token_type, 
                         actual=payload.get("type"))
            return None
        
        # Extract user data
        username: str = payload.get("sub")
        user_id: str = payload.get("user_id")
        roles_str: List[str] = payload.get("roles", [])
        
        if username is None or user_id is None:
            logger.warning("Invalid token payload", payload=payload)
            return None
        
        # Convert role strings to UserRole enums
        roles = [UserRole(role) for role in roles_str]
        
        token_data = TokenData(
            username=username,
            user_id=user_id,
            roles=roles,
            exp=payload.get("exp"),
            iat=payload.get("iat"),
            scope=payload.get("scope")
        )
        
        return token_data
        
    except JWTError as e:
        logger.error("JWT verification error", error=str(e))
        return None
    except Exception as e:
        logger.error("Unexpected token verification error", error=str(e))
        return None


def generate_api_key() -> str:
    """Generate a secure API key."""
    # Generate a 32-byte random key and encode as URL-safe base64
    return secrets.token_urlsafe(32)


def hash_api_key(api_key: str) -> str:
    """Hash an API key for storage."""
    # Use the same password hashing for API keys
    return hash_password(api_key)


def verify_api_key(plain_api_key: str, hashed_api_key: str) -> bool:
    """Verify an API key against its hash."""
    return verify_password(plain_api_key, hashed_api_key)


def validate_password_strength(
    password: str,
    min_length: int = 6,
    require_uppercase: bool = False,
    require_lowercase: bool = True,
    require_digits: bool = False,
    require_special: bool = False
) -> tuple[bool, Optional[str]]:
    """Validate password strength based on requirements."""
    if len(password) < min_length:
        return False, f"Password must be at least {min_length} characters long"
    
    if require_uppercase and not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    
    if require_lowercase and not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
    
    if require_digits and not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit"
    
    if require_special and not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        return False, "Password must contain at least one special character"
    
    return True, None


def extract_token_from_header(authorization: str) -> Optional[str]:
    """Extract token from Authorization header."""
    if not authorization:
        return None
    
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    
    return parts[1]


def create_token_response(
    user_id: str,
    username: str,
    roles: List[UserRole],
    scope: str = "",
    access_token_expires: Optional[timedelta] = None,
    refresh_token_expires: Optional[timedelta] = None,
    secret_key: str = DEFAULT_SECRET_KEY,
    algorithm: str = DEFAULT_ALGORITHM
) -> Dict[str, Any]:
    """Create a complete token response with access and refresh tokens."""
    # Token data
    token_data = {
        "sub": username,
        "user_id": user_id,
        "roles": [role.value for role in roles],
        "scope": scope
    }
    
    # Create tokens
    access_token = create_access_token(
        data=token_data,
        secret_key=secret_key,
        algorithm=algorithm,
        expires_delta=access_token_expires
    )
    
    refresh_token = create_refresh_token(
        data=token_data,
        secret_key=secret_key,
        algorithm=algorithm,
        expires_delta=refresh_token_expires
    )
    
    # Calculate expiration time
    expires_in = int(
        access_token_expires.total_seconds() if access_token_expires 
        else DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": expires_in,
        "scope": scope
    }