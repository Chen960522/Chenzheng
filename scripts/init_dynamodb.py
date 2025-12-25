"""Initialize DynamoDB tables for AWS Pricing Assistant."""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.config.settings import settings
from src.config.aws_clients import aws_clients
from src.utils.logger import get_logger

logger = get_logger(__name__)


def create_users_table():
    """Create users table with encryption at rest."""
    table_name = settings.dynamodb_users_table
    
    try:
        table = aws_clients.dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {'AttributeName': 'user_id', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'user_id', 'AttributeType': 'S'},
                {'AttributeName': 'username', 'AttributeType': 'S'}
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'username-index',
                    'KeySchema': [
                        {'AttributeName': 'username', 'KeyType': 'HASH'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
                }
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            },
            SSESpecification={
                'Enabled': True,
                'SSEType': 'KMS'  # Use AWS KMS for encryption
            }
        )
        
        table.wait_until_exists()
        logger.info(f"Created table with encryption: {table_name}")
        
    except aws_clients.dynamodb.meta.client.exceptions.ResourceInUseException:
        logger.info(f"Table already exists: {table_name}")


def create_sessions_table():
    """Create sessions table with encryption at rest."""
    table_name = settings.dynamodb_sessions_table
    
    try:
        table = aws_clients.dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {'AttributeName': 'session_id', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'session_id', 'AttributeType': 'S'},
                {'AttributeName': 'user_id', 'AttributeType': 'S'}
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'user-sessions-index',
                    'KeySchema': [
                        {'AttributeName': 'user_id', 'KeyType': 'HASH'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
                }
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            },
            SSESpecification={
                'Enabled': True,
                'SSEType': 'KMS'  # Use AWS KMS for encryption
            }
        )
        
        # Enable TTL on expires_at attribute
        aws_clients.dynamodb.meta.client.update_time_to_live(
            TableName=table_name,
            TimeToLiveSpecification={
                'Enabled': True,
                'AttributeName': 'expires_at'
            }
        )
        
        table.wait_until_exists()
        logger.info(f"Created table with encryption: {table_name}")
        
    except aws_clients.dynamodb.meta.client.exceptions.ResourceInUseException:
        logger.info(f"Table already exists: {table_name}")


def create_quotes_table():
    """Create quotes table with encryption at rest."""
    table_name = settings.dynamodb_quotes_table
    
    try:
        table = aws_clients.dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {'AttributeName': 'quote_id', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'quote_id', 'AttributeType': 'S'},
                {'AttributeName': 'user_id', 'AttributeType': 'S'},
                {'AttributeName': 'created_at', 'AttributeType': 'S'}
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'user-quotes-index',
                    'KeySchema': [
                        {'AttributeName': 'user_id', 'KeyType': 'HASH'},
                        {'AttributeName': 'created_at', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
                }
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            },
            SSESpecification={
                'Enabled': True,
                'SSEType': 'KMS'  # Use AWS KMS for encryption
            }
        )
        
        table.wait_until_exists()
        logger.info(f"Created table with encryption: {table_name}")
        
    except aws_clients.dynamodb.meta.client.exceptions.ResourceInUseException:
        logger.info(f"Table already exists: {table_name}")


def create_cloud_services_table():
    """Create cloud_services table with encryption at rest."""
    table_name = settings.dynamodb_cloud_services_table
    
    try:
        table = aws_clients.dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {'AttributeName': 'provider', 'KeyType': 'HASH'},
                {'AttributeName': 'service_name', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'provider', 'AttributeType': 'S'},
                {'AttributeName': 'service_name', 'AttributeType': 'S'},
                {'AttributeName': 'service_category', 'AttributeType': 'S'},
                {'AttributeName': 'crawled_at', 'AttributeType': 'S'}
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'category-index',
                    'KeySchema': [
                        {'AttributeName': 'service_category', 'KeyType': 'HASH'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
                },
                {
                    'IndexName': 'crawled-date-index',
                    'KeySchema': [
                        {'AttributeName': 'crawled_at', 'KeyType': 'HASH'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
                }
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            },
            SSESpecification={
                'Enabled': True,
                'SSEType': 'KMS'  # Use AWS KMS for encryption
            }
        )
        
        table.wait_until_exists()
        logger.info(f"Created table with encryption: {table_name}")
        
    except aws_clients.dynamodb.meta.client.exceptions.ResourceInUseException:
        logger.info(f"Table already exists: {table_name}")


def create_mapping_cache_table():
    """Create service_mapping_cache table with encryption at rest."""
    table_name = settings.dynamodb_service_mapping_cache_table
    
    try:
        table = aws_clients.dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {'AttributeName': 'source_provider', 'KeyType': 'HASH'},
                {'AttributeName': 'source_service', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'source_provider', 'AttributeType': 'S'},
                {'AttributeName': 'source_service', 'AttributeType': 'S'}
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            },
            SSESpecification={
                'Enabled': True,
                'SSEType': 'KMS'  # Use AWS KMS for encryption
            }
        )
        
        table.wait_until_exists()
        logger.info(f"Created table with encryption: {table_name}")
        
    except aws_clients.dynamodb.meta.client.exceptions.ResourceInUseException:
        logger.info(f"Table already exists: {table_name}")


def main():
    """Initialize all DynamoDB tables."""
    logger.info("Starting DynamoDB table initialization...")
    
    create_users_table()
    create_sessions_table()
    create_quotes_table()
    create_cloud_services_table()
    create_mapping_cache_table()
    
    logger.info("DynamoDB table initialization complete!")


if __name__ == "__main__":
    main()
