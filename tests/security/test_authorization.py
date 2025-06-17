"""Test authorization and role-based access control."""

import pytest
from unittest.mock import Mock, patch

from src.auth.auth_models import UserRole, TokenData
from src.auth.auth_middleware import require_auth, require_roles
from src.auth.auth_utils import create_access_token, verify_token
from fastapi import HTTPException
from datetime import timedelta


class TestRoleBasedAccess:
    """Test role-based access control."""
    
    @pytest.fixture
    def mock_request(self):
        """Create a mock request object."""
        request = Mock()
        request.headers = {}
        return request
    
    @pytest.fixture
    def auth_config(self):
        """Get auth configuration."""
        from src.auth.auth_models import AuthConfig
        return AuthConfig(
            jwt_secret_key="test-secret",
            jwt_algorithm="HS256",
            access_token_expire_minutes=30,
            refresh_token_expire_days=7,
            password_min_length=6,
            max_login_attempts=5,
            lockout_duration_minutes=15
        )
    
    def test_admin_has_all_access(self, mock_request, auth_config):
        """Test that admin role has access to all endpoints."""
        # Create admin token
        token = create_access_token(
            user_id="admin-id",
            username="admin",
            roles=[UserRole.ADMIN],
            expires_delta=timedelta(minutes=30),
            secret_key=auth_config.jwt_secret_key,
            algorithm=auth_config.jwt_algorithm
        )
        
        mock_request.headers["Authorization"] = f"Bearer {token}"
        
        # Test access to admin-only endpoint
        @require_roles([UserRole.ADMIN])
        async def admin_endpoint(request):
            return {"message": "Admin access granted"}
        
        result = admin_endpoint(mock_request)
        assert result is not None
    
    def test_user_denied_admin_access(self, mock_request, auth_config):
        """Test that user role is denied admin access."""
        # Create user token
        token = create_access_token(
            user_id="user-id",
            username="user",
            roles=[UserRole.USER],
            expires_delta=timedelta(minutes=30),
            secret_key=auth_config.jwt_secret_key,
            algorithm=auth_config.jwt_algorithm
        )
        
        mock_request.headers["Authorization"] = f"Bearer {token}"
        
        # Test access to admin-only endpoint
        @require_roles([UserRole.ADMIN])
        async def admin_endpoint(request):
            return {"message": "Admin access granted"}
        
        with pytest.raises(HTTPException) as exc_info:
            admin_endpoint(mock_request)
        
        assert exc_info.value.status_code == 403
        assert "Insufficient permissions" in exc_info.value.detail
    
    def test_viewer_limited_access(self, mock_request, auth_config):
        """Test viewer role has limited access."""
        # Create viewer token
        token = create_access_token(
            user_id="viewer-id",
            username="viewer",
            roles=[UserRole.VIEWER],
            expires_delta=timedelta(minutes=30),
            secret_key=auth_config.jwt_secret_key,
            algorithm=auth_config.jwt_algorithm
        )
        
        mock_request.headers["Authorization"] = f"Bearer {token}"
        
        # Viewer should have access to viewer endpoints
        @require_roles([UserRole.VIEWER, UserRole.USER, UserRole.ADMIN])
        async def public_read_endpoint(request):
            return {"data": "public data"}
        
        result = public_read_endpoint(mock_request)
        assert result is not None
        
        # Viewer should NOT have access to write endpoints
        @require_roles([UserRole.USER, UserRole.ADMIN])
        async def write_endpoint(request):
            return {"message": "Write successful"}
        
        with pytest.raises(HTTPException) as exc_info:
            write_endpoint(mock_request)
        
        assert exc_info.value.status_code == 403
    
    def test_multiple_roles(self, mock_request, auth_config):
        """Test user with multiple roles."""
        # Create token with multiple roles
        token = create_access_token(
            user_id="multi-role-id",
            username="multi-user",
            roles=[UserRole.USER, UserRole.VIEWER],
            expires_delta=timedelta(minutes=30),
            secret_key=auth_config.jwt_secret_key,
            algorithm=auth_config.jwt_algorithm
        )
        
        mock_request.headers["Authorization"] = f"Bearer {token}"
        
        # Should have access if ANY required role matches
        @require_roles([UserRole.USER])
        async def user_endpoint(request):
            return {"message": "User access"}
        
        @require_roles([UserRole.VIEWER])
        async def viewer_endpoint(request):
            return {"message": "Viewer access"}
        
        # Both should work
        assert user_endpoint(mock_request) is not None
        assert viewer_endpoint(mock_request) is not None
    
    def test_no_roles_required(self, mock_request, auth_config):
        """Test endpoint with no specific roles required."""
        # Create token with any role
        token = create_access_token(
            user_id="any-id",
            username="any-user",
            roles=[UserRole.VIEWER],
            expires_delta=timedelta(minutes=30),
            secret_key=auth_config.jwt_secret_key,
            algorithm=auth_config.jwt_algorithm
        )
        
        mock_request.headers["Authorization"] = f"Bearer {token}"
        
        # Endpoint that just requires authentication, not specific roles
        @require_auth
        async def authenticated_endpoint(request):
            return {"message": "Authenticated"}
        
        result = authenticated_endpoint(mock_request)
        assert result is not None


