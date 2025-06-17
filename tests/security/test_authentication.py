"""Test authentication functionality."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from src.auth.auth_manager import AuthManager, get_auth_manager
from src.auth.auth_models import UserCredentials, UserRole, AuthConfig
from src.auth.auth_utils import verify_token
from fastapi import HTTPException


class TestAuthenticationManager:
    """Test authentication manager functionality."""
    
    @pytest.fixture
    def auth_manager(self):
        """Create a fresh auth manager instance."""
        # Reset singleton
        from src.auth import auth_manager as auth_module
        auth_module._auth_manager = None
        
        config = AuthConfig(
            jwt_secret_key="test-secret-key",
            jwt_algorithm="HS256",
            access_token_expire_minutes=30,
            refresh_token_expire_days=7,
            password_min_length=6,
            max_login_attempts=3,
            lockout_duration_minutes=5
        )
        return get_auth_manager(config)
    
    def test_default_users_created(self, auth_manager):
        """Test that default users are created on initialization."""
        # Check that we have the expected number of users
        assert len(auth_manager.users) == 3
        
        # Find users by username
        usernames = [user["username"] for user in auth_manager.users.values()]
        assert "admin" in usernames
        assert "user" in usernames
        assert "viewer" in usernames
        
        # Check admin user roles
        admin_user = next(u for u in auth_manager.users.values() if u["username"] == "admin")
        assert UserRole.ADMIN in admin_user["roles"]
    
    def test_successful_authentication(self, auth_manager):
        """Test successful user authentication."""
        credentials = UserCredentials(username="admin", password="admin123")
        user = auth_manager.authenticate_user(credentials)
        
        assert user is not None
        assert user.username == "admin"
        assert UserRole.ADMIN in user.roles
        assert user.is_active is True
        assert user.last_login is not None
    
    def test_invalid_username(self, auth_manager):
        """Test authentication with invalid username."""
        credentials = UserCredentials(username="nonexistent", password="password")
        user = auth_manager.authenticate_user(credentials)
        
        assert user is None
    
    def test_invalid_password(self, auth_manager):
        """Test authentication with invalid password."""
        credentials = UserCredentials(username="admin", password="wrongpassword")
        user = auth_manager.authenticate_user(credentials)
        
        assert user is None
    
    def test_inactive_user(self, auth_manager):
        """Test authentication with inactive user."""
        # Make admin user inactive
        admin_user = next(u for u in auth_manager.users.values() if u["username"] == "admin")
        admin_user["is_active"] = False
        
        credentials = UserCredentials(username="admin", password="admin123")
        user = auth_manager.authenticate_user(credentials)
        
        assert user is None
    
    def test_account_lockout(self, auth_manager):
        """Test account lockout after failed attempts."""
        credentials = UserCredentials(username="admin", password="wrongpassword")
        
        # Make max_login_attempts failed attempts
        for _ in range(auth_manager.config.max_login_attempts):
            auth_manager.authenticate_user(credentials)
        
        # Next attempt should raise HTTPException
        with pytest.raises(HTTPException) as exc_info:
            auth_manager.authenticate_user(credentials)
        
        assert exc_info.value.status_code == 403
        assert "locked" in exc_info.value.detail.lower()
    
    def test_lockout_expiration(self, auth_manager):
        """Test that lockout expires after duration."""
        credentials = UserCredentials(username="admin", password="wrongpassword")
        
        # Lock the account
        for _ in range(auth_manager.config.max_login_attempts):
            auth_manager.authenticate_user(credentials)
        
        # Manipulate failed attempts to simulate time passing
        old_time = datetime.utcnow() - timedelta(minutes=auth_manager.config.lockout_duration_minutes + 1)
        auth_manager.failed_attempts["admin"] = [old_time] * auth_manager.config.max_login_attempts
        
        # Should be able to attempt login again
        correct_credentials = UserCredentials(username="admin", password="admin123")
        user = auth_manager.authenticate_user(correct_credentials)
        assert user is not None
    
    def test_failed_attempts_cleared_on_success(self, auth_manager):
        """Test that failed attempts are cleared on successful login."""
        wrong_credentials = UserCredentials(username="admin", password="wrongpassword")
        correct_credentials = UserCredentials(username="admin", password="admin123")
        
        # Make some failed attempts
        auth_manager.authenticate_user(wrong_credentials)
        auth_manager.authenticate_user(wrong_credentials)
        
        assert "admin" in auth_manager.failed_attempts
        assert len(auth_manager.failed_attempts["admin"]) == 2
        
        # Successful login should clear attempts
        user = auth_manager.authenticate_user(correct_credentials)
        assert user is not None
        assert "admin" not in auth_manager.failed_attempts


class TestTokenGeneration:
    """Test token generation and validation."""
    
    @pytest.fixture
    def auth_manager(self):
        """Create auth manager for testing."""
        from src.auth import auth_manager as auth_module
        auth_module._auth_manager = None
        return get_auth_manager()
    
    def test_create_token_response(self, auth_manager):
        """Test creating token response for authenticated user."""
        credentials = UserCredentials(username="admin", password="admin123")
        user = auth_manager.authenticate_user(credentials)
        
        token_response = auth_manager.create_token_response(user)
        
        assert token_response.access_token is not None
        assert token_response.refresh_token is not None
        assert token_response.token_type == "bearer"
        assert token_response.expires_in > 0
        
        # Verify tokens are different
        assert token_response.access_token != token_response.refresh_token
    
    def test_access_token_contains_user_info(self, auth_manager):
        """Test that access token contains correct user information."""
        credentials = UserCredentials(username="admin", password="admin123")
        user = auth_manager.authenticate_user(credentials)
        
        token_response = auth_manager.create_token_response(user)
        
        # Decode and verify token
        token_data = verify_token(
            token_response.access_token,
            secret_key=auth_manager.config.jwt_secret_key,
            algorithm=auth_manager.config.jwt_algorithm,
            token_type="access"
        )
        
        assert token_data is not None
        assert token_data.user_id == user.id
        assert token_data.username == user.username
        assert UserRole.ADMIN in token_data.roles
    
    def test_refresh_token_stored(self, auth_manager):
        """Test that refresh tokens are stored correctly."""
        credentials = UserCredentials(username="admin", password="admin123")
        user = auth_manager.authenticate_user(credentials)
        
        token_response = auth_manager.create_token_response(user)
        
        # Check refresh token is stored
        assert token_response.refresh_token in auth_manager.refresh_tokens
        
        stored_info = auth_manager.refresh_tokens[token_response.refresh_token]
        assert stored_info["user_id"] == user.id
        assert stored_info["username"] == user.username
        assert "created_at" in stored_info
        assert "expires_at" in stored_info


class TestTokenRefresh:
    """Test token refresh functionality."""
    
    @pytest.fixture
    def auth_manager(self):
        """Create auth manager for testing."""
        from src.auth import auth_manager as auth_module
        auth_module._auth_manager = None
        return get_auth_manager()
    
    def test_successful_token_refresh(self, auth_manager):
        """Test successful token refresh."""
        # Login and get initial tokens
        credentials = UserCredentials(username="admin", password="admin123")
        user = auth_manager.authenticate_user(credentials)
        initial_response = auth_manager.create_token_response(user)
        
        # Refresh token
        from src.auth.auth_models import TokenRefreshRequest
        refresh_request = TokenRefreshRequest(refresh_token=initial_response.refresh_token)
        new_response = auth_manager.refresh_access_token(refresh_request)
        
        assert new_response.access_token is not None
        assert new_response.refresh_token is not None
        
        # New tokens should be different from old ones
        assert new_response.access_token != initial_response.access_token
        assert new_response.refresh_token != initial_response.refresh_token
        
        # Old refresh token should be removed
        assert initial_response.refresh_token not in auth_manager.refresh_tokens
        
        # New refresh token should be stored
        assert new_response.refresh_token in auth_manager.refresh_tokens
    
    def test_invalid_refresh_token(self, auth_manager):
        """Test refresh with invalid token."""
        from src.auth.auth_models import TokenRefreshRequest
        refresh_request = TokenRefreshRequest(refresh_token="invalid-token")
        
        with pytest.raises(HTTPException) as exc_info:
            auth_manager.refresh_access_token(refresh_request)
        
        assert exc_info.value.status_code == 401
        assert "Invalid refresh token" in exc_info.value.detail
    
    def test_refresh_token_not_in_store(self, auth_manager):
        """Test refresh with token not in store."""
        # Create a valid refresh token but don't store it
        from src.auth.auth_utils import create_refresh_token
        from datetime import timedelta
        
        token = create_refresh_token(
            user_id="test-id",
            username="test-user",
            roles=[UserRole.USER],
            expires_delta=timedelta(days=1),
            secret_key=auth_manager.config.jwt_secret_key,
            algorithm=auth_manager.config.jwt_algorithm
        )
        
        from src.auth.auth_models import TokenRefreshRequest
        refresh_request = TokenRefreshRequest(refresh_token=token)
        
        with pytest.raises(HTTPException) as exc_info:
            auth_manager.refresh_access_token(refresh_request)
        
        assert exc_info.value.status_code == 401
        assert "Invalid refresh token" in exc_info.value.detail
    
    def test_refresh_for_inactive_user(self, auth_manager):
        """Test refresh token for user that becomes inactive."""
        # Login and get tokens
        credentials = UserCredentials(username="admin", password="admin123")
        user = auth_manager.authenticate_user(credentials)
        token_response = auth_manager.create_token_response(user)
        
        # Make user inactive
        auth_manager.users[user.id]["is_active"] = False
        
        # Try to refresh
        from src.auth.auth_models import TokenRefreshRequest
        refresh_request = TokenRefreshRequest(refresh_token=token_response.refresh_token)
        
        with pytest.raises(HTTPException) as exc_info:
            auth_manager.refresh_access_token(refresh_request)
        
        assert exc_info.value.status_code == 401
        assert "not found or inactive" in exc_info.value.detail


class TestUserManagement:
    """Test user management functionality."""
    
    @pytest.fixture
    def auth_manager(self):
        """Create auth manager for testing."""
        from src.auth import auth_manager as auth_module
        auth_module._auth_manager = None
        return get_auth_manager()
    
    def test_get_user_by_id(self, auth_manager):
        """Test retrieving user by ID."""
        # Get admin user ID
        admin_data = next(u for u in auth_manager.users.values() if u["username"] == "admin")
        admin_id = admin_data["id"]
        
        user = auth_manager.get_user_by_id(admin_id)
        
        assert user is not None
        assert user.id == admin_id
        assert user.username == "admin"
        assert UserRole.ADMIN in user.roles
    
    def test_get_nonexistent_user(self, auth_manager):
        """Test retrieving non-existent user."""
        user = auth_manager.get_user_by_id("nonexistent-id")
        assert user is None


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    @pytest.fixture
    def auth_manager(self):
        """Create auth manager for testing."""
        from src.auth import auth_manager as auth_module
        auth_module._auth_manager = None
        return get_auth_manager()
    
    def test_empty_credentials(self, auth_manager):
        """Test authentication with empty credentials."""
        credentials = UserCredentials(username="", password="")
        user = auth_manager.authenticate_user(credentials)
        assert user is None
    
    def test_very_long_credentials(self, auth_manager):
        """Test authentication with very long credentials."""
        credentials = UserCredentials(
            username="a" * 1000,
            password="b" * 1000
        )
        user = auth_manager.authenticate_user(credentials)
        assert user is None
    
    def test_special_characters_in_credentials(self, auth_manager):
        """Test authentication with special characters."""
        credentials = UserCredentials(
            username="admin'; DROP TABLE users; --",
            password="<script>alert('xss')</script>"
        )
        user = auth_manager.authenticate_user(credentials)
        assert user is None
    
    @patch('src.auth.auth_utils.datetime')
    def test_token_expiration_boundary(self, mock_datetime, auth_manager):
        """Test token behavior at expiration boundary."""
        # This would test that tokens expire exactly when expected
        # Implementation depends on how token expiration is handled
        pass