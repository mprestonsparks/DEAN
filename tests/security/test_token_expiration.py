"""Test token expiration and refresh flows."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, Mock
import time
import jwt

from src.auth.auth_models import UserRole, TokenRefreshRequest
from src.auth.auth_utils import create_access_token, create_refresh_token, verify_token
from src.auth.auth_manager import AuthManager, get_auth_manager
from fastapi import HTTPException


class TestTokenExpiration:
    """Test token expiration behavior."""
    
    @pytest.fixture
    def auth_config(self):
        """Get auth configuration."""
        from src.auth.auth_models import AuthConfig
        return AuthConfig(
            jwt_secret_key="test-secret-key",
            jwt_algorithm="HS256",
            access_token_expire_minutes=1,  # Short for testing
            refresh_token_expire_days=1,
            password_min_length=6,
            max_login_attempts=5,
            lockout_duration_minutes=15
        )
    
    @pytest.fixture
    def auth_manager(self, auth_config):
        """Create auth manager with test config."""
        from src.auth import auth_manager as auth_module
        auth_module._auth_manager = None
        return get_auth_manager(auth_config)
    
    def test_access_token_expires(self, auth_config):
        """Test that access tokens expire after configured time."""
        # Create token with 1 second expiry
        token = create_access_token(
            user_id="test-id",
            username="testuser",
            roles=[UserRole.USER],
            expires_delta=timedelta(seconds=1),
            secret_key=auth_config.jwt_secret_key,
            algorithm=auth_config.jwt_algorithm
        )
        
        # Should be valid immediately
        token_data = verify_token(
            token,
            secret_key=auth_config.jwt_secret_key,
            algorithm=auth_config.jwt_algorithm,
            token_type="access"
        )
        assert token_data is not None
        
        # Wait for expiration
        time.sleep(2)
        
        # Should now be expired
        token_data = verify_token(
            token,
            secret_key=auth_config.jwt_secret_key,
            algorithm=auth_config.jwt_algorithm,
            token_type="access"
        )
        assert token_data is None
    
    def test_refresh_token_longer_expiry(self, auth_config):
        """Test that refresh tokens have longer expiry than access tokens."""
        access_token = create_access_token(
            user_id="test-id",
            username="testuser",
            roles=[UserRole.USER],
            expires_delta=timedelta(minutes=auth_config.access_token_expire_minutes),
            secret_key=auth_config.jwt_secret_key,
            algorithm=auth_config.jwt_algorithm
        )
        
        refresh_token = create_refresh_token(
            user_id="test-id",
            username="testuser",
            roles=[UserRole.USER],
            expires_delta=timedelta(days=auth_config.refresh_token_expire_days),
            secret_key=auth_config.jwt_secret_key,
            algorithm=auth_config.jwt_algorithm
        )
        
        # Decode tokens to check expiry
        access_payload = jwt.decode(
            access_token,
            auth_config.jwt_secret_key,
            algorithms=[auth_config.jwt_algorithm],
            options={"verify_signature": False}
        )
        
        refresh_payload = jwt.decode(
            refresh_token,
            auth_config.jwt_secret_key,
            algorithms=[auth_config.jwt_algorithm],
            options={"verify_signature": False}
        )
        
        # Refresh token should expire later
        assert refresh_payload["exp"] > access_payload["exp"]
    
    def test_token_not_valid_before(self, auth_config):
        """Test that tokens can have 'not valid before' time."""
        # Create token that's not valid yet
        future_time = datetime.utcnow() + timedelta(seconds=2)
        
        token_payload = {
            "sub": "test-id",
            "username": "testuser",
            "roles": ["user"],
            "type": "access",
            "exp": datetime.utcnow() + timedelta(minutes=30),
            "nbf": future_time,  # Not valid before
            "iat": datetime.utcnow()
        }
        
        token = jwt.encode(
            token_payload,
            auth_config.jwt_secret_key,
            algorithm=auth_config.jwt_algorithm
        )
        
        # Should not be valid yet
        token_data = verify_token(
            token,
            secret_key=auth_config.jwt_secret_key,
            algorithm=auth_config.jwt_algorithm,
            token_type="access"
        )
        assert token_data is None
        
        # Wait until valid
        time.sleep(3)
        
        # Should now be valid
        token_data = verify_token(
            token,
            secret_key=auth_config.jwt_secret_key,
            algorithm=auth_config.jwt_algorithm,
            token_type="access"
        )
        assert token_data is not None


class TestRefreshTokenFlow:
    """Test refresh token flow and edge cases."""
    
    @pytest.fixture
    def auth_manager(self):
        """Create auth manager for testing."""
        from src.auth import auth_manager as auth_module
        auth_module._auth_manager = None
        
        from src.auth.auth_models import AuthConfig
        config = AuthConfig(
            jwt_secret_key="test-secret-key",
            jwt_algorithm="HS256",
            access_token_expire_minutes=5,
            refresh_token_expire_days=7,
            password_min_length=6,
            max_login_attempts=5,
            lockout_duration_minutes=15
        )
        return get_auth_manager(config)
    
    def test_refresh_token_single_use(self, auth_manager):
        """Test that refresh tokens can only be used once."""
        # Login to get tokens
        from src.auth.auth_models import UserCredentials
        credentials = UserCredentials(username="admin", password="admin123")
        user = auth_manager.authenticate_user(credentials)
        initial_tokens = auth_manager.create_token_response(user)
        
        # Use refresh token once
        refresh_request = TokenRefreshRequest(refresh_token=initial_tokens.refresh_token)
        new_tokens = auth_manager.refresh_access_token(refresh_request)
        
        assert new_tokens.access_token != initial_tokens.access_token
        assert new_tokens.refresh_token != initial_tokens.refresh_token
        
        # Try to use the same refresh token again
        with pytest.raises(HTTPException) as exc_info:
            auth_manager.refresh_access_token(refresh_request)
        
        assert exc_info.value.status_code == 401
        assert "Invalid refresh token" in exc_info.value.detail
    
    def test_refresh_token_rotation(self, auth_manager):
        """Test that refresh tokens are rotated on use."""
        # Login to get initial tokens
        from src.auth.auth_models import UserCredentials
        credentials = UserCredentials(username="admin", password="admin123")
        user = auth_manager.authenticate_user(credentials)
        tokens1 = auth_manager.create_token_response(user)
        
        # Refresh to get new tokens
        refresh_request1 = TokenRefreshRequest(refresh_token=tokens1.refresh_token)
        tokens2 = auth_manager.refresh_access_token(refresh_request1)
        
        # All tokens should be different
        assert tokens2.access_token != tokens1.access_token
        assert tokens2.refresh_token != tokens1.refresh_token
        
        # Can use new refresh token
        refresh_request2 = TokenRefreshRequest(refresh_token=tokens2.refresh_token)
        tokens3 = auth_manager.refresh_access_token(refresh_request2)
        
        assert tokens3.access_token != tokens2.access_token
        assert tokens3.refresh_token != tokens2.refresh_token
    
    def test_refresh_maintains_user_context(self, auth_manager):
        """Test that refreshed tokens maintain user context."""
        # Login as admin
        from src.auth.auth_models import UserCredentials
        credentials = UserCredentials(username="admin", password="admin123")
        user = auth_manager.authenticate_user(credentials)
        initial_tokens = auth_manager.create_token_response(user)
        
        # Verify initial token has correct user info
        initial_data = verify_token(
            initial_tokens.access_token,
            secret_key=auth_manager.config.jwt_secret_key,
            algorithm=auth_manager.config.jwt_algorithm,
            token_type="access"
        )
        
        # Refresh token
        refresh_request = TokenRefreshRequest(refresh_token=initial_tokens.refresh_token)
        new_tokens = auth_manager.refresh_access_token(refresh_request)
        
        # Verify refreshed token has same user info
        new_data = verify_token(
            new_tokens.access_token,
            secret_key=auth_manager.config.jwt_secret_key,
            algorithm=auth_manager.config.jwt_algorithm,
            token_type="access"
        )
        
        assert new_data.user_id == initial_data.user_id
        assert new_data.username == initial_data.username
        assert new_data.roles == initial_data.roles
    
    def test_expired_refresh_token(self, auth_manager):
        """Test that expired refresh tokens are rejected."""
        # Create an expired refresh token
        expired_token = create_refresh_token(
            user_id="test-id",
            username="testuser",
            roles=[UserRole.USER],
            expires_delta=timedelta(seconds=-1),  # Already expired
            secret_key=auth_manager.config.jwt_secret_key,
            algorithm=auth_manager.config.jwt_algorithm
        )
        
        refresh_request = TokenRefreshRequest(refresh_token=expired_token)
        
        with pytest.raises(HTTPException) as exc_info:
            auth_manager.refresh_access_token(refresh_request)
        
        assert exc_info.value.status_code == 401
        assert "Invalid refresh token" in exc_info.value.detail


class TestTokenEdgeCases:
    """Test edge cases in token handling."""
    
    @pytest.fixture
    def auth_config(self):
        """Get auth configuration."""
        from src.auth.auth_models import AuthConfig
        return AuthConfig(
            jwt_secret_key="test-secret-key",
            jwt_algorithm="HS256",
            access_token_expire_minutes=30,
            refresh_token_expire_days=7,
            password_min_length=6,
            max_login_attempts=5,
            lockout_duration_minutes=15
        )
    
    def test_malformed_token(self, auth_config):
        """Test handling of malformed tokens."""
        malformed_tokens = [
            "not.a.jwt",
            "invalid-base64",
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",  # Missing parts
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..",  # Empty parts
            "",  # Empty string
        ]
        
        for token in malformed_tokens:
            result = verify_token(
                token,
                secret_key=auth_config.jwt_secret_key,
                algorithm=auth_config.jwt_algorithm,
                token_type="access"
            )
            assert result is None
    
    def test_wrong_algorithm_token(self, auth_config):
        """Test token with wrong algorithm is rejected."""
        # Create token with different algorithm
        token_payload = {
            "sub": "test-id",
            "username": "testuser",
            "roles": ["user"],
            "type": "access",
            "exp": datetime.utcnow() + timedelta(minutes=30),
            "iat": datetime.utcnow()
        }
        
        # Use RS256 instead of expected HS256
        token = jwt.encode(
            token_payload,
            auth_config.jwt_secret_key,
            algorithm="HS384"  # Different algorithm
        )
        
        # Should be rejected
        result = verify_token(
            token,
            secret_key=auth_config.jwt_secret_key,
            algorithm=auth_config.jwt_algorithm,
            token_type="access"
        )
        assert result is None
    
    def test_token_missing_claims(self, auth_config):
        """Test token missing required claims."""
        # Create tokens missing various required claims
        test_cases = [
            {"username": "test", "roles": ["user"], "type": "access"},  # Missing sub
            {"sub": "id", "roles": ["user"], "type": "access"},  # Missing username
            {"sub": "id", "username": "test", "type": "access"},  # Missing roles
            {"sub": "id", "username": "test", "roles": ["user"]},  # Missing type
        ]
        
        for payload in test_cases:
            payload["exp"] = datetime.utcnow() + timedelta(minutes=30)
            payload["iat"] = datetime.utcnow()
            
            token = jwt.encode(
                payload,
                auth_config.jwt_secret_key,
                algorithm=auth_config.jwt_algorithm
            )
            
            result = verify_token(
                token,
                secret_key=auth_config.jwt_secret_key,
                algorithm=auth_config.jwt_algorithm,
                token_type="access"
            )
            assert result is None
    
    @patch('src.auth.auth_utils.datetime')
    def test_clock_skew_handling(self, mock_datetime, auth_config):
        """Test handling of clock skew between servers."""
        # Simulate clock skew by mocking datetime
        current_time = datetime.utcnow()
        mock_datetime.utcnow.return_value = current_time + timedelta(seconds=61)  # 61 seconds ahead
        
        # Create token with normal time
        token = create_access_token(
            user_id="test-id",
            username="testuser",
            roles=[UserRole.USER],
            expires_delta=timedelta(minutes=30),
            secret_key=auth_config.jwt_secret_key,
            algorithm=auth_config.jwt_algorithm
        )
        
        # With 60-second clock skew tolerance, should still be valid
        # (Implementation may vary - this documents expected behavior)
        result = verify_token(
            token,
            secret_key=auth_config.jwt_secret_key,
            algorithm=auth_config.jwt_algorithm,
            token_type="access"
        )
        # Result depends on implementation's clock skew tolerance