"""Secure logging utilities that sanitize sensitive information."""

import re
import logging
from typing import Any, Dict, Optional
import json

from src.utils.logger import get_logger

# Patterns for sensitive data
SENSITIVE_PATTERNS = {
    'password': re.compile(r'(password|passwd|pwd)["\']?\s*[:=]\s*["\']?([^"\'\s,}]+)', re.IGNORECASE),
    'token': re.compile(r'(token|jwt|bearer)["\']?\s*[:=]\s*["\']?([^"\'\s,}]+)', re.IGNORECASE),
    'api_key': re.compile(r'(api[_-]?key|apikey)["\']?\s*[:=]\s*["\']?([^"\'\s,}]+)', re.IGNORECASE),
    'secret': re.compile(r'(secret|secret[_-]?key)["\']?\s*[:=]\s*["\']?([^"\'\s,}]+)', re.IGNORECASE),
    'credit_card': re.compile(r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b'),
    'ssn': re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
    'email': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
    'phone': re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'),
    'aws_access_key': re.compile(r'AKIA[0-9A-Z]{16}'),
    'aws_secret_key': re.compile(r'[A-Za-z0-9/+=]{40}'),
}

# Fields that should be redacted in structured logs
SENSITIVE_FIELDS = {
    'password',
    'password_hash',
    'token',
    'access_token',
    'refresh_token',
    'jwt',
    'api_key',
    'secret',
    'secret_key',
    'aws_access_key_id',
    'aws_secret_access_key',
    'credit_card',
    'ssn',
    'social_security_number',
}


class SensitiveDataFilter(logging.Filter):
    """
    Logging filter that redacts sensitive information from log messages.
    
    This filter scans log messages for patterns that match sensitive data
    (passwords, tokens, API keys, etc.) and replaces them with [REDACTED].
    """
    
    def __init__(self, name: str = ''):
        super().__init__(name)
        self.redaction_text = '[REDACTED]'
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        Filter log record to redact sensitive information.
        
        Args:
            record: Log record to filter
        
        Returns:
            True (always allow the record, but modify it)
        """
        # Sanitize the message
        if isinstance(record.msg, str):
            record.msg = self.sanitize_text(record.msg)
        
        # Sanitize arguments
        if record.args:
            if isinstance(record.args, dict):
                record.args = self.sanitize_dict(record.args)
            elif isinstance(record.args, (list, tuple)):
                record.args = tuple(
                    self.sanitize_text(str(arg)) if isinstance(arg, str) else arg
                    for arg in record.args
                )
        
        return True
    
    def sanitize_text(self, text: str) -> str:
        """
        Sanitize text by replacing sensitive patterns.
        
        Args:
            text: Text to sanitize
        
        Returns:
            Sanitized text
        """
        for pattern_name, pattern in SENSITIVE_PATTERNS.items():
            if pattern_name in ['password', 'token', 'api_key', 'secret']:
                # For key-value patterns, keep the key but redact the value
                text = pattern.sub(r'\1: ' + self.redaction_text, text)
            else:
                # For other patterns, redact the entire match
                text = pattern.sub(self.redaction_text, text)
        
        return text
    
    def sanitize_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize dictionary by redacting sensitive fields.
        
        Args:
            data: Dictionary to sanitize
        
        Returns:
            Sanitized dictionary
        """
        sanitized = {}
        
        for key, value in data.items():
            # Check if key is sensitive
            if key.lower() in SENSITIVE_FIELDS:
                sanitized[key] = self.redaction_text
            elif isinstance(value, dict):
                sanitized[key] = self.sanitize_dict(value)
            elif isinstance(value, str):
                sanitized[key] = self.sanitize_text(value)
            elif isinstance(value, (list, tuple)):
                sanitized[key] = [
                    self.sanitize_dict(item) if isinstance(item, dict)
                    else self.sanitize_text(item) if isinstance(item, str)
                    else item
                    for item in value
                ]
            else:
                sanitized[key] = value
        
        return sanitized


class SecureLogger:
    """
    Secure logger wrapper that automatically sanitizes sensitive information.
    
    This class wraps the standard logger and ensures all log messages
    are sanitized before being written.
    """
    
    def __init__(self, name: str):
        """
        Initialize secure logger.
        
        Args:
            name: Logger name
        """
        self.logger = get_logger(name)
        
        # Add sensitive data filter to all handlers
        sensitive_filter = SensitiveDataFilter()
        for handler in self.logger.handlers:
            handler.addFilter(sensitive_filter)
    
    def debug(self, msg: str, *args, **kwargs):
        """Log debug message with sanitization."""
        self.logger.debug(msg, *args, **kwargs)
    
    def info(self, msg: str, *args, **kwargs):
        """Log info message with sanitization."""
        self.logger.info(msg, *args, **kwargs)
    
    def warning(self, msg: str, *args, **kwargs):
        """Log warning message with sanitization."""
        self.logger.warning(msg, *args, **kwargs)
    
    def error(self, msg: str, *args, **kwargs):
        """Log error message with sanitization."""
        self.logger.error(msg, *args, **kwargs)
    
    def critical(self, msg: str, *args, **kwargs):
        """Log critical message with sanitization."""
        self.logger.critical(msg, *args, **kwargs)
    
    def exception(self, msg: str, *args, **kwargs):
        """Log exception with sanitization."""
        self.logger.exception(msg, *args, **kwargs)
    
    def log_request(self, method: str, path: str, user_id: Optional[str] = None, **kwargs):
        """
        Log API request with sanitized parameters.
        
        Args:
            method: HTTP method
            path: Request path
            user_id: Optional user ID
            **kwargs: Additional parameters to log
        """
        # Sanitize kwargs
        filter = SensitiveDataFilter()
        sanitized_kwargs = filter.sanitize_dict(kwargs)
        
        log_data = {
            'method': method,
            'path': path,
            'user_id': user_id,
            **sanitized_kwargs
        }
        
        self.info(f"API Request: {json.dumps(log_data)}")
    
    def log_response(self, method: str, path: str, status_code: int, duration: float, **kwargs):
        """
        Log API response with sanitized data.
        
        Args:
            method: HTTP method
            path: Request path
            status_code: Response status code
            duration: Request duration in seconds
            **kwargs: Additional parameters to log
        """
        # Sanitize kwargs
        filter = SensitiveDataFilter()
        sanitized_kwargs = filter.sanitize_dict(kwargs)
        
        log_data = {
            'method': method,
            'path': path,
            'status_code': status_code,
            'duration': f"{duration:.3f}s",
            **sanitized_kwargs
        }
        
        self.info(f"API Response: {json.dumps(log_data)}")
    
    def log_security_event(self, event_type: str, user_id: Optional[str] = None, **kwargs):
        """
        Log security event with sanitized data.
        
        Args:
            event_type: Type of security event
            user_id: Optional user ID
            **kwargs: Additional parameters to log
        """
        # Sanitize kwargs
        filter = SensitiveDataFilter()
        sanitized_kwargs = filter.sanitize_dict(kwargs)
        
        log_data = {
            'event_type': event_type,
            'user_id': user_id,
            **sanitized_kwargs
        }
        
        self.warning(f"Security Event: {json.dumps(log_data)}")


def get_secure_logger(name: str) -> SecureLogger:
    """
    Get a secure logger instance.
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        SecureLogger instance
    """
    return SecureLogger(name)


def sanitize_for_logging(data: Any) -> Any:
    """
    Sanitize data for logging.
    
    This is a utility function that can be used to manually sanitize
    data before logging.
    
    Args:
        data: Data to sanitize
    
    Returns:
        Sanitized data
    """
    filter = SensitiveDataFilter()
    
    if isinstance(data, dict):
        return filter.sanitize_dict(data)
    elif isinstance(data, str):
        return filter.sanitize_text(data)
    elif isinstance(data, (list, tuple)):
        return [sanitize_for_logging(item) for item in data]
    else:
        return data
