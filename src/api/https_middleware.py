"""Middleware to enforce HTTPS connections."""

from fastapi import Request
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable

from src.config.ssl_config import ssl_config
from src.utils.logger import get_logger

logger = get_logger(__name__)


class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce HTTPS by redirecting HTTP requests.
    
    This middleware redirects all HTTP requests to HTTPS when SSL is enabled
    and HTTPS enforcement is configured.
    """
    
    # Paths that are exempt from HTTPS enforcement (e.g., health checks)
    EXEMPT_PATHS = [
        "/health",
    ]
    
    async def dispatch(self, request: Request, call_next: Callable):
        """Process each request and enforce HTTPS if configured."""
        
        # Skip enforcement if not configured
        if not ssl_config.should_enforce_https():
            return await call_next(request)
        
        # Skip enforcement for exempt paths
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)
        
        # Check if request is using HTTPS
        # Check both the scheme and X-Forwarded-Proto header (for load balancers)
        is_https = (
            request.url.scheme == "https" or
            request.headers.get("X-Forwarded-Proto") == "https"
        )
        
        if not is_https:
            # Redirect to HTTPS
            https_url = request.url.replace(scheme="https")
            logger.info(f"Redirecting HTTP request to HTTPS: {request.url} -> {https_url}")
            return RedirectResponse(url=str(https_url), status_code=301)
        
        # Add security headers
        response = await call_next(request)
        
        # Strict-Transport-Security header (HSTS)
        # Tells browsers to always use HTTPS for this domain
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # X-Content-Type-Options header
        # Prevents MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # X-Frame-Options header
        # Prevents clickjacking attacks
        response.headers["X-Frame-Options"] = "DENY"
        
        # X-XSS-Protection header
        # Enables browser XSS protection
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Content-Security-Policy header
        # Restricts resource loading to prevent XSS
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self' wss: https:;"
        )
        
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.
    
    This middleware adds various security headers even when HTTPS is not enforced,
    providing defense-in-depth security.
    """
    
    async def dispatch(self, request: Request, call_next: Callable):
        """Add security headers to response."""
        
        response = await call_next(request)
        
        # X-Content-Type-Options
        if "X-Content-Type-Options" not in response.headers:
            response.headers["X-Content-Type-Options"] = "nosniff"
        
        # X-Frame-Options
        if "X-Frame-Options" not in response.headers:
            response.headers["X-Frame-Options"] = "DENY"
        
        # X-XSS-Protection
        if "X-XSS-Protection" not in response.headers:
            response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Referrer-Policy
        if "Referrer-Policy" not in response.headers:
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions-Policy (formerly Feature-Policy)
        if "Permissions-Policy" not in response.headers:
            response.headers["Permissions-Policy"] = (
                "geolocation=(), "
                "microphone=(), "
                "camera=(), "
                "payment=(), "
                "usb=(), "
                "magnetometer=(), "
                "gyroscope=(), "
                "accelerometer=()"
            )
        
        return response
