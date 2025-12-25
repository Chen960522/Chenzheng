"""Pytest configuration and fixtures."""

import pytest
import os
from dotenv import load_dotenv

# Load test environment variables
load_dotenv('.env.test')


@pytest.fixture(scope="session")
def aws_credentials():
    """Mock AWS credentials for testing."""
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'


@pytest.fixture
def test_settings():
    """Test settings fixture."""
    from src.config.settings import Settings
    
    return Settings(
        environment='test',
        debug=True,
        jwt_secret_key='test-secret-key',
        dynamodb_users_table='test-users',
        dynamodb_sessions_table='test-sessions',
        dynamodb_quotes_table='test-quotes',
        dynamodb_cloud_services_table='test-cloud-services',
        dynamodb_mapping_cache_table='test-mapping-cache'
    )