class TestAPIKeyAuthorization:
    """Test API key authorization."""
    
    @pytest.fixture
    def auth_manager(self):
        """Create auth manager for testing."""
        from src.auth.auth_manager import get_auth_manager
        from src.auth import auth_manager as auth_module
        auth_module._auth_manager = None
        return get_auth_manager()
    
    def test_create_api_key_with_roles(self, auth_manager):
        """Test creating API key with specific roles."""
        plain_key, api_key = auth_manager.create_api_key(
            name="Test API Key",
            description="Test key for integration",
            roles=[UserRole.USER]
        )
        
        assert plain_key is not None
        assert api_key.name == "Test API Key"
        assert api_key.description == "Test key for integration"
        assert UserRole.USER in api_key.roles
        assert api_key.is_active is True
        assert api_key.key_id in auth_manager.api_keys
    
    def test_validate_api_key(self, auth_manager):
        """Test API key validation."""
        plain_key, api_key = auth_manager.create_api_key(
            name="Test Key",
            roles=[UserRole.USER]
        )
        
        # Validate with correct key
        validated_key = auth_manager.validate_api_key(plain_key)
        assert validated_key is not None
        assert validated_key.key_id == api_key.key_id
        assert validated_key.last_used is not None
    
    def test_invalid_api_key(self, auth_manager):
        """Test validation with invalid API key."""
        result = auth_manager.validate_api_key("invalid-key-12345")
        assert result is None
    
    def test_inactive_api_key(self, auth_manager):
        """Test validation with inactive API key."""
        plain_key, api_key = auth_manager.create_api_key(
            name="Inactive Key",
            roles=[UserRole.USER]
        )
        
        # Deactivate the key
        auth_manager.api_keys[api_key.key_id].is_active = False
        
        # Should not validate
        result = auth_manager.validate_api_key(plain_key)
        assert result is None
    
    def test_expired_api_key(self, auth_manager):
        """Test validation with expired API key."""
        from datetime import datetime, timedelta
        
        plain_key, api_key = auth_manager.create_api_key(
            name="Expired Key",
            roles=[UserRole.USER]
        )
        
        # Set expiration in the past
        auth_manager.api_keys[api_key.key_id].expires_at = datetime.utcnow() - timedelta(days=1)
        
        # Should not validate
        result = auth_manager.validate_api_key(plain_key)
        assert result is None
    
    def test_api_key_roles_enforcement(self, auth_manager):
        """Test that API key roles are enforced."""
        # Create API key with viewer role only
        plain_key, api_key = auth_manager.create_api_key(
            name="Viewer API Key",
            roles=[UserRole.VIEWER]
        )
        
        validated_key = auth_manager.validate_api_key(plain_key)
        assert validated_key is not None
        assert UserRole.VIEWER in validated_key.roles
        assert UserRole.USER not in validated_key.roles
        assert UserRole.ADMIN not in validated_key.roles


