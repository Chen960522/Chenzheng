"""FastAPI middleware for authentication and authorization."""

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
import time

from src.services.auth_service import AuthenticationService
from src.utils.secure_logger import get_secure_logger

logger = get_secure_logger(__name__)

# Initialize services
auth_service = AuthenticationService()


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """
    Middleware to verify JWT tokens and enforce role-based access control.
    
    This middleware runs on every request and validates authentication headers.
    Public endpoints (login, health check) are excluded from authentication.
    """
    
    # Public endpoints that don't require authentication
    PUBLIC_PATHS = [
        "/",
        "/health",
        "/api/auth/login",
        "/docs",
        "/openapi.json",
        "/redoc"
    ]
    
    async def dispatch(self, request: Request, call_next: Callable):
        """Process each request through the middleware."""
        
        # Skip authentication for public paths
        if request.url.path in self.PUBLIC_PATHS:
            return await call_next(request)
        
        # Skip authentication for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)
        
        # Extract authentication headers
        session_id = request.headers.get("X-Session-ID")
        auth_header = request.headers.get("Authorization")
        
        # Check if authentication headers are present
        if not session_id or not auth_header:
            logger.warning(f"Missing authentication headers for {request.url.path}")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Missing authentication headers"},
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Extract token from Authorization header
        token = auth_header
        if token.startswith("Bearer "):
            token = token[7:]
        
        # Validate session and token
        try:
            user = auth_service.validate_session(session_id, token)
            
            if not user:
                logger.warning(f"Invalid session for {request.url.path}")
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Invalid or expired session"},
                    headers={"WWW-Authenticate": "Bearer"}
                )
            
            # Check if user is active
            if not user.is_active:
                logger.warning(f"Deactivated user attempted access: {user.username}")
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": "User account is deactivated"}
                )
            
            # Store user info in request state for use in endpoints
            request.state.user = {
                "user_id": user.user_id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "full_name": user.full_name
            }
            
            # Log successful authentication
            logger.debug(f"Authenticated user {user.username} for {request.url.path}")
            
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Authentication service error"}
            )
        
        # Continue to the endpoint
        response = await call_next(request)
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce rate limiting per user.
    
    Limits requests to 100 per minute per user.
    """
    
    def __init__(self, app, max_requests: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.request_counts = {}  # {user_id: [(timestamp, count)]}
    
    async def dispatch(self, request: Request, call_next: Callable):
        """Process each request through rate limiting."""
        
        # Skip rate limiting for public paths
        if request.url.path in AuthenticationMiddleware.PUBLIC_PATHS:
            return await call_next(request)
        
        # Get user from request state (set by AuthenticationMiddleware)
        user = getattr(request.state, "user", None)
        
        if not user:
            # If no user in state, authentication middleware will handle it
            return await call_next(request)
        
        user_id = user["user_id"]
        current_time = time.time()
        
        # Initialize user's request history if not exists
        if user_id not in self.request_counts:
            self.request_counts[user_id] = []
        
        # Clean up old requests outside the time window
        self.request_counts[user_id] = [
            (ts, count) for ts, count in self.request_counts[user_id]
            if current_time - ts < self.window_seconds
        ]
        
        # Count requests in current window
        total_requests = sum(count for _, count in self.request_counts[user_id])
        
        # Check if rate limit exceeded
        if total_requests >= self.max_requests:
            logger.warning(f"Rate limit exceeded for user {user_id}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": f"Rate limit exceeded. Maximum {self.max_requests} requests per {self.window_seconds} seconds."
                },
                headers={
                    "Retry-After": str(self.window_seconds),
                    "X-RateLimit-Limit": str(self.max_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(current_time + self.window_seconds))
                }
            )
        
        # Add current request to history
        self.request_counts[user_id].append((current_time, 1))
        
        # Add rate limit headers to response
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(self.max_requests - total_requests - 1)
        response.headers["X-RateLimit-Reset"] = str(int(current_time + self.window_seconds))
        
        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all API requests and responses with secure logging.
    """
    
    async def dispatch(self, request: Request, call_next: Callable):
        """Log request and response details with sanitization."""
        
        start_time = time.time()
        
        # Get user info if available
        user = getattr(request.state, "user", None)
        user_id = user["user_id"] if user else None
        
        # Log request (secure logger will sanitize sensitive data)
        logger.log_request(
            method=request.method,
            path=request.url.path,
            user_id=user_id,
            query_params=dict(request.query_params)
        )
        
        # Process request
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Log response
        logger.log_response(
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration=process_time
        )
        
        # Add processing time header
        response.headers["X-Process-Time"] = str(process_time)
        
        return response
