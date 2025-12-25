"""Request validation and sanitization utilities."""

import re
import html
from typing import Any, Optional
from fastapi import HTTPException, status

from src.utils.logger import get_logger

logger = get_logger(__name__)


# Validation patterns
USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{3,50}$')
PASSWORD_MIN_LENGTH = 8
QUOTE_ID_PATTERN = re.compile(r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$')
REGION_PATTERN = re.compile(r'^[a-z]{2}-[a-z]+-\d{1}$|^us-gov-[a-z]+-\d{1}$|^cn-[a-z]+-\d{1}$')


def sanitize_string(value: str, max_length: Optional[int] = None) -> str:
    """
    Sanitize a string input.
    
    - Strips leading/trailing whitespace
    - Escapes HTML entities
    - Optionally truncates to max_length
    """
    if not isinstance(value, str):
        raise ValueError("Value must be a string")
    
    # Strip whitespace
    sanitized = value.strip()
    
    # Escape HTML entities to prevent XSS
    sanitized = html.escape(sanitized)
    
    # Truncate if needed
    if max_length and len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    
    return sanitized


def validate_username(username: str) -> str:
    """
    Validate and sanitize username.
    
    Rules:
    - 3-50 characters
    - Alphanumeric, underscore, and hyphen only
    """
    username = sanitize_string(username, max_length=50)
    
    if not USERNAME_PATTERN.match(username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username must be 3-50 characters and contain only letters, numbers, underscores, and hyphens"
        )
    
    return username


def validate_password(password: str) -> str:
    """
    Validate password strength.
    
    Rules:
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character
    """
    if len(password) < PASSWORD_MIN_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Password must be at least {PASSWORD_MIN_LENGTH} characters long"
        )
    
    if not re.search(r'[A-Z]', password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one uppercase letter"
        )
    
    if not re.search(r'[a-z]', password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one lowercase letter"
        )
    
    if not re.search(r'\d', password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one digit"
        )
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one special character"
        )
    
    return password


def validate_email(email: str) -> str:
    """
    Validate and sanitize email address.
    """
    email = sanitize_string(email, max_length=255)
    
    # Basic email validation (Pydantic EmailStr does more thorough validation)
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email address format"
        )
    
    return email.lower()


def validate_role(role: str) -> str:
    """
    Validate user role.
    
    Allowed roles: admin, sales
    """
    role = sanitize_string(role).lower()
    
    if role not in ['admin', 'sales']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role. Must be 'admin' or 'sales'"
        )
    
    return role


def validate_quote_id(quote_id: str) -> str:
    """
    Validate quote ID format (UUID).
    """
    quote_id = sanitize_string(quote_id)
    
    if not QUOTE_ID_PATTERN.match(quote_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid quote ID format"
        )
    
    return quote_id


def validate_user_id(user_id: str) -> str:
    """
    Validate user ID format (UUID).
    """
    user_id = sanitize_string(user_id)
    
    if not QUOTE_ID_PATTERN.match(user_id):  # Same pattern as quote_id
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format"
        )
    
    return user_id


def validate_region(region: str) -> str:
    """
    Validate AWS region format.
    
    Examples: us-east-1, eu-west-2, ap-southeast-1, us-gov-west-1, cn-north-1
    """
    region = sanitize_string(region).lower()
    
    if not REGION_PATTERN.match(region):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid AWS region format"
        )
    
    return region


def validate_pricing_model(pricing_model: str) -> str:
    """
    Validate pricing model.
    
    Allowed models: on-demand, reserved, savings-plan
    """
    pricing_model = sanitize_string(pricing_model).lower()
    
    if pricing_model not in ['on-demand', 'reserved', 'savings-plan']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid pricing model. Must be 'on-demand', 'reserved', or 'savings-plan'"
        )
    
    return pricing_model


def validate_export_format(format: str) -> str:
    """
    Validate export format.
    
    Allowed formats: pdf, excel, json
    """
    format = sanitize_string(format).lower()
    
    if format not in ['pdf', 'excel', 'json']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid export format. Must be 'pdf', 'excel', or 'json'"
        )
    
    return format


def validate_quote_status(status_value: str) -> str:
    """
    Validate quote status.
    
    Allowed statuses: draft, finalized, sent
    """
    status_value = sanitize_string(status_value).lower()
    
    if status_value not in ['draft', 'finalized', 'sent']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid quote status. Must be 'draft', 'finalized', or 'sent'"
        )
    
    return status_value


def sanitize_configuration_text(text: str) -> str:
    """
    Sanitize configuration text input.
    
    - Strips leading/trailing whitespace
    - Limits to reasonable size (1MB)
    - Does NOT escape HTML since this is configuration data
    """
    if not isinstance(text, str):
        raise ValueError("Configuration text must be a string")
    
    # Strip whitespace
    sanitized = text.strip()
    
    # Check size limit (1MB)
    max_size = 1024 * 1024  # 1MB
    if len(sanitized.encode('utf-8')) > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Configuration text exceeds maximum size of 1MB"
        )
    
    # Check for empty input
    if not sanitized:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Configuration text cannot be empty"
        )
    
    return sanitized


def validate_pagination(limit: int, offset: int) -> tuple:
    """
    Validate pagination parameters.
    
    - limit: 1-1000
    - offset: >= 0
    """
    if limit < 1 or limit > 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Limit must be between 1 and 1000"
        )
    
    if offset < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Offset must be non-negative"
        )
    
    return limit, offset


def sanitize_notes(notes: Optional[str]) -> Optional[str]:
    """
    Sanitize notes field.
    
    - Strips whitespace
    - Escapes HTML
    - Limits to 5000 characters
    """
    if notes is None:
        return None
    
    return sanitize_string(notes, max_length=5000)
