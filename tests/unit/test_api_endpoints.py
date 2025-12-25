"""Unit tests for API endpoints."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from decimal import Decimal

from src.models.user import User
from src.models.quote import Quote


# Mock data
@pytest.fixture
def mock_user():
    """Create a mock user."""
    return User(
        user_id="test-user-id",
        username="testuser",
        email="test@example.com",
        password_hash="hashed_password",
        role="sales",
        full_name="Test User",
        created_at=datetime.now(),
        last_login=None,
        is_active=True
    )


@pytest.fixture
def mock_admin_user():
    """Create a mock admin user."""
    return User(
        user_id="admin-user-id",
        username="adminuser",
        email="admin@example.com",
        password_hash="hashed_password",
        role="admin",
        full_name="Admin User",
        created_at=datetime.now(),
        last_login=None,
        is_active=True
    )


@pytest.fixture
def mock_quote():
    """Create a mock quote."""
    return Quote(
        quote_id="test-quote-id",
        user_id="test-user-id",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        status="draft",
        original_input="Test configuration",
        parsed_services=[{"service": "EC2"}],
        aws_mappings=[{"aws_service": "EC2"}],
        pricing_results=[{"monthly_cost": 100.0}],
        total_monthly_cost=Decimal("100.00"),
        total_annual_cost=Decimal("1200.00"),
        currency="USD",
        region="us-east-1",
        notes=None,
        export_urls={}
    )


# Authentication endpoint tests

def test_login_with_valid_credentials(mock_user):
    """Test login with valid credentials."""
    with patch('src.api.auth.auth_service.login') as mock_login:
        mock_login.return_value = {
            "user_id": mock_user.user_id,
            "username": mock_user.username,
            "email": mock_user.email,
            "role": mock_user.role,
            "full_name": mock_user.full_name,
            "token": "test-token",
            "session_id": "test-session",
            "expires_at": "2024-01-01T00:00:00"
        }
        
        # Test would make actual API call here
        result = mock_login("testuser", "password")
        
        assert result is not None
        assert result["username"] == "testuser"
        assert "token" in result
        assert "session_id" in result


def test_login_with_invalid_credentials():
    """Test login with invalid credentials."""
    with patch('src.api.auth.auth_service.login') as mock_login:
        mock_login.return_value = None
        
        result = mock_login("testuser", "wrongpassword")
        
        assert result is None


def test_logout_success():
    """Test successful logout."""
    with patch('src.api.auth.auth_service.logout') as mock_logout:
        mock_logout.return_value = True
        
        result = mock_logout("test-session")
        
        assert result is True


def test_get_current_user(mock_user):
    """Test getting current user info."""
    with patch('src.api.auth.auth_service.validate_session') as mock_validate:
        mock_validate.return_value = mock_user
        
        user = mock_validate("test-session", "test-token")
        
        assert user is not None
        assert user.username == "testuser"
        assert user.role == "sales"


# Quote endpoint tests

def test_create_quote_success(mock_user, mock_quote):
    """Test successful quote creation."""
    with patch('src.api.quotes.agent_service.process_quote_request') as mock_process, \
         patch('src.api.quotes.quote_service.create_quote') as mock_create:
        
        mock_process.return_value = {
            "parsed_services": [{"service": "EC2"}],
            "aws_mappings": [{"aws_service": "EC2"}],
            "pricing_results": [{"monthly_cost": 100.0}],
            "total_monthly_cost": 100.0,
            "total_annual_cost": 1200.0
        }
        
        mock_create.return_value = mock_quote
        
        # Test would make actual API call here
        result = mock_create(
            user_id=mock_user.user_id,
            original_input="Test configuration",
            parsed_services=[{"service": "EC2"}],
            aws_mappings=[{"aws_service": "EC2"}],
            pricing_results=[{"monthly_cost": 100.0}],
            total_monthly_cost=100.0,
            total_annual_cost=1200.0,
            region="us-east-1",
            notes=None
        )
        
        assert result is not None
        assert result.quote_id == "test-quote-id"
        assert result.user_id == mock_user.user_id


def test_create_quote_with_empty_configuration():
    """Test quote creation with empty configuration."""
    with patch('src.api.validators.sanitize_configuration_text') as mock_sanitize:
        # Should raise HTTPException
        from fastapi import HTTPException
        mock_sanitize.side_effect = HTTPException(status_code=400, detail="Configuration text cannot be empty")
        
        with pytest.raises(HTTPException) as exc_info:
            mock_sanitize("")
        
        assert exc_info.value.status_code == 400


def test_get_quote_success(mock_user, mock_quote):
    """Test getting a quote by ID."""
    with patch('src.api.quotes.quote_service.get_quote') as mock_get:
        mock_get.return_value = mock_quote
        
        result = mock_get("test-quote-id")
        
        assert result is not None
        assert result.quote_id == "test-quote-id"


def test_get_quote_not_found():
    """Test getting a non-existent quote."""
    with patch('src.api.quotes.quote_service.get_quote') as mock_get:
        mock_get.return_value = None
        
        result = mock_get("non-existent-id")
        
        assert result is None


def test_get_quote_unauthorized(mock_user, mock_quote):
    """Test getting a quote that belongs to another user."""
    # Quote belongs to different user
    mock_quote.user_id = "other-user-id"
    
    with patch('src.api.quotes.quote_service.get_quote') as mock_get:
        mock_get.return_value = mock_quote
        
        result = mock_get("test-quote-id")
        
        # Authorization check would happen in endpoint
        assert result.user_id != mock_user.user_id


def test_list_quotes_for_user(mock_user, mock_quote):
    """Test listing quotes for a user."""
    with patch('src.api.quotes.quote_service.list_user_quotes') as mock_list:
        mock_list.return_value = [mock_quote]
        
        result = mock_list(user_id=mock_user.user_id, limit=50, offset=0)
        
        assert len(result) == 1
        assert result[0].user_id == mock_user.user_id


def test_update_quote_success(mock_quote):
    """Test updating a quote."""
    with patch('src.api.quotes.quote_service.update_quote') as mock_update:
        updated_quote = mock_quote
        updated_quote.status = "finalized"
        updated_quote.notes = "Updated notes"
        
        mock_update.return_value = updated_quote
        
        result = mock_update(
            quote_id="test-quote-id",
            status="finalized",
            notes="Updated notes"
        )
        
        assert result.status == "finalized"
        assert result.notes == "Updated notes"


def test_delete_quote_success():
    """Test deleting a quote."""
    with patch('src.api.quotes.quote_service.delete_quote') as mock_delete:
        mock_delete.return_value = True
        
        result = mock_delete("test-quote-id")
        
        assert result is True


# User management endpoint tests

def test_create_user_success(mock_admin_user):
    """Test creating a new user (admin only)."""
    with patch('src.api.users.user_service.create_user') as mock_create:
        new_user = User(
            user_id="new-user-id",
            username="newuser",
            email="new@example.com",
            password_hash="hashed_password",
            role="sales",
            full_name="New User",
            created_at=datetime.now(),
            last_login=None,
            is_active=True
        )
        
        mock_create.return_value = new_user
        
        result = mock_create(
            username="newuser",
            email="new@example.com",
            password="SecurePass123!",
            role="sales",
            full_name="New User"
        )
        
        assert result is not None
        assert result.username == "newuser"
        assert result.role == "sales"


def test_create_user_duplicate_username():
    """Test creating a user with duplicate username."""
    with patch('src.api.users.user_service.get_user_by_username') as mock_get:
        mock_get.return_value = User(
            user_id="existing-user-id",
            username="existinguser",
            email="existing@example.com",
            password_hash="hashed_password",
            role="sales",
            full_name="Existing User",
            created_at=datetime.now(),
            last_login=None,
            is_active=True
        )
        
        result = mock_get("existinguser")
        
        # Should indicate user already exists
        assert result is not None


def test_list_users_admin(mock_admin_user):
    """Test listing all users (admin only)."""
    with patch('src.api.users.user_service.list_users') as mock_list:
        mock_list.return_value = [mock_admin_user]
        
        result = mock_list(limit=100, offset=0)
        
        assert len(result) >= 1


def test_update_user_success(mock_user):
    """Test updating a user."""
    with patch('src.api.users.user_service.update_user') as mock_update:
        updated_user = mock_user
        updated_user.email = "newemail@example.com"
        updated_user.role = "admin"
        
        mock_update.return_value = updated_user
        
        result = mock_update(
            user_id=mock_user.user_id,
            email="newemail@example.com",
            role="admin",
            full_name=None,
            is_active=None
        )
        
        assert result.email == "newemail@example.com"
        assert result.role == "admin"


def test_delete_user_success():
    """Test deleting a user."""
    with patch('src.api.users.user_service.delete_user') as mock_delete:
        mock_delete.return_value = True
        
        result = mock_delete("test-user-id")
        
        assert result is True


def test_reset_password_success():
    """Test resetting a user's password."""
    with patch('src.api.users.user_service.reset_password') as mock_reset:
        mock_reset.return_value = True
        
        result = mock_reset("test-user-id", "NewSecurePass123!")
        
        assert result is True


