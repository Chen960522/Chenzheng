"""Application settings and configuration management."""

from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # AWS Configuration
    aws_region: str = "us-east-1"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    
    # Bedrock Configuration
    bedrock_model_id: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"
    bedrock_knowledge_base_id: str = ""
    bedrock_embedding_model_id: str = "amazon.titan-embed-text-v2:0"
    
    # DynamoDB Tables
    dynamodb_users_table: str = "aws-pricing-assistant-users"
    dynamodb_sessions_table: str = "aws-pricing-assistant-sessions"
    dynamodb_quotes_table: str = "aws-pricing-assistant-quotes"
    dynamodb_cloud_services_table: str = "aws-pricing-assistant-cloud-services"
    dynamodb_service_mapping_cache_table: str = "aws-pricing-assistant-service-mapping-cache"
    
    # S3 Configuration
    s3_bucket_name: str = "aws-pricing-assistant-exports"
    s3_knowledge_base_bucket: str = "aws-pricing-assistant-kb-data"
    
    # Authentication
    jwt_secret_key: str = "change-this-secret-key-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_rate_limit: int = 100
    
    # CloudWatch Configuration
    cloudwatch_log_group: str = "/aws/pricing-assistant"
    cloudwatch_log_stream: str = "application"
    
    # Application Settings
    environment: str = "development"
    debug: bool = True
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    
    # Web Crawler Configuration
    crawler_schedule: str = "cron(0 2 * * ? *)"
    crawler_user_agent: str = "AWS-Pricing-Assistant-Bot/1.0"
    crawler_retry_attempts: int = 3
    crawler_retry_delay: int = 5
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    @property
    def KNOWLEDGE_BASE_BUCKET_NAME(self) -> str:
        """Get Knowledge Base S3 bucket name."""
        return self.s3_knowledge_base_bucket
    
    @property
    def AWS_REGION(self) -> str:
        """Get AWS region."""
        return self.aws_region


# Global settings instance
settings = Settings()
