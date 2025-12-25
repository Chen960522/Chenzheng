"""Authentication API endpoints."""

from fastapi import APIRouter, HTTPException, status, Depends, Request
from pydantic import BaseModel, EmailStr
from typing import Optional

from src.services.auth_service import AuthenticationService
from src.services.user_service import UserService
from src.models.user import User
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/auth", tags=["authentication"])

# Initialize services
auth_service = AuthenticationService()
user_service = UserService()


# Request/Response Models

class LoginRequest(BaseModel):
    """Login request model."""
    username: str
    password: str


class LoginResponse(BaseModel):
    """Login response model."""
    user_id: str
    username: str
    email: str
    role: str
    full_name: str
    token: str
    session_id: str
    expires_at: str


class RefreshTokenRequest(BaseModel):
    """Refresh token request model."""
    token: str


class RefreshTokenResponse(BaseModel):
    """Refresh token response model."""
    token: str


class LogoutRequest(BaseModel):
    """Logout request model."""
    session_id: str


class UserInfoResponse(BaseModel):
    """User info response model."""
    user_id: str
    username: str
    email: str
    role: str
    full_name: str
    is_active: bool
    created_at: str
    last_login: Optional[str]


# Helper functions

def get_client_info(request: Request) -> tuple:
    """Extract client IP and user agent from request."""
    ip_address = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    return ip_address, user_agent


# Endpoints

@router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
async def login(request: Request, login_data: LoginRequest):
    """
    Login endpoint.
    
    Authenticates user and creates a session.
    """
    ip_address, user_agent = get_client_info(request)
    
    result = auth_service.login(
        username=login_data.username,
        password=login_data.password,
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    return LoginResponse(**result)


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(logout_data: LogoutRequest):
    """
    Logout endpoint.
    
    Deletes the user session.
    """
    success = auth_service.logout(logout_data.session_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to logout"
        )
    
    return {"message": "Logged out successfully"}


@router.post("/refresh", response_model=RefreshTokenResponse, status_code=status.HTTP_200_OK)
async def refresh_token(refresh_data: RefreshTokenRequest):
    """
    Refresh token endpoint.
    
    Generates a new access token from an existing valid token.
    """
    new_token = auth_service.refresh_token(refresh_data.token)
    
    if not new_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    return RefreshTokenResponse(token=new_token)


@router.get("/me", response_model=UserInfoResponse, status_code=status.HTTP_200_OK)
async def get_current_user(request: Request):
    """
    Get current user info endpoint.
    
    Returns information about the currently authenticated user.
    Requires valid session_id and token in headers.
    """
    session_id = request.headers.get("X-Session-ID")
    token = request.headers.get("Authorization")
    
    if not session_id or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication headers"
        )
    
    # Remove "Bearer " prefix if present
    if token.startswith("Bearer "):
        token = token[7:]
    
    user = auth_service.validate_session(session_id, token)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session"
        )
    
    return UserInfoResponse(
        user_id=user.user_id,
        username=user.username,
        email=user.email,
        role=user.role,
        full_name=user.full_name,
        is_active=user.is_active,
        created_at=user.created_at.isoformat(),
        last_login=user.last_login.isoformat() if user.last_login else None
    )
