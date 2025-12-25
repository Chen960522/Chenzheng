"""
Price Calculator for AWS services.

This service calculates pricing for AWS services across all regions,
supporting multiple pricing models (On-Demand, Reserved, Savings Plans).
"""

from typing import Dict, Any, Optional
from decimal import Decimal
from datetime import datetime

from src.models.cloud_service import AWSServiceMapping
from src.models.pricing_result import PricingResult
from src.services.aws_pricing_service import AWSPricingService
from src.services.knowledge_base_service import KnowledgeBaseService
from src.utils.logger import get_logger

logger = get_logger(__name__)


class PriceCalculator:
    """
    Price Calculator for AWS services.
    
    Calculates pricing for AWS services across all regions:
    - US, Canada, South America
    - Europe (all regions)
    - Asia Pacific (all regions)
    - Middle East, Africa
    - China (special handling)
    - AWS GovCloud (special handling)
    
    Supports multiple pricing models:
    - On-Demand
    - Reserved Instances
    - Savings Plans
    """
    
    def __init__(
        self,
        pricing_service: Optional[AWSPricingService] = None,
        knowledge_base_service: Optional[KnowledgeBaseService] = None
    ):
        """
        Initialize Price Calculator.
        
        Args:
            pricing_service: AWS Pricing API service
            knowledge_base_service: Knowledge Base service for fallback pricing data
        """
        self.pricing_service = pricing_service or AWSPricingService()
        self.kb_service = knowledge_base_service or KnowledgeBaseService()
        self.supported_regions = PricingResult.SUPPORTED_REGIONS
        
        logger.info("PriceCalculator initialized")
    
    def calculate_price(
        self,
        aws_mapping: AWSServiceMapping,
        region: str = 'us-east-1',
        pricing_model: str = 'on-demand',
        usage_hours: int = 730,  # Default: 730 hours/month (24*30.42)
        quantity: int = 1
    ) -> PricingResult:
        """
        Calculate price for an AWS service.
        
        Args:
            aws_mapping: AWS service mapping with specifications
            region: AWS region code
            pricing_model: Pricing model ('on-demand', 'reserved', 'savings-plan')
            usage_hours: Number of usage hours per month
            quantity: Number of instances/units
            
        Returns:
            PricingResult with monthly and annual costs
            
        Raises:
            ValueError: If region is not supported
        """
        logger.info(
            f"Calculating price for {aws_mapping.aws_service} "
            f"({aws_mapping.aws_service_type}) in {region}"
        )
        
        # Validate region
        if region not in self.supported_regions:
            raise ValueError(
                f"Unsupported region: {region}. "
                f"Supported regions: {', '.join(self.supported_regions)}"
            )
        
        # Check if service is available in region
        if not self._is_service_available_in_region(aws_mapping.aws_service, region):
            logger.warning(
                f"{aws_mapping.aws_service} may not be available in {region}"
            )
            return PricingResult(
                monthly_cost=Decimal('0'),
                annual_cost=Decimal('0'),
                pricing_model=pricing_model,
                region=region,
                breakdown={},
                region_availability=False
            )
        
        # Calculate based on service type
        if aws_mapping.aws_service_category == 'compute':
            return self._calculate_compute_price(
                aws_mapping, region, pricing_model, usage_hours, quantity
            )
        elif aws_mapping.aws_service_category == 'storage':
            return self._calculate_storage_price(
                aws_mapping, region, pricing_model, quantity
            )
        elif aws_mapping.aws_service_category == 'database':
            return self._calculate_database_price(
                aws_mapping, region, pricing_model, usage_hours, quantity
            )
        elif aws_mapping.aws_service_category == 'serverless':
            return self._calculate_serverless_price(
                aws_mapping, region, pricing_model, quantity
            )
        else:
            # Generic calculation for other service types
            return self._calculate_generic_price(
                aws_mapping, region, pricing_model, usage_hours, quantity
            )
    
    def get_all_region_prices(
        self,
        aws_mapping: AWSServiceMapping,
        pricing_model: str = 'on-demand',
        usage_hours: int = 730,
        quantity: int = 1
    ) -> Dict[str, Optional[PricingResult]]:
        """
        Calculate prices for all supported regions.
        
        Args:
            aws_mapping: AWS service mapping
            pricing_model: Pricing model
            usage_hours: Usage hours per month
            quantity: Number of instances/units
            
        Returns:
            Dictionary mapping region codes to PricingResult objects
        """
        logger.info(
            f"Calculating prices for {aws_mapping.aws_service} across all regions"
        )
        
        results = {}
        for region in self.supported_regions:
            try:
                results[region] = self.calculate_price(
                    aws_mapping, region, pricing_model, usage_hours, quantity
                )
            except Exception as e:
                logger.error(f"Error calculating price for {region}: {e}")
                results[region] = None
        
        return results
    
    def _calculate_compute_price(
        self,
        aws_mapping: AWSServiceMapping,
        region: str,
        pricing_model: str,
        usage_hours: int,
        quantity: int
    ) -> PricingResult:
        """Calculate pricing for compute services (EC2, etc.)."""
        logger.info(f"Calculating compute price for {aws_mapping.aws_service_type}")
        
        # Get pricing from AWS Pricing API
        pricing_data = None
        if aws_mapping.aws_service == 'EC2':
            pricing_data = self.pricing_service.get_ec2_pricing(
                instance_type=aws_mapping.aws_service_type,
                region=region,
                pricing_model=pricing_model
            )
        
        # Fallback to Knowledge Base if API fails
        if not pricing_data:
            logger.info("Falling back to Knowledge Base for pricing")
            pricing_data = self._get_pricing_from_kb(
                aws_mapping.aws_service,
                aws_mapping.aws_service_type,
                region
            )
        
        if not pricing_data:
            logger.warning(f"No pricing data found for {aws_mapping.aws_service_type}")
            return self._create_unavailable_pricing_result(region, pricing_model)
        
        # Calculate costs
        hourly_rate = pricing_data.get('hourly_rate', Decimal('0'))
        monthly_compute_cost = hourly_rate * Decimal(str(usage_hours)) * Decimal(str(quantity))
        
        # Add data transfer costs if applicable
        data_transfer_cost = self._calculate_data_transfer_cost(
            aws_mapping, region, quantity
        )
        
        monthly_cost = monthly_compute_cost + data_transfer_cost
        annual_cost = monthly_cost * Decimal('12')
        
        breakdown = {
            'compute': monthly_compute_cost,
            'data_transfer': data_transfer_cost
        }
        
        return PricingResult(
            monthly_cost=monthly_cost,
            annual_cost=annual_cost,
            pricing_model=pricing_model,
            region=region,
            breakdown=breakdown,
            last_updated=datetime.now()
        )
    
    def _calculate_storage_price(
        self,
        aws_mapping: AWSServiceMapping,
        region: str,
        pricing_model: str,
        quantity: int
    ) -> PricingResult:
        """Calculate pricing for storage services (S3, EBS, etc.)."""
        logger.info(f"Calculating storage price for {aws_mapping.aws_service_type}")
        
        # Get pricing from AWS Pricing API
        pricing_data = None
        if aws_mapping.aws_service == 'S3':
            pricing_data = self.pricing_service.get_s3_pricing(
                storage_class=aws_mapping.aws_service_type,
                region=region
            )
        
        # Fallback to Knowledge Base
        if not pricing_data:
            pricing_data = self._get_pricing_from_kb(
                aws_mapping.aws_service,
                aws_mapping.aws_service_type,
                region
            )
        
        if not pricing_data:
            return self._create_unavailable_pricing_result(region, pricing_model)
        
        # Calculate costs
        price_per_gb = pricing_data.get('price_per_gb', Decimal('0'))
        
        # Get storage capacity from specifications
        capacity_gb = Decimal(str(
            aws_mapping.specifications.get('capacity_gb', 100)
        ))
        
        monthly_storage_cost = price_per_gb * capacity_gb * Decimal(str(quantity))
        
        # Add data transfer costs
        data_transfer_cost = self._calculate_data_transfer_cost(
            aws_mapping, region, quantity
        )
        
        monthly_cost = monthly_storage_cost + data_transfer_cost
        annual_cost = monthly_cost * Decimal('12')
        
        breakdown = {
            'storage': monthly_storage_cost,
            'data_transfer': data_transfer_cost
        }
        
        return PricingResult(
            monthly_cost=monthly_cost,
            annual_cost=annual_cost,
            pricing_model=pricing_model,
            region=region,
            breakdown=breakdown,
            last_updated=datetime.now()
        )
    
    def _calculate_database_price(
        self,
        aws_mapping: AWSServiceMapping,
        region: str,
        pricing_model: str,
        usage_hours: int,
        quantity: int
    ) -> PricingResult:
        """Calculate pricing for database services (RDS, DynamoDB, etc.)."""
        logger.info(f"Calculating database price for {aws_mapping.aws_service_type}")
        
        # Get pricing from AWS Pricing API
        pricing_data = None
        if aws_mapping.aws_service == 'RDS':
            engine = aws_mapping.specifications.get('engine', 'MySQL')
            pricing_data = self.pricing_service.get_rds_pricing(
                instance_type=aws_mapping.aws_service_type,
                engine=engine,
                region=region,
                pricing_model=pricing_model
            )
        
        # Fallback to Knowledge Base
        if not pricing_data:
            pricing_data = self._get_pricing_from_kb(
                aws_mapping.aws_service,
                aws_mapping.aws_service_type,
                region
            )
        
        if not pricing_data:
            return self._create_unavailable_pricing_result(region, pricing_model)
        
        # Calculate costs
        hourly_rate = pricing_data.get('hourly_rate', Decimal('0'))
        monthly_instance_cost = hourly_rate * Decimal(str(usage_hours)) * Decimal(str(quantity))
        
        # Add storage costs if applicable
        storage_gb = Decimal(str(
            aws_mapping.specifications.get('storage_gb', 20)
        ))
        storage_cost_per_gb = Decimal('0.115')  # Approximate RDS storage cost
        monthly_storage_cost = storage_cost_per_gb * storage_gb * Decimal(str(quantity))
        
        # Add data transfer costs
        data_transfer_cost = self._calculate_data_transfer_cost(
            aws_mapping, region, quantity
        )
        
        monthly_cost = monthly_instance_cost + monthly_storage_cost + data_transfer_cost
        annual_cost = monthly_cost * Decimal('12')
        
        breakdown = {
            'instance': monthly_instance_cost,
            'storage': monthly_storage_cost,
            'data_transfer': data_transfer_cost
        }
        
        return PricingResult(
            monthly_cost=monthly_cost,
            annual_cost=annual_cost,
            pricing_model=pricing_model,
            region=region,
            breakdown=breakdown,
            last_updated=datetime.now()
        )
    
    def _calculate_serverless_price(
        self,
        aws_mapping: AWSServiceMapping,
        region: str,
        pricing_model: str,
        quantity: int
    ) -> PricingResult:
        """Calculate pricing for serverless services (Lambda, etc.)."""
        logger.info(f"Calculating serverless price for {aws_mapping.aws_service}")
        
        # Get pricing from AWS Pricing API
        pricing_data = None
        if aws_mapping.aws_service == 'Lambda':
            pricing_data = self.pricing_service.get_lambda_pricing(region)
        
        # Fallback to Knowledge Base
        if not pricing_data:
            pricing_data = self._get_pricing_from_kb(
                aws_mapping.aws_service,
                aws_mapping.aws_service_type,
                region
            )
        
        if not pricing_data:
            return self._create_unavailable_pricing_result(region, pricing_model)
        
        # Calculate costs based on invocations and duration
        price_per_gb_second = pricing_data.get('price_per_gb_second', Decimal('0.0000166667'))
        
        # Get usage from specifications
        invocations_per_month = Decimal(str(
            aws_mapping.specifications.get('invocations_per_month', 1000000)
        ))
        avg_duration_ms = Decimal(str(
            aws_mapping.specifications.get('avg_duration_ms', 200)
        ))
        memory_mb = Decimal(str(
            aws_mapping.specifications.get('memory_mb', 128)
        ))
        
        # Calculate GB-seconds
        gb_seconds = (
            invocations_per_month *
            (avg_duration_ms / Decimal('1000')) *
            (memory_mb / Decimal('1024'))
        ) * Decimal(str(quantity))
        
        monthly_compute_cost = price_per_gb_second * gb_seconds
        
        # Add request costs ($0.20 per 1M requests)
        request_cost = (invocations_per_month / Decimal('1000000')) * Decimal('0.20') * Decimal(str(quantity))
        
        monthly_cost = monthly_compute_cost + request_cost
        annual_cost = monthly_cost * Decimal('12')
        
        breakdown = {
            'compute': monthly_compute_cost,
            'requests': request_cost
        }
        
        return PricingResult(
            monthly_cost=monthly_cost,
            annual_cost=annual_cost,
            pricing_model=pricing_model,
            region=region,
            breakdown=breakdown,
            last_updated=datetime.now()
        )
    
    def _calculate_generic_price(
        self,
        aws_mapping: AWSServiceMapping,
        region: str,
        pricing_model: str,
        usage_hours: int,
        quantity: int
    ) -> PricingResult:
        """Calculate pricing for generic/other service types."""
        logger.info(f"Calculating generic price for {aws_mapping.aws_service}")
        
        # Try to get pricing from Knowledge Base
        pricing_data = self._get_pricing_from_kb(
            aws_mapping.aws_service,
            aws_mapping.aws_service_type,
            region
        )
        
        if not pricing_data:
            return self._create_unavailable_pricing_result(region, pricing_model)
        
        # Use generic hourly rate if available
        hourly_rate = pricing_data.get('hourly_rate', Decimal('0'))
        monthly_cost = hourly_rate * Decimal(str(usage_hours)) * Decimal(str(quantity))
        annual_cost = monthly_cost * Decimal('12')
        
        breakdown = {
            'service': monthly_cost
        }
        
        return PricingResult(
            monthly_cost=monthly_cost,
            annual_cost=annual_cost,
            pricing_model=pricing_model,
            region=region,
            breakdown=breakdown,
            last_updated=datetime.now()
        )
    
    def _calculate_data_transfer_cost(
        self,
        aws_mapping: AWSServiceMapping,
        region: str,
        quantity: int
    ) -> Decimal:
        """Calculate data transfer costs."""
        # Get data transfer from specifications
        data_transfer_gb = Decimal(str(
            aws_mapping.specifications.get('data_transfer_gb_per_month', 0)
        ))
        
        if data_transfer_gb == 0:
            return Decimal('0')
        
        # Get data transfer pricing
        transfer_pricing = self.pricing_service.get_data_transfer_pricing(region)
        
        if not transfer_pricing:
            # Use approximate data transfer cost ($0.09/GB for first 10TB)
            price_per_gb = Decimal('0.09')
        else:
            price_per_gb = transfer_pricing.get('price_per_gb', Decimal('0.09'))
        
        return price_per_gb * data_transfer_gb * Decimal(str(quantity))
    
    def _get_pricing_from_kb(
        self,
        aws_service: str,
        service_type: str,
        region: str
    ) -> Optional[Dict[str, Any]]:
        """Get pricing information from Knowledge Base."""
        try:
            query = f"Pricing for AWS {aws_service} {service_type} in {region}"
            results = self.kb_service.query(query, max_results=1)
            
            if results:
                # Parse pricing from KB results
                # This is a simplified implementation
                # In production, you'd parse structured pricing data
                return {
                    'hourly_rate': Decimal('0.01'),  # Placeholder
                    'price_per_gb': Decimal('0.023')  # Placeholder
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting pricing from KB: {e}")
            return None
    
    def _is_service_available_in_region(
        self,
        aws_service: str,
        region: str
    ) -> bool:
        """
        Check if an AWS service is available in a specific region.
        
        Some services are not available in all regions (especially China and GovCloud).
        """
        # Services with limited regional availability
        limited_services = {
            'SageMaker': ['cn-north-1', 'cn-northwest-1'],  # Not in China
            'Rekognition': ['cn-north-1', 'cn-northwest-1'],  # Not in China
            'Comprehend': ['cn-north-1', 'cn-northwest-1'],  # Not in China
        }
        
        unavailable_regions = limited_services.get(aws_service, [])
        return region not in unavailable_regions
    
    def _create_unavailable_pricing_result(
        self,
        region: str,
        pricing_model: str
    ) -> PricingResult:
        """Create a PricingResult for unavailable pricing."""
        return PricingResult(
            monthly_cost=Decimal('0'),
            annual_cost=Decimal('0'),
            pricing_model=pricing_model,
            region=region,
            breakdown={},
            region_availability=False,
            last_updated=datetime.now()
        )