class TestAuthorizationMiddleware:
    """Test authorization middleware functionality."""
    
    @pytest.fixture
    def mock_request(self):
        """Create a mock request object."""
        request = Mock()
        request.headers = {}
        return request
    
    @pytest.fixture
    def auth_config(self):
        """Get auth configuration."""
        from src.auth.auth_models import AuthConfig
        return AuthConfig(
            jwt_secret_key="test-secret",
            jwt_algorithm="HS256",
            access_token_expire_minutes=30,
            refresh_token_expire_days=7,
            password_min_length=6,
            max_login_attempts=5,
            lockout_duration_minutes=15
        )
    
    def test_missing_authorization_header(self, mock_request):
        """Test request without authorization header."""
        @require_auth
        async def protected_endpoint(request):
            return {"message": "Protected"}
        
        with pytest.raises(HTTPException) as exc_info:
            protected_endpoint(mock_request)
        
        assert exc_info.value.status_code == 401
        assert "Missing authentication" in exc_info.value.detail
    
    def test_invalid_bearer_format(self, mock_request):
        """Test invalid bearer token format."""
        mock_request.headers["Authorization"] = "InvalidFormat token"
        
        @require_auth
        async def protected_endpoint(request):
            return {"message": "Protected"}
        
        with pytest.raises(HTTPException) as exc_info:
            protected_endpoint(mock_request)
        
        assert exc_info.value.status_code == 401
        assert "Invalid authentication" in exc_info.value.detail
    
    def test_expired_token(self, mock_request, auth_config):
        """Test expired token is rejected."""
        # Create token that's already expired
        token = create_access_token(
            user_id="user-id",
            username="user",
            roles=[UserRole.USER],
            expires_delta=timedelta(minutes=-1),  # Expired
            secret_key=auth_config.jwt_secret_key,
            algorithm=auth_config.jwt_algorithm
        )
        
        mock_request.headers["Authorization"] = f"Bearer {token}"
        
        @require_auth
        async def protected_endpoint(request):
            return {"message": "Protected"}
        
        with pytest.raises(HTTPException) as exc_info:
            protected_endpoint(mock_request)
        
        assert exc_info.value.status_code == 401
        assert "Invalid or expired token" in exc_info.value.detail
    
    def test_tampered_token(self, mock_request, auth_config):
        """Test tampered token is rejected."""
        # Create valid token
        token = create_access_token(
            user_id="user-id",
            username="user",
            roles=[UserRole.USER],
            expires_delta=timedelta(minutes=30),
            secret_key=auth_config.jwt_secret_key,
            algorithm=auth_config.jwt_algorithm
        )
        
        # Tamper with the token
        tampered_token = token[:-10] + "tampered123"
        mock_request.headers["Authorization"] = f"Bearer {tampered_token}"
        
        @require_auth
        async def protected_endpoint(request):
            return {"message": "Protected"}
        
        with pytest.raises(HTTPException) as exc_info:
            protected_endpoint(mock_request)
        
        assert exc_info.value.status_code == 401
        assert "Invalid or expired token" in exc_info.value.detail


class TestCrossServiceAuthorization:
    """Test authorization between services."""
    
    @pytest.fixture
    def service_token(self, auth_config):
        """Create a service-to-service token."""
        return create_access_token(
            user_id="service-orchestrator",
            username="orchestrator-service",
            roles=[UserRole.SERVICE],
            expires_delta=timedelta(hours=24),
            secret_key=auth_config.jwt_secret_key,
            algorithm=auth_config.jwt_algorithm
        )
    
    @pytest.fixture
    def auth_config(self):
        """Get auth configuration."""
        from src.auth.auth_models import AuthConfig
        return AuthConfig(
            jwt_secret_key="test-secret",
            jwt_algorithm="HS256",
            access_token_expire_minutes=30,
            refresh_token_expire_days=7,
            password_min_length=6,
            max_login_attempts=5,
            lockout_duration_minutes=15
        )
    
    def test_service_role_access(self, mock_request, service_token):
        """Test service role has appropriate access."""
        mock_request.headers["Authorization"] = f"Bearer {service_token}"
        
        @require_roles([UserRole.SERVICE, UserRole.ADMIN])
        async def service_endpoint(request):
            return {"message": "Service access granted"}
        
        result = service_endpoint(mock_request)
        assert result is not None
    
    def test_service_cannot_access_user_endpoints(self, mock_request, service_token):
        """Test service role cannot access user-only endpoints."""
        mock_request.headers["Authorization"] = f"Bearer {service_token}"
        
        @require_roles([UserRole.USER])
        async def user_only_endpoint(request):
            return {"message": "User only"}
        
        with pytest.raises(HTTPException) as exc_info:
            user_only_endpoint(mock_request)
        
        assert exc_info.value.status_code == 403
        assert "Insufficient permissions" in exc_info.value.detail