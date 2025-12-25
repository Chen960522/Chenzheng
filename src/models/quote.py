"""Quote data model for AWS pricing quotes."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, List, Optional
import uuid


@dataclass
class Quote:
    """
    Quote document for AWS service pricing.
    
    Contains all information needed for a complete pricing quote:
    - Original service configurations from other cloud providers
    - Mapped AWS services and specifications
    - Pricing results for each service
    - Total costs (monthly and annual)
    - Export URLs for different formats (PDF, Excel, JSON)
    - User and status information
    """
    
    quote_id: str  # UUID
    user_id: str  # User who created the quote
    created_at: datetime
    updated_at: datetime
    status: str  # 'draft', 'finalized', 'sent'
    original_input: str  # Original configuration text/file content
    parsed_services: List[Dict[str, Any]]  # Parsed ServiceConfig objects as dicts
    aws_mappings: List[Dict[str, Any]]  # AWS service mappings as dicts
    pricing_results: List[Dict[str, Any]]  # PricingResult objects as dicts
    total_monthly_cost: Decimal  # Total monthly cost in USD
    total_annual_cost: Decimal  # Total annual cost in USD
    currency: str = 'USD'
    region: str = 'us-east-1'  # Primary AWS region for the quote
    notes: Optional[str] = None  # Additional notes or comments
    export_urls: Dict[str, str] = field(default_factory=dict)  # format -> S3 URL
    language: str = 'en'  # 'en' or 'zh' for output language
    
    # Supported quote statuses
    SUPPORTED_STATUSES = ['draft', 'finalized', 'sent']
    
    # Supported export formats
    SUPPORTED_FORMATS = ['pdf', 'excel', 'json']
    
    # Supported languages
    SUPPORTED_LANGUAGES = ['en', 'zh']
    
    def __post_init__(self):
        """Validate the quote after initialization."""
        if self.status not in self.SUPPORTED_STATUSES:
            raise ValueError(
                f"Unsupported status: {self.status}. "
                f"Supported statuses: {', '.join(self.SUPPORTED_STATUSES)}"
            )
        
        if self.language not in self.SUPPORTED_LANGUAGES:
            raise ValueError(
                f"Unsupported language: {self.language}. "
                f"Supported languages: {', '.join(self.SUPPORTED_LANGUAGES)}"
            )
        
        if not self.quote_id:
            raise ValueError("Quote ID cannot be empty")
        
        if not self.user_id:
            raise ValueError("User ID cannot be empty")
        
        if self.total_monthly_cost < 0:
            raise ValueError("Total monthly cost cannot be negative")
        
        if self.total_annual_cost < 0:
            raise ValueError("Total annual cost cannot be negative")
        
        if not isinstance(self.parsed_services, list):
            raise ValueError("Parsed services must be a list")
        
        if not isinstance(self.aws_mappings, list):
            raise ValueError("AWS mappings must be a list")
        
        if not isinstance(self.pricing_results, list):
            raise ValueError("Pricing results must be a list")
        
        # Validate export URLs format
        for format_type in self.export_urls.keys():
            if format_type not in self.SUPPORTED_FORMATS:
                raise ValueError(
                    f"Unsupported export format: {format_type}. "
                    f"Supported formats: {', '.join(self.SUPPORTED_FORMATS)}"
                )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for DynamoDB storage."""
        return {
            'quote_id': self.quote_id,
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'status': self.status,
            'original_input': self.original_input,
            'parsed_services': self.parsed_services,
            'aws_mappings': self.aws_mappings,
            'pricing_results': self.pricing_results,
            'total_monthly_cost': float(self.total_monthly_cost),
            'total_annual_cost': float(self.total_annual_cost),
            'currency': self.currency,
            'region': self.region,
            'notes': self.notes,
            'export_urls': self.export_urls,
            'language': self.language
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Quote':
        """Create Quote from dictionary."""
        return cls(
            quote_id=data['quote_id'],
            user_id=data['user_id'],
            created_at=datetime.fromisoformat(data['created_at']) if isinstance(data['created_at'], str) else data['created_at'],
            updated_at=datetime.fromisoformat(data['updated_at']) if isinstance(data['updated_at'], str) else data['updated_at'],
            status=data['status'],
            original_input=data['original_input'],
            parsed_services=data['parsed_services'],
            aws_mappings=data['aws_mappings'],
            pricing_results=data['pricing_results'],
            total_monthly_cost=Decimal(str(data['total_monthly_cost'])),
            total_annual_cost=Decimal(str(data['total_annual_cost'])),
            currency=data.get('currency', 'USD'),
            region=data.get('region', 'us-east-1'),
            notes=data.get('notes'),
            export_urls=data.get('export_urls', {}),
            language=data.get('language', 'en')
        )
    
    @classmethod
    def create_new(
        cls,
        user_id: str,
        original_input: str,
        parsed_services: List[Dict[str, Any]],
        aws_mappings: List[Dict[str, Any]],
        pricing_results: List[Dict[str, Any]],
        region: str = 'us-east-1',
        language: str = 'en',
        notes: Optional[str] = None
    ) -> 'Quote':
        """
        Create a new quote with calculated totals.
        
        Args:
            user_id: User ID who created the quote
            original_input: Original configuration text
            parsed_services: List of parsed service configurations
            aws_mappings: List of AWS service mappings
            pricing_results: List of pricing results
            region: Primary AWS region
            language: Output language ('en' or 'zh')
            notes: Optional notes
        
        Returns:
            New Quote instance
        """
        now = datetime.now()
        
        # Calculate total costs from pricing results
        total_monthly = Decimal('0')
        total_annual = Decimal('0')
        
        for pricing in pricing_results:
            total_monthly += Decimal(str(pricing.get('monthly_cost', 0)))
            total_annual += Decimal(str(pricing.get('annual_cost', 0)))
        
        return cls(
            quote_id=str(uuid.uuid4()),
            user_id=user_id,
            created_at=now,
            updated_at=now,
            status='draft',
            original_input=original_input,
            parsed_services=parsed_services,
            aws_mappings=aws_mappings,
            pricing_results=pricing_results,
            total_monthly_cost=total_monthly,
            total_annual_cost=total_annual,
            region=region,
            language=language,
            notes=notes
        )
    
    def update_status(self, new_status: str) -> None:
        """Update quote status."""
        if new_status not in self.SUPPORTED_STATUSES:
            raise ValueError(
                f"Unsupported status: {new_status}. "
                f"Supported statuses: {', '.join(self.SUPPORTED_STATUSES)}"
            )
        self.status = new_status
        self.updated_at = datetime.now()
    
    def add_export_url(self, format_type: str, url: str) -> None:
        """Add an export URL for a specific format."""
        if format_type not in self.SUPPORTED_FORMATS:
            raise ValueError(
                f"Unsupported export format: {format_type}. "
                f"Supported formats: {', '.join(self.SUPPORTED_FORMATS)}"
            )
        self.export_urls[format_type] = url
        self.updated_at = datetime.now()
    
    def get_export_url(self, format_type: str) -> Optional[str]:
        """Get export URL for a specific format."""
        return self.export_urls.get(format_type)
    
    def has_export(self, format_type: str) -> bool:
        """Check if export exists for a specific format."""
        return format_type in self.export_urls
    
    def update_notes(self, notes: str) -> None:
        """Update quote notes."""
        self.notes = notes
        self.updated_at = datetime.now()
    
    def get_service_count(self) -> int:
        """Get the number of services in the quote."""
        return len(self.parsed_services)
    
    def is_draft(self) -> bool:
        """Check if quote is in draft status."""
        return self.status == 'draft'
    
    def is_finalized(self) -> bool:
        """Check if quote is finalized."""
        return self.status == 'finalized'
    
    def is_sent(self) -> bool:
        """Check if quote has been sent."""
        return self.status == 'sent'
    
    def finalize(self) -> None:
        """Finalize the quote."""
        self.update_status('finalized')
    
    def mark_as_sent(self) -> None:
        """Mark the quote as sent."""
        self.update_status('sent')
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the quote."""
        return {
            'quote_id': self.quote_id,
            'status': self.status,
            'service_count': self.get_service_count(),
            'total_monthly_cost': float(self.total_monthly_cost),
            'total_annual_cost': float(self.total_annual_cost),
            'currency': self.currency,
            'region': self.region,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def __repr__(self) -> str:
        """String representation of the quote."""
        return (
            f"Quote(quote_id='{self.quote_id}', "
            f"status='{self.status}', "
            f"services={self.get_service_count()}, "
            f"total_monthly={self.total_monthly_cost:.2f} {self.currency})"
        )


@dataclass
class AWSServiceMapping:
    """
    Mapping from a cloud provider service to AWS service.
    
    Used within quotes to show how each original service maps to AWS.
    """
    
    aws_service: str  # AWS service name (e.g., 'EC2', 'S3', 'RDS')
    aws_service_category: str  # Service category (compute, storage, database, etc.)
    aws_service_type: str  # Specific type (instance type, storage class, etc.)
    specifications: Dict[str, Any]  # AWS service specifications
    confidence_score: float  # 0.0 to 1.0
    explanation: str  # Explanation of the mapping
    alternatives: List[str] = field(default_factory=list)  # Alternative AWS services
    mapping_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    def __post_init__(self):
        """Validate the mapping after initialization."""
        if not 0.0 <= self.confidence_score <= 1.0:
            raise ValueError("Confidence score must be between 0.0 and 1.0")
        
        if not self.aws_service:
            raise ValueError("AWS service cannot be empty")
        
        if not self.aws_service_category:
            raise ValueError("AWS service category cannot be empty")
        
        if not isinstance(self.specifications, dict):
            raise ValueError("Specifications must be a dictionary")
        
        if not isinstance(self.alternatives, list):
            raise ValueError("Alternatives must be a list")
    
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
    
    def is_high_confidence(self) -> bool:
        """Check if mapping has high confidence (>= 0.8)."""
        return self.confidence_score >= 0.8
    
    def has_alternatives(self) -> bool:
        """Check if there are alternative AWS services."""
        return len(self.alternatives) > 0
    
    def __repr__(self) -> str:
        """String representation of the mapping."""
        return (
            f"AWSServiceMapping(aws_service='{self.aws_service}', "
            f"type='{self.aws_service_type}', "
            f"confidence={self.confidence_score:.2f})"
        )
