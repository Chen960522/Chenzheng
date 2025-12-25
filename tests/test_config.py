"""Tests for configuration module."""

import pytest
from src.config.settings import Settings


def test_settings_defaults():
    """Test that settings have sensible defaults."""
    settings = Settings()
    
    assert settings.aws_region == "us-east-1"
    assert settings.jwt_algorithm == "HS256"
    assert settings.jwt_access_token_expire_minutes == 30
    assert settings.api_port == 8000
    assert settings.environment == "development"


def test_settings_from_env(monkeypatch):
    """Test that settings can be loaded from environment variables."""
    monkeypatch.setenv("AWS_REGION", "us-west-2")
    monkeypatch.setenv("API_PORT", "9000")
    monkeypatch.setenv("ENVIRONMENT", "production")
    
    settings = Settings()
    
    assert settings.aws_region == "us-west-2"
    assert settings.api_port == 9000
    assert settings.environment == "production"


def test_dynamodb_table_names():
    """Test that DynamoDB table names are configured."""
    settings = Settings()
    
    assert settings.dynamodb_users_table
    assert settings.dynamodb_sessions_table
    assert settings.dynamodb_quotes_table
    assert settings.dynamodb_cloud_services_table
    assert settings.dynamodb_mapping_cache_table


def test_bedrock_configuration():
    """Test that Bedrock configuration is present."""
    settings = Settings()
    
    assert settings.bedrock_model_id
    assert settings.bedrock_embedding_model_id
    assert "claude" in settings.bedrock_model_id.lower()
