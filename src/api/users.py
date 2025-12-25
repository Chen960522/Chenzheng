"""User management API endpoints (Admin only)."""

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr
from typing import Optional, List

from src.services.user_service import UserService
from src.models.user import User
from src.utils.logger import get_logger
from .dependencies import get_current_user, require_admin
from .validators import (
    validate_username, validate_password, validate_email,
    validate_role, validate_user_id, validate_pagination
)

logger = get_logger(__name__)

router = APIRouter(prefix="/api/users", tags=["users"])

# Initialize services
user_service = UserService()


# Request/Response Models

class CreateUserRequest(BaseModel):
    """Create user request model."""
    username: str
    email: EmailStr
    password: str
    role: str = "sales"  # Default role
    full_name: str


class UpdateUserRequest(BaseModel):
    """Update user request model."""
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None


class ResetPasswordRequest(BaseModel):
    """Reset password request model."""
    new_password: str


class UserResponse(BaseModel):
    """User response model."""
    user_id: str
    username: str
    email: str
    role: str
    full_name: str
    is_active: bool
    created_at: str
    last_login: Optional[str]


class UserListResponse(BaseModel):
    """User list response model."""
    users: List[UserResponse]
    total: int


# Endpoints

@router.post("/create", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: CreateUserRequest,
    current_user: dict = Depends(require_admin)
):
    """
    Create a new user (Admin only).
    
    Creates a new user account with the specified role.
    """
    try:
        logger.info(f"Admin {current_user['user_id']} creating new user: {user_data.username}")
        
        # Validate and sanitize inputs
        username = validate_username(user_data.username)
        email = validate_email(user_data.email)
        password = validate_password(user_data.password)
        role = validate_role(user_data.role)
        
        # Check if username already exists
        existing_user = user_service.get_user_by_username(username)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already exists"
            )
        
        # Create user
        user = user_service.create_user(
            username=username,
            email=email,
            password=password,
            role=role,
            full_name=user_data.full_name
        )
        
        return _user_to_response(user)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )


@router.get("/list", response_model=UserListResponse, status_code=status.HTTP_200_OK)
async def list_users(
    limit: int = 100,
    offset: int = 0,
    current_user: dict = Depends(require_admin)
):
    """
    List all users (Admin only).
    
    Returns a paginated list of all users in the system.
    """
    try:
        # Validate pagination
        limit, offset = validate_pagination(limit, offset)
        
        users = user_service.list_users(limit=limit, offset=offset)
        
        return UserListResponse(
            users=[_user_to_response(u) for u in users],
            total=len(users)
        )
        
    except Exception as e:
        logger.error(f"Error listing users: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list users"
        )


@router.put("/{user_id}", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def update_user(
    user_id: str,
    update_data: UpdateUserRequest,
    current_user: dict = Depends(require_admin)
):
    """
    Update a user (Admin only).
    
    Updates user information including role and active status.
    """
    try:
        logger.info(f"Admin {current_user['user_id']} updating user: {user_id}")
        
        # Validate inputs
        user_id = validate_user_id(user_id)
        if update_data.email:
            update_data.email = validate_email(update_data.email)
        if update_data.role:
            update_data.role = validate_role(update_data.role)
        
        user = user_service.get_user(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Update user
        updated_user = user_service.update_user(
            user_id=user_id,
            email=update_data.email,
            role=update_data.role,
            full_name=update_data.full_name,
            is_active=update_data.is_active
        )
        
        return _user_to_response(updated_user)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user"
        )


@router.delete("/{user_id}", status_code=status.HTTP_200_OK)
async def delete_user(
    user_id: str,
    current_user: dict = Depends(require_admin)
):
    """
    Delete a user (Admin only).
    
    Permanently deletes a user account.
    """
    try:
        logger.info(f"Admin {current_user['user_id']} deleting user: {user_id}")
        
        # Prevent self-deletion
        if user_id == current_user['user_id']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete your own account"
            )
        
        user = user_service.get_user(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Delete user
        success = user_service.delete_user(user_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete user"
            )
        
        return {"message": "User deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user"
        )


@router.post("/{user_id}/reset-password", status_code=status.HTTP_200_OK)
async def reset_user_password(
    user_id: str,
    reset_data: ResetPasswordRequest,
    current_user: dict = Depends(require_admin)
):
    """
    Reset a user's password (Admin only).
    
    Sets a new password for the specified user.
    """
    try:
        logger.info(f"Admin {current_user['user_id']} resetting password for user: {user_id}")
        
        # Validate inputs
        user_id = validate_user_id(user_id)
        new_password = validate_password(reset_data.new_password)
        
        user = user_service.get_user(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Reset password
        success = user_service.reset_password(user_id, new_password)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to reset password"
            )
        
        return {"message": "Password reset successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting password: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset password"
        )


# Helper functions

def _user_to_response(user: User) -> UserResponse:
    """Convert User model to UserResponse."""
    return UserResponse(
        user_id=user.user_id,
        username=user.username,
        email=user.email,
        role=user.role,
        full_name=user.full_name,
        is_active=user.is_active,
        created_at=user.created_at.isoformat(),
        last_login=user.last_login.isoformat() if user.last_login else None
    )
