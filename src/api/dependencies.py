"""FastAPI dependencies for authentication and authorization."""

from fastapi import HTTPException, status, Request, Depends
from typing import Optional, Dict

from src.services.auth_service import AuthenticationService
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Initialize services
auth_service = AuthenticationService()


async def get_current_user(request: Request) -> Dict:
    """
    Dependency to get the current authenticated user.
    
    Validates session and token from request headers.
    Returns user information if valid, raises HTTPException otherwise.
    """
    session_id = request.headers.get("X-Session-ID")
    token = request.headers.get("Authorization")
    
    if not session_id or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication headers",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Remove "Bearer " prefix if present
    if token.startswith("Bearer "):
        token = token[7:]
    
    # Validate session
    user = auth_service.validate_session(session_id, token)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated"
        )
    
    return {
        "user_id": user.user_id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "full_name": user.full_name
    }


async def require_auth(current_user: Dict = Depends(get_current_user)) -> Dict:
    """
    Dependency to require authentication.
    
    Simply returns the current user from get_current_user.
    """
    return current_user


async def require_admin(current_user: Dict = Depends(get_current_user)) -> Dict:
    """
    Dependency to require admin role.
    
    Validates that the current user has admin role.
    """
    if current_user['role'] != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    return current_user


async def optional_auth(request: Request) -> Optional[Dict]:
    """
    Dependency for optional authentication.
    
    Returns user information if authenticated, None otherwise.
    """
    try:
        return await get_current_user(request)
    except HTTPException:
        return None
