#!/usr/bin/env python3
"""Set up CloudWatch log groups with proper configuration."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.settings import settings
from src.config.aws_clients import aws_clients
from src.utils.logger import get_logger

logger = get_logger(__name__)


def create_log_group(log_group_name: str, retention_days: int = 30):
    """
    Create CloudWatch log group with retention policy.
    
    Args:
        log_group_name: Name of the log group
        retention_days: Log retention period in days
    """
    try:
        # Create log group
        aws_clients.cloudwatch.create_log_group(logGroupName=log_group_name)
        logger.info(f"Created log group: {log_group_name}")
    except aws_clients.cloudwatch.exceptions.ResourceAlreadyExistsException:
        logger.info(f"Log group already exists: {log_group_name}")
    except Exception as e:
        logger.error(f"Failed to create log group: {e}")
        raise
    
    try:
        # Set retention policy
        aws_clients.cloudwatch.put_retention_policy(
            logGroupName=log_group_name,
            retentionInDays=retention_days
        )
        logger.info(f"Set retention policy to {retention_days} days for {log_group_name}")
    except Exception as e:
        logger.error(f"Failed to set retention policy: {e}")
        raise


def enable_log_encryption(log_group_name: str, kms_key_id: str = None):
    """
    Enable encryption for CloudWatch log group.
    
    Args:
        log_group_name: Name of the log group
        kms_key_id: Optional KMS key ID (uses default CloudWatch key if not provided)
    """
    try:
        if kms_key_id:
            aws_clients.cloudwatch.associate_kms_key(
                logGroupName=log_group_name,
                kmsKeyId=kms_key_id
            )
            logger.info(f"Enabled encryption with KMS key for {log_group_name}")
        else:
            logger.info(f"Using default CloudWatch encryption for {log_group_name}")
    except Exception as e:
        logger.error(f"Failed to enable log encryption: {e}")
        raise


def main():
    """Set up CloudWatch log groups."""
    print("=" * 60)
    print("AWS Pricing Assistant - CloudWatch Logs Setup")
    print("=" * 60)
    print()
    
    log_group = settings.cloudwatch_log_group
    retention_days = 30  # Default retention period
    
    print(f"Setting up log group: {log_group}")
    print(f"Retention period: {retention_days} days")
    print()
    
    try:
        # Create log group with retention
        create_log_group(log_group, retention_days)
        
        # Enable encryption (optional - requires KMS key)
        # Uncomment and provide KMS key ID if needed
        # kms_key_id = "arn:aws:kms:region:account:key/key-id"
        # enable_log_encryption(log_group, kms_key_id)
        
        print()
        print("✓ CloudWatch log group setup complete!")
        print()
        print("Log group details:")
        print(f"  - Name: {log_group}")
        print(f"  - Retention: {retention_days} days")
        print(f"  - Encryption: Default CloudWatch encryption")
        print()
        print("To view logs:")
        print(f"  aws logs tail {log_group} --follow")
        print()
        
    except Exception as e:
        print(f"✗ Error setting up CloudWatch logs: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
