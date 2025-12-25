"""Unit tests for authentication service."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock
from passlib.context import CryptContext
from jose import jwt


# Simple test without full imports
class TestPasswordHashingUnit:
    """Test password hashing functionality without full service."""
    
    def test_argon2_hash_creates_valid_hash(self):
        """Test that Argon2 creates a valid hash."""
        pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
        password = "test_password_123"
        hashed = pwd_context.hash(password)
        
        assert hashed.startswith("$argon2id$")
        assert hashed != password
        assert pwd_context.verify(password, hashed) is True
    
    def test_argon2_verify_with_incorrect_password(self):
        """Test that verification fails with incorrect password."""
        pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
        password = "test_password_123"
        wrong_password = "wrong_password"
        hashed = pwd_context.hash(password)
        
        assert pwd_context.verify(wrong_password, hashed) is False


class TestJWTTokens:
    """Test JWT token functionality."""
    
    def test_create_and_verify_jwt_token(self):
        """Test creating and verifying a JWT token."""
        secret_key = "test-secret-key"
        algorithm = "HS256"
        
        # Create token
        expire = datetime.utcnow() + timedelta(minutes=30)
        payload = {
            "sub": "user-123",
            "username": "testuser",
            "role": "sales",
            "exp": expire
        }
        token = jwt.encode(payload, secret_key, algorithm=algorithm)
        
        # Verify token
        decoded = jwt.decode(token, secret_key, algorithms=[algorithm])
        assert decoded["sub"] == "user-123"
        assert decoded["username"] == "testuser"
        assert decoded["role"] == "sales"
    
    def test_expired_token_fails_verification(self):
        """Test that expired tokens fail verification."""
        secret_key = "test-secret-key"
        algorithm = "HS256"
        
        # Create expired token
        expire = datetime.utcnow() - timedelta(minutes=1)
        payload = {
            "sub": "user-123",
            "exp": expire
        }
        token = jwt.encode(payload, secret_key, algorithm=algorithm)
        
        # Verify token fails
        from jose import JWTError
        with pytest.raises(JWTError):
            jwt.decode(token, secret_key, algorithms=[algorithm])
    
    def test_invalid_token_fails_verification(self):
        """Test that invalid tokens fail verification."""
        secret_key = "test-secret-key"
        algorithm = "HS256"
        invalid_token = "invalid.token.here"
        
        from jose import JWTError
        with pytest.raises(JWTError):
            jwt.decode(invalid_token, secret_key, algorithms=[algorithm])


class TestUserModel:
    """Test User model functionality."""
    
    def test_user_to_dynamodb_item(self):
        """Test converting User to DynamoDB item."""
        from src.models.user import User
        
        user = User(
            user_id="test-123",
            username="testuser",
            email="test@example.com",
            password_hash="hash123",
            role="sales",
            full_name="Test User",
            created_at=datetime(2024, 1, 1, 12, 0, 0),
            is_active=True
        )
        
        item = user.to_dynamodb_item()
        
        assert item["user_id"] == "test-123"
        assert item["username"] == "testuser"
        assert item["email"] == "test@example.com"
        assert item["role"] == "sales"
        assert item["is_active"] is True
    
    def test_user_from_dynamodb_item(self):
        """Test creating User from DynamoDB item."""
        from src.models.user import User
        
        item = {
            "user_id": "test-123",
            "username": "testuser",
            "email": "test@example.com",
            "password_hash": "hash123",
            "role": "sales",
            "full_name": "Test User",
            "created_at": "2024-01-01T12:00:00",
            "is_active": True
        }
        
        user = User.from_dynamodb_item(item)
        
        assert user.user_id == "test-123"
        assert user.username == "testuser"
        assert user.is_active is True


class TestSessionModel:
    """Test Session model functionality."""
    
    def test_session_to_dynamodb_item(self):
        """Test converting Session to DynamoDB item."""
        from src.models.user import Session
        
        session = Session(
            session_id="session-123",
            user_id="user-123",
            token="token123",
            created_at=datetime(2024, 1, 1, 12, 0, 0),
            expires_at=datetime(2024, 1, 1, 12, 30, 0),
            ip_address="127.0.0.1",
            user_agent="test-agent"
        )
        
        item = session.to_dynamodb_item()
        
        assert item["session_id"] == "session-123"
        assert item["user_id"] == "user-123"
        assert item["token"] == "token123"
        assert item["ip_address"] == "127.0.0.1"
    
    def test_session_is_expired(self):
        """Test session expiration check."""
        from src.models.user import Session
        
        # Create expired session
        expired_session = Session(
            session_id="session-123",
            user_id="user-123",
            token="token123",
            created_at=datetime.utcnow() - timedelta(hours=1),
            expires_at=datetime.utcnow() - timedelta(minutes=30),
            ip_address="127.0.0.1",
            user_agent="test-agent"
        )
        
        assert expired_session.is_expired() is True
        
        # Create valid session
        valid_session = Session(
            session_id="session-456",
            user_id="user-123",
            token="token456",
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(minutes=30),
            ip_address="127.0.0.1",
            user_agent="test-agent"
        )
        
        assert valid_session.is_expired() is False
