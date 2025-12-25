"""Logging configuration with CloudWatch integration."""

import logging
import sys
from typing import Optional


class CloudWatchHandler(logging.Handler):
    """Custom handler for sending logs to CloudWatch."""
    
    def __init__(self, log_group: str, log_stream: str):
        super().__init__()
        self.log_group = log_group
        self.log_stream = log_stream
        self._cloudwatch_client = None
        self._sequence_token = None
    
    def emit(self, record: logging.LogRecord):
        """Send log record to CloudWatch."""
        try:
            if self._cloudwatch_client is None:
                from ..config.aws_clients import aws_clients
                self._cloudwatch_client = aws_clients.cloudwatch
                self._ensure_log_stream_exists()
            
            log_event = {
                'timestamp': int(record.created * 1000),
                'message': self.format(record)
            }
            
            kwargs = {
                'logGroupName': self.log_group,
                'logStreamName': self.log_stream,
                'logEvents': [log_event]
            }
            
            if self._sequence_token:
                kwargs['sequenceToken'] = self._sequence_token
            
            response = self._cloudwatch_client.put_log_events(**kwargs)
            self._sequence_token = response.get('nextSequenceToken')
            
        except Exception as e:
            # Don't let logging errors crash the application
            print(f"Error sending log to CloudWatch: {e}", file=sys.stderr)
    
    def _ensure_log_stream_exists(self):
        """Ensure the log group and stream exist."""
        try:
            # Create log group if it doesn't exist
            try:
                self._cloudwatch_client.create_log_group(logGroupName=self.log_group)
            except self._cloudwatch_client.exceptions.ResourceAlreadyExistsException:
                pass
            
            # Create log stream if it doesn't exist
            try:
                self._cloudwatch_client.create_log_stream(
                    logGroupName=self.log_group,
                    logStreamName=self.log_stream
                )
            except self._cloudwatch_client.exceptions.ResourceAlreadyExistsException:
                pass
        except Exception as e:
            print(f"Error creating log group/stream: {e}", file=sys.stderr)


def get_logger(name: str, level: Optional[int] = None) -> logging.Logger:
    """
    Get a configured logger instance.
    
    Args:
        name: Logger name (typically __name__)
        level: Logging level (defaults to DEBUG in dev, INFO in prod)
    
    Returns:
        Configured logger instance
    """
    # Lazy import to avoid circular dependency
    from ..config.settings import settings
    
    logger = logging.getLogger(name)
    
    # Set level based on environment
    if level is None:
        level = logging.DEBUG if settings.debug else logging.INFO
    logger.setLevel(level)
    
    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # CloudWatch handler (only in production)
    if settings.environment == 'production':
        try:
            cloudwatch_handler = CloudWatchHandler(
                settings.cloudwatch_log_group,
                settings.cloudwatch_log_stream
            )
            cloudwatch_handler.setFormatter(formatter)
            logger.addHandler(cloudwatch_handler)
        except Exception as e:
            logger.warning(f"Failed to initialize CloudWatch logging: {e}")
    
    return logger
