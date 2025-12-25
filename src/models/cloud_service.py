"""Cloud Service, AWS Service Mapping, and Service Mapping Cache data models."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
import uuid


@dataclass
class CloudService:
    """Cloud service model for storing crawled service information."""
    
    service_id: str
    provider: str  # 'alibaba', 'huawei', 'tencent', 'gcp', 'azure'
    service_name: str
    service_name_en: str
    service_name_zh: Optional[str]
    service_category: str  # 'compute', 'storage', 'database', 'network', etc.
    description: str
    specifications: Dict[str, Any]  # CPU, memory, storage, etc.
    features: List[str]
    pricing_info: Optional[Dict[str, Any]]  # If available from crawling
    source_url: str
    crawled_at: datetime
    last_updated: datetime
    data_quality_score: float  # 0.0 to 1.0
    manual_review_required: bool = False
    
    @staticmethod
    def generate_id() -> str:
        """Generate a new service ID."""
        return str(uuid.uuid4())
    
    def to_dynamodb_item(self) -> dict:
        """Convert to DynamoDB item format."""
        item = {
            'service_id': self.service_id,
            'provider': self.provider,
            'service_name': self.service_name,
            'service_name_en': self.service_name_en,
            'service_category': self.service_category,
            'description': self.description,
            'specifications': self.specifications,
            'features': self.features,
            'source_url': self.source_url,
            'crawled_at': self.crawled_at.isoformat(),
            'last_updated': self.last_updated.isoformat(),
            'data_quality_score': str(self.data_quality_score),  # Store as string for Decimal compatibility
            'manual_review_required': self.manual_review_required
        }
        
        if self.service_name_zh:
            item['service_name_zh'] = self.service_name_zh
        
        if self.pricing_info:
            item['pricing_info'] = self.pricing_info
        
        return item
    
    @classmethod
    def from_dynamodb_item(cls, item: dict) -> 'CloudService':
        """Create CloudService from DynamoDB item."""
        return cls(
            service_id=item['service_id'],
            provider=item['provider'],
            service_name=item['service_name'],
            service_name_en=item['service_name_en'],
            service_name_zh=item.get('service_name_zh'),
            service_category=item['service_category'],
            description=item['description'],
            specifications=item['specifications'],
            features=item['features'],
            pricing_info=item.get('pricing_info'),
            source_url=item['source_url'],
            crawled_at=datetime.fromisoformat(item['crawled_at']),
            last_updated=datetime.fromisoformat(item['last_updated']),
            data_quality_score=float(item['data_quality_score']),
            manual_review_required=item.get('manual_review_required', False)
        )


@dataclass
class AWSServiceMapping:
    """
    AWS service mapping result.
    
    Represents the mapping from a cloud provider service to an AWS service,
    including specifications, confidence score, and explanation.
    """
    
    aws_service: str  # AWS service name (e.g., 'EC2', 'S3', 'RDS', 'Lambda')
    aws_service_category: str  # Service category (e.g., 'compute', 'storage', 'database')
    aws_service_type: str  # Specific type (e.g., 't3.micro', 'Standard', 'db.t3.small')
    specifications: Dict[str, Any]  # AWS service specifications
    confidence_score: float  # 0.0 to 1.0
    explanation: str  # Explanation of why this mapping was chosen
    alternatives: List[str] = field(default_factory=list)  # Alternative AWS services
    mapping_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    # Supported AWS service categories
    SUPPORTED_CATEGORIES = [
        'compute',
        'storage',
        'database',
        'network',
        'analytics',
        'ml',  # Machine Learning
        'container',
        'serverless',
        'messaging',
        'monitoring',
        'security',
        'cdn',  # Content Delivery Network
        'iot',  # Internet of Things
        'blockchain',
        'developer_tools',
        'management',
        'application_integration',
        'business_applications',
        'end_user_computing',
        'media_services',
        'game_development'
    ]
    
    def __post_init__(self):
        """Validate the AWS service mapping after initialization."""
        if not self.aws_service:
            raise ValueError("AWS service name cannot be empty")
        
        if self.aws_service_category not in self.SUPPORTED_CATEGORIES:
            raise ValueError(
                f"Unsupported AWS service category: {self.aws_service_category}. "
                f"Supported categories: {', '.join(self.SUPPORTED_CATEGORIES)}"
            )
        
        if not self.aws_service_type:
            raise ValueError("AWS service type cannot be empty")
        
        if not isinstance(self.specifications, dict):
            raise ValueError("Specifications must be a dictionary")
        
        if not 0.0 <= self.confidence_score <= 1.0:
            raise ValueError("Confidence score must be between 0.0 and 1.0")
        
        if not self.explanation:
            raise ValueError("Explanation cannot be empty")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            'mapping_id': self.mapping_id,
            'aws_service': self.aws_service,
            'aws_service_category': self.aws_service_category,
            'aws_service_type': self.aws_service_type,
            'specifications': self.specifications,
            'confidence_score': self.confidence_score,
            'explanation': self.explanation,
            'alternatives': self.alternatives
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AWSServiceMapping':
        """Create AWSServiceMapping from dictionary."""
        return cls(
            aws_service=data['aws_service'],
            aws_service_category=data['aws_service_category'],
            aws_service_type=data['aws_service_type'],
            specifications=data['specifications'],
            confidence_score=data['confidence_score'],
            explanation=data['explanation'],
            alternatives=data.get('alternatives', []),
            mapping_id=data.get('mapping_id', str(uuid.uuid4()))
        )
    
    def is_high_confidence(self, threshold: float = 0.8) -> bool:
        """Check if this mapping has high confidence."""
        return self.confidence_score >= threshold
    
    def has_alternatives(self) -> bool:
        """Check if alternative AWS services are available."""
        return len(self.alternatives) > 0
    
    def __repr__(self) -> str:
        """String representation of the AWS service mapping."""
        return (
            f"AWSServiceMapping(aws_service='{self.aws_service}', "
            f"aws_service_type='{self.aws_service_type}', "
            f"confidence={self.confidence_score:.2f})"
        )


@dataclass
class ServiceMappingCache:
    """Service mapping cache model for storing successful mappings."""
    
    mapping_id: str
    source_provider: str
    source_service: str
    source_specs: Dict[str, Any]
    aws_service: str
    aws_service_type: str
    aws_specs: Dict[str, Any]
    confidence_score: float
    created_at: datetime
    hit_count: int  # Number of times this mapping was used
    last_used: datetime
    
    @staticmethod
    def generate_id() -> str:
        """Generate a new mapping ID."""
        return str(uuid.uuid4())
    
    def to_dynamodb_item(self) -> dict:
        """Convert to DynamoDB item format."""
        return {
            'mapping_id': self.mapping_id,
            'source_provider': self.source_provider,
            'source_service': self.source_service,
            'source_specs': self.source_specs,
            'aws_service': self.aws_service,
            'aws_service_type': self.aws_service_type,
            'aws_specs': self.aws_specs,
            'confidence_score': str(self.confidence_score),  # Store as string for Decimal compatibility
            'created_at': self.created_at.isoformat(),
            'hit_count': self.hit_count,
            'last_used': self.last_used.isoformat()
        }
    
    @classmethod
    def from_dynamodb_item(cls, item: dict) -> 'ServiceMappingCache':
        """Create ServiceMappingCache from DynamoDB item."""
        return cls(
            mapping_id=item['mapping_id'],
            source_provider=item['source_provider'],
            source_service=item['source_service'],
            source_specs=item['source_specs'],
            aws_service=item['aws_service'],
            aws_service_type=item['aws_service_type'],
            aws_specs=item['aws_specs'],
            confidence_score=float(item['confidence_score']),
            created_at=datetime.fromisoformat(item['created_at']),
            hit_count=item['hit_count'],
            last_used=datetime.fromisoformat(item['last_used'])
        )
    
    def to_aws_service_mapping(self, explanation: str = "", alternatives: List[str] = None) -> AWSServiceMapping:
        """Convert cached mapping to AWSServiceMapping."""
        if alternatives is None:
            alternatives = []
        
        # Infer category from aws_service (simplified logic)
        category = self._infer_category(self.aws_service)
        
        return AWSServiceMapping(
            aws_service=self.aws_service,
            aws_service_category=category,
            aws_service_type=self.aws_service_type,
            specifications=self.aws_specs,
            confidence_score=self.confidence_score,
            explanation=explanation or f"Cached mapping from {self.source_provider} {self.source_service}",
            alternatives=alternatives,
            mapping_id=self.mapping_id
        )
    
    def _infer_category(self, aws_service: str) -> str:
        """Infer AWS service category from service name."""
        # Simple mapping of common AWS services to categories
        service_categories = {
            'EC2': 'compute',
            'Lambda': 'serverless',
            'ECS': 'container',
            'EKS': 'container',
            'S3': 'storage',
            'EBS': 'storage',
            'EFS': 'storage',
            'RDS': 'database',
            'DynamoDB': 'database',
            'Aurora': 'database',
            'VPC': 'network',
            'CloudFront': 'cdn',
            'Route53': 'network',
            'ALB': 'network',
            'NLB': 'network',
            'SQS': 'messaging',
            'SNS': 'messaging',
            'Kinesis': 'analytics',
            'EMR': 'analytics',
            'Athena': 'analytics',
            'SageMaker': 'ml',
            'CloudWatch': 'monitoring',
            'IAM': 'security',
            'KMS': 'security',
        }
        return service_categories.get(aws_service, 'compute')
