"""Service configuration data models."""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
import uuid


@dataclass
class ServiceConfig:
    """
    Configuration for a cloud service from any provider.
    
    Supports all service categories including:
    - Compute (EC2, VM instances, Lambda, containers)
    - Storage (S3, block storage, file storage)
    - Database (RDS, NoSQL, data warehouses)
    - Network (VPC, CDN, load balancers, VPN)
    - Analytics (data processing, streaming, ETL)
    - Machine Learning (training, inference, AI services)
    - Container (orchestration, registry)
    - Serverless (functions, event processing)
    - Messaging (queues, pub/sub, event buses)
    - Monitoring (logs, metrics, tracing)
    - Security (IAM, encryption, compliance)
    - CDN & Edge (content delivery, edge computing)
    - IoT (device management, data ingestion)
    - Blockchain (distributed ledger)
    - Developer Tools (CI/CD, code repositories)
    - Management (infrastructure as code, automation)
    - Application Integration (workflow, data integration)
    - Business Applications (collaboration, communication)
    - End User Computing (virtual desktops, app streaming)
    - Media Services (video processing, streaming)
    - Game Development (game servers, game engines)
    """
    
    provider: str  # 'alibaba', 'huawei', 'tencent', 'gcp', 'azure'
    service_type: str  # Service category (compute, storage, database, etc.)
    service_name: str  # Original service name from provider
    specifications: Dict[str, Any]  # Service specifications (CPU, memory, storage, etc.)
    region: Optional[str] = None  # Provider's region
    quantity: int = 1  # Number of instances/units
    config_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    # Supported service categories
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
    
    # Supported cloud providers
    SUPPORTED_PROVIDERS = [
        'alibaba',
        'huawei',
        'tencent',
        'gcp',
        'azure'
    ]
    
    def __post_init__(self):
        """Validate the service configuration after initialization."""
        if self.provider not in self.SUPPORTED_PROVIDERS:
            raise ValueError(
                f"Unsupported provider: {self.provider}. "
                f"Supported providers: {', '.join(self.SUPPORTED_PROVIDERS)}"
            )
        
        if self.service_type not in self.SUPPORTED_CATEGORIES:
            raise ValueError(
                f"Unsupported service type: {self.service_type}. "
                f"Supported types: {', '.join(self.SUPPORTED_CATEGORIES)}"
            )
        
        if not self.service_name:
            raise ValueError("Service name cannot be empty")
        
        if not isinstance(self.specifications, dict):
            raise ValueError("Specifications must be a dictionary")
        
        if self.quantity < 1:
            raise ValueError("Quantity must be at least 1")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            'config_id': self.config_id,
            'provider': self.provider,
            'service_type': self.service_type,
            'service_name': self.service_name,
            'specifications': self.specifications,
            'region': self.region,
            'quantity': self.quantity
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ServiceConfig':
        """Create ServiceConfig from dictionary."""
        return cls(
            provider=data['provider'],
            service_type=data['service_type'],
            service_name=data['service_name'],
            specifications=data['specifications'],
            region=data.get('region'),
            quantity=data.get('quantity', 1),
            config_id=data.get('config_id', str(uuid.uuid4()))
        )
    
    def get_specification(self, key: str, default: Any = None) -> Any:
        """Get a specific specification value."""
        return self.specifications.get(key, default)
    
    def has_specification(self, key: str) -> bool:
        """Check if a specification exists."""
        return key in self.specifications
    
    def get_compute_specs(self) -> Dict[str, Any]:
        """Extract compute-related specifications (CPU, memory)."""
        compute_keys = ['cpu', 'vcpu', 'cores', 'memory', 'ram', 'memory_gb', 'ram_gb']
        return {k: v for k, v in self.specifications.items() if k.lower() in compute_keys}
    
    def get_storage_specs(self) -> Dict[str, Any]:
        """Extract storage-related specifications."""
        storage_keys = ['storage', 'disk', 'storage_gb', 'disk_size', 'capacity', 'volume_size']
        return {k: v for k, v in self.specifications.items() if k.lower() in storage_keys}
    
    def get_network_specs(self) -> Dict[str, Any]:
        """Extract network-related specifications."""
        network_keys = ['bandwidth', 'network', 'throughput', 'bandwidth_mbps', 'network_speed']
        return {k: v for k, v in self.specifications.items() if k.lower() in network_keys}
    
    def __repr__(self) -> str:
        """String representation of the service configuration."""
        return (
            f"ServiceConfig(provider='{self.provider}', "
            f"service_type='{self.service_type}', "
            f"service_name='{self.service_name}', "
            f"quantity={self.quantity})"
        )
