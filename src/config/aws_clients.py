"""AWS client configuration and initialization."""

import boto3
from typing import Optional
from .settings import settings


class AWSClients:
    """Singleton class for managing AWS service clients."""
    
    _instance: Optional['AWSClients'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # Create boto3 session
        self.session = boto3.Session(
            aws_access_key_id=settings.aws_access_key_id or None,
            aws_secret_access_key=settings.aws_secret_access_key or None,
            region_name=settings.aws_region
        )
        
        # Initialize clients
        self._dynamodb = None
        self._s3 = None
        self._bedrock_runtime = None
        self._bedrock_agent_runtime = None
        self._pricing = None
        self._cloudwatch = None
        self._secrets_manager = None
        
        self._initialized = True
    
    @property
    def dynamodb(self):
        """Get DynamoDB client."""
        if self._dynamodb is None:
            self._dynamodb = self.session.resource('dynamodb')
        return self._dynamodb
    
    @property
    def s3(self):
        """Get S3 client."""
        if self._s3 is None:
            self._s3 = self.session.client('s3')
        return self._s3
    
    @property
    def bedrock_runtime(self):
        """Get Bedrock Runtime client."""
        if self._bedrock_runtime is None:
            self._bedrock_runtime = self.session.client('bedrock-runtime')
        return self._bedrock_runtime
    
    @property
    def bedrock_agent_runtime(self):
        """Get Bedrock Agent Runtime client."""
        if self._bedrock_agent_runtime is None:
            self._bedrock_agent_runtime = self.session.client('bedrock-agent-runtime')
        return self._bedrock_agent_runtime
    
    @property
    def pricing(self):
        """Get Pricing client."""
        if self._pricing is None:
            # Pricing API is only available in us-east-1 and ap-south-1
            self._pricing = boto3.client('pricing', region_name='us-east-1')
        return self._pricing
    
    @property
    def cloudwatch(self):
        """Get CloudWatch Logs client."""
        if self._cloudwatch is None:
            self._cloudwatch = self.session.client('logs')
        return self._cloudwatch
    
    @property
    def secrets_manager(self):
        """Get Secrets Manager client."""
        if self._secrets_manager is None:
            self._secrets_manager = self.session.client('secretsmanager')
        return self._secrets_manager


# Global AWS clients instance
aws_clients = AWSClients()
