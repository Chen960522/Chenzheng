"""Pricing Result data model for AWS service pricing calculations."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, Optional
import uuid


@dataclass
class PricingResult:
    """
    Pricing result for an AWS service.
    
    Contains pricing information for a specific AWS service configuration,
    including monthly and annual costs, pricing model, region, and breakdown.
    
    Supports all AWS regions:
    - US: us-east-1, us-east-2, us-west-1, us-west-2
    - Canada: ca-central-1, ca-west-1
    - South America: sa-east-1
    - Europe: eu-west-1, eu-west-2, eu-west-3, eu-central-1, eu-central-2, 
              eu-north-1, eu-south-1, eu-south-2
    - Asia Pacific: ap-south-1, ap-south-2, ap-southeast-1, ap-southeast-2, 
                    ap-southeast-3, ap-southeast-4, ap-northeast-1, ap-northeast-2, 
                    ap-northeast-3, ap-east-1
    - Middle East: me-south-1, me-central-1
    - Africa: af-south-1
    - China: cn-north-1, cn-northwest-1
    - AWS GovCloud: us-gov-east-1, us-gov-west-1
    """
    
    monthly_cost: Decimal  # Monthly cost in USD
    annual_cost: Decimal  # Annual cost in USD
    pricing_model: str  # 'on-demand', 'reserved', 'savings-plan'
    region: str  # AWS region code
    breakdown: Dict[str, Decimal]  # Cost breakdown (compute, storage, data_transfer, etc.)
    currency: str = 'USD'
    last_updated: datetime = field(default_factory=datetime.now)
    region_availability: bool = True  # False if service not available in region
    pricing_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    # All supported AWS regions
    SUPPORTED_REGIONS = [
        # US regions
        'us-east-1',      # US East (N. Virginia)
        'us-east-2',      # US East (Ohio)
        'us-west-1',      # US West (N. California)
        'us-west-2',      # US West (Oregon)
        
        # Canada regions
        'ca-central-1',   # Canada (Central)
        'ca-west-1',      # Canada (Calgary)
        
        # South America regions
        'sa-east-1',      # South America (São Paulo)
        
        # Europe regions
        'eu-west-1',      # Europe (Ireland)
        'eu-west-2',      # Europe (London)
        'eu-west-3',      # Europe (Paris)
        'eu-central-1',   # Europe (Frankfurt)
        'eu-central-2',   # Europe (Zurich)
        'eu-north-1',     # Europe (Stockholm)
        'eu-south-1',     # Europe (Milan)
        'eu-south-2',     # Europe (Spain)
        
        # Asia Pacific regions
        'ap-south-1',     # Asia Pacific (Mumbai)
        'ap-south-2',     # Asia Pacific (Hyderabad)
        'ap-southeast-1', # Asia Pacific (Singapore)
        'ap-southeast-2', # Asia Pacific (Sydney)
        'ap-southeast-3', # Asia Pacific (Jakarta)
        'ap-southeast-4', # Asia Pacific (Melbourne)
        'ap-northeast-1', # Asia Pacific (Tokyo)
        'ap-northeast-2', # Asia Pacific (Seoul)
        'ap-northeast-3', # Asia Pacific (Osaka)
        'ap-east-1',      # Asia Pacific (Hong Kong)
        
        # Middle East regions
        'me-south-1',     # Middle East (Bahrain)
        'me-central-1',   # Middle East (UAE)
        
        # Africa regions
        'af-south-1',     # Africa (Cape Town)
        
        # China regions (special handling required)
        'cn-north-1',     # China (Beijing)
        'cn-northwest-1', # China (Ningxia)
        
        # AWS GovCloud regions (special handling required)
        'us-gov-east-1',  # AWS GovCloud (US-East)
        'us-gov-west-1',  # AWS GovCloud (US-West)
    ]
    
    # Supported pricing models
    SUPPORTED_PRICING_MODELS = [
        'on-demand',
        'reserved',
        'savings-plan'
    ]
    
    def __post_init__(self):
        """Validate the pricing result after initialization."""
        if self.region not in self.SUPPORTED_REGIONS:
            raise ValueError(
                f"Unsupported region: {self.region}. "
                f"Supported regions: {', '.join(self.SUPPORTED_REGIONS)}"
            )
        
        if self.pricing_model not in self.SUPPORTED_PRICING_MODELS:
            raise ValueError(
                f"Unsupported pricing model: {self.pricing_model}. "
                f"Supported models: {', '.join(self.SUPPORTED_PRICING_MODELS)}"
            )
        
        if self.monthly_cost < 0:
            raise ValueError("Monthly cost cannot be negative")
        
        if self.annual_cost < 0:
            raise ValueError("Annual cost cannot be negative")
        
        if not isinstance(self.breakdown, dict):
            raise ValueError("Breakdown must be a dictionary")
        
        # Validate breakdown values are non-negative
        for key, value in self.breakdown.items():
            if value < 0:
                raise ValueError(f"Breakdown value for '{key}' cannot be negative")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            'pricing_id': self.pricing_id,
            'monthly_cost': float(self.monthly_cost),
            'annual_cost': float(self.annual_cost),
            'pricing_model': self.pricing_model,
            'region': self.region,
            'breakdown': {k: float(v) for k, v in self.breakdown.items()},
            'currency': self.currency,
            'last_updated': self.last_updated.isoformat(),
            'region_availability': self.region_availability
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PricingResult':
        """Create PricingResult from dictionary."""
        return cls(
            monthly_cost=Decimal(str(data['monthly_cost'])),
            annual_cost=Decimal(str(data['annual_cost'])),
            pricing_model=data['pricing_model'],
            region=data['region'],
            breakdown={k: Decimal(str(v)) for k, v in data['breakdown'].items()},
            currency=data.get('currency', 'USD'),
            last_updated=datetime.fromisoformat(data['last_updated']) if isinstance(data.get('last_updated'), str) else data.get('last_updated', datetime.now()),
            region_availability=data.get('region_availability', True),
            pricing_id=data.get('pricing_id', str(uuid.uuid4()))
        )
    
    def get_breakdown_item(self, key: str, default: Decimal = Decimal('0')) -> Decimal:
        """Get a specific breakdown item value."""
        return self.breakdown.get(key, default)
    
    def has_breakdown_item(self, key: str) -> bool:
        """Check if a breakdown item exists."""
        return key in self.breakdown
    
    def get_total_breakdown(self) -> Decimal:
        """Calculate total from breakdown items."""
        return sum(self.breakdown.values(), Decimal('0'))
    
    def is_available_in_region(self) -> bool:
        """Check if the service is available in the specified region."""
        return self.region_availability
    
    def is_china_region(self) -> bool:
        """Check if this is a China region (requires special handling)."""
        return self.region.startswith('cn-')
    
    def is_govcloud_region(self) -> bool:
        """Check if this is a GovCloud region (requires special handling)."""
        return self.region.startswith('us-gov-')
    
    def requires_special_handling(self) -> bool:
        """Check if this region requires special handling (China or GovCloud)."""
        return self.is_china_region() or self.is_govcloud_region()
    
    def get_region_name(self) -> str:
        """Get human-readable region name."""
        region_names = {
            'us-east-1': 'US East (N. Virginia)',
            'us-east-2': 'US East (Ohio)',
            'us-west-1': 'US West (N. California)',
            'us-west-2': 'US West (Oregon)',
            'ca-central-1': 'Canada (Central)',
            'ca-west-1': 'Canada (Calgary)',
            'sa-east-1': 'South America (São Paulo)',
            'eu-west-1': 'Europe (Ireland)',
            'eu-west-2': 'Europe (London)',
            'eu-west-3': 'Europe (Paris)',
            'eu-central-1': 'Europe (Frankfurt)',
            'eu-central-2': 'Europe (Zurich)',
            'eu-north-1': 'Europe (Stockholm)',
            'eu-south-1': 'Europe (Milan)',
            'eu-south-2': 'Europe (Spain)',
            'ap-south-1': 'Asia Pacific (Mumbai)',
            'ap-south-2': 'Asia Pacific (Hyderabad)',
            'ap-southeast-1': 'Asia Pacific (Singapore)',
            'ap-southeast-2': 'Asia Pacific (Sydney)',
            'ap-southeast-3': 'Asia Pacific (Jakarta)',
            'ap-southeast-4': 'Asia Pacific (Melbourne)',
            'ap-northeast-1': 'Asia Pacific (Tokyo)',
            'ap-northeast-2': 'Asia Pacific (Seoul)',
            'ap-northeast-3': 'Asia Pacific (Osaka)',
            'ap-east-1': 'Asia Pacific (Hong Kong)',
            'me-south-1': 'Middle East (Bahrain)',
            'me-central-1': 'Middle East (UAE)',
            'af-south-1': 'Africa (Cape Town)',
            'cn-north-1': 'China (Beijing)',
            'cn-northwest-1': 'China (Ningxia)',
            'us-gov-east-1': 'AWS GovCloud (US-East)',
            'us-gov-west-1': 'AWS GovCloud (US-West)',
        }
        return region_names.get(self.region, self.region)
    
    def __repr__(self) -> str:
        """String representation of the pricing result."""
        return (
            f"PricingResult(region='{self.region}', "
            f"pricing_model='{self.pricing_model}', "
            f"monthly_cost={self.monthly_cost:.2f} {self.currency})"
        )