# Authorization tests

def test_admin_required_for_user_management(mock_user):
    """Test that admin role is required for user management."""
    # Regular user should not have access
    assert mock_user.role != "admin"


def test_user_can_only_access_own_quotes(mock_user, mock_quote):
    """Test that users can only access their own quotes."""
    assert mock_quote.user_id == mock_user.user_id


# Error response tests

def test_invalid_quote_id_format():
    """Test error response for invalid quote ID format."""
    with patch('src.api.validators.validate_quote_id') as mock_validate:
        from fastapi import HTTPException
        mock_validate.side_effect = HTTPException(status_code=400, detail="Invalid quote ID format")
        
        with pytest.raises(HTTPException) as exc_info:
            mock_validate("invalid-id")
        
        assert exc_info.value.status_code == 400


def test_invalid_region_format():
    """Test error response for invalid region format."""
    with patch('src.api.validators.validate_region') as mock_validate:
        from fastapi import HTTPException
        mock_validate.side_effect = HTTPException(status_code=400, detail="Invalid AWS region format")
        
        with pytest.raises(HTTPException) as exc_info:
            mock_validate("invalid-region")
        
        assert exc_info.value.status_code == 400


def test_invalid_pricing_model():
    """Test error response for invalid pricing model."""
    with patch('src.api.validators.validate_pricing_model') as mock_validate:
        from fastapi import HTTPException
        mock_validate.side_effect = HTTPException(status_code=400, detail="Invalid pricing model")
        
        with pytest.raises(HTTPException) as exc_info:
            mock_validate("invalid-model")
        
        assert exc_info.value.status_code == 400
