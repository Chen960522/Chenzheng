"""
AWS Pricing API integration service.

This service provides methods to retrieve pricing information from AWS Pricing API
for all AWS services and regions.
"""

from typing import Dict, Any, Optional, List
from decimal import Decimal
import json

from src.config.aws_clients import aws_clients
from src.utils.logger import get_logger

logger = get_logger(__name__)


class AWSPricingService:
    """
    Service for interacting with AWS Pricing API.
    
    Retrieves pricing information for AWS services across all regions.
    The AWS Pricing API is only available in us-east-1 and ap-south-1 regions,
    but provides pricing data for all AWS regions.
    """
    
    def __init__(self):
        """Initialize AWS Pricing Service."""
        self.pricing_client = aws_clients.pricing
        logger.info("AWSPricingService initialized")
    
    def get_ec2_pricing(
        self,
        instance_type: str,
        region: str,
        operating_system: str = 'Linux',
        tenancy: str = 'Shared',
        pricing_model: str = 'on-demand'
    ) -> Optional[Dict[str, Any]]:
        """
        Get EC2 instance pricing.
        
        Args:
            instance_type: EC2 instance type (e.g., 't3.micro', 'm5.large')
            region: AWS region code (e.g., 'us-east-1')
            operating_system: Operating system ('Linux', 'Windows', 'RHEL', 'SUSE')
            tenancy: Tenancy type ('Shared', 'Dedicated', 'Host')
            pricing_model: Pricing model ('on-demand', 'reserved')
            
        Returns:
            Dictionary with pricing information or None if not found
        """
        try:
            logger.info(f"Getting EC2 pricing for {instance_type} in {region}")
            
            # Convert region code to location name
            location = self._get_location_from_region(region)
            
            filters = [
                {'Type': 'TERM_MATCH', 'Field': 'instanceType', 'Value': instance_type},
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': location},
                {'Type': 'TERM_MATCH', 'Field': 'operatingSystem', 'Value': operating_system},
                {'Type': 'TERM_MATCH', 'Field': 'tenancy', 'Value': tenancy},
                {'Type': 'TERM_MATCH', 'Field': 'preInstalledSw', 'Value': 'NA'},
                {'Type': 'TERM_MATCH', 'Field': 'capacitystatus', 'Value': 'Used'}
            ]
            
            response = self.pricing_client.get_products(
                ServiceCode='AmazonEC2',
                Filters=filters,
                MaxResults=1
            )
            
            if not response.get('PriceList'):
                logger.warning(f"No pricing found for {instance_type} in {region}")
                return None
            
            # Parse the pricing data
            price_item = json.loads(response['PriceList'][0])
            pricing_info = self._extract_ec2_pricing(price_item, pricing_model)
            
            return pricing_info
            
        except Exception as e:
            logger.error(f"Error getting EC2 pricing: {e}")
            return None
    
    def get_s3_pricing(
        self,
        storage_class: str,
        region: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get S3 storage pricing.
        
        Args:
            storage_class: S3 storage class ('Standard', 'Intelligent-Tiering', 
                          'Standard-IA', 'One Zone-IA', 'Glacier', 'Glacier Deep Archive')
            region: AWS region code
            
        Returns:
            Dictionary with pricing information or None if not found
        """
        try:
            logger.info(f"Getting S3 pricing for {storage_class} in {region}")
            
            location = self._get_location_from_region(region)
            
            # Map storage class to AWS Pricing API values
            storage_class_map = {
                'Standard': 'General Purpose',
                'Intelligent-Tiering': 'Intelligent-Tiering',
                'Standard-IA': 'Infrequent Access',
                'One Zone-IA': 'One Zone - Infrequent Access',
                'Glacier': 'Archive',
                'Glacier Deep Archive': 'Deep Archive'
            }
            
            api_storage_class = storage_class_map.get(storage_class, storage_class)
            
            filters = [
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': location},
                {'Type': 'TERM_MATCH', 'Field': 'storageClass', 'Value': api_storage_class},
                {'Type': 'TERM_MATCH', 'Field': 'volumeType', 'Value': 'Standard'}
            ]
            
            response = self.pricing_client.get_products(
                ServiceCode='AmazonS3',
                Filters=filters,
                MaxResults=1
            )
            
            if not response.get('PriceList'):
                logger.warning(f"No pricing found for S3 {storage_class} in {region}")
                return None
            
            price_item = json.loads(response['PriceList'][0])
            pricing_info = self._extract_s3_pricing(price_item)
            
            return pricing_info
            
        except Exception as e:
            logger.error(f"Error getting S3 pricing: {e}")
            return None
    
    def get_rds_pricing(
        self,
        instance_type: str,
        engine: str,
        region: str,
        deployment_option: str = 'Single-AZ',
        pricing_model: str = 'on-demand'
    ) -> Optional[Dict[str, Any]]:
        """
        Get RDS instance pricing.
        
        Args:
            instance_type: RDS instance type (e.g., 'db.t3.micro', 'db.m5.large')
            engine: Database engine ('MySQL', 'PostgreSQL', 'MariaDB', 'Oracle', 'SQL Server')
            region: AWS region code
            deployment_option: Deployment option ('Single-AZ', 'Multi-AZ')
            pricing_model: Pricing model ('on-demand', 'reserved')
            
        Returns:
            Dictionary with pricing information or None if not found
        """
        try:
            logger.info(f"Getting RDS pricing for {instance_type} ({engine}) in {region}")
            
            location = self._get_location_from_region(region)
            
            filters = [
                {'Type': 'TERM_MATCH', 'Field': 'instanceType', 'Value': instance_type},
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': location},
                {'Type': 'TERM_MATCH', 'Field': 'databaseEngine', 'Value': engine},
                {'Type': 'TERM_MATCH', 'Field': 'deploymentOption', 'Value': deployment_option}
            ]
            
            response = self.pricing_client.get_products(
                ServiceCode='AmazonRDS',
                Filters=filters,
                MaxResults=1
            )
            
            if not response.get('PriceList'):
                logger.warning(f"No pricing found for RDS {instance_type} in {region}")
                return None
            
            price_item = json.loads(response['PriceList'][0])
            pricing_info = self._extract_rds_pricing(price_item, pricing_model)
            
            return pricing_info
            
        except Exception as e:
            logger.error(f"Error getting RDS pricing: {e}")
            return None
    
    def get_lambda_pricing(self, region: str) -> Optional[Dict[str, Any]]:
        """
        Get Lambda pricing.
        
        Args:
            region: AWS region code
            
        Returns:
            Dictionary with pricing information or None if not found
        """
        try:
            logger.info(f"Getting Lambda pricing in {region}")
            
            location = self._get_location_from_region(region)
            
            filters = [
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': location},
                {'Type': 'TERM_MATCH', 'Field': 'group', 'Value': 'AWS-Lambda-Duration'}
            ]
            
            response = self.pricing_client.get_products(
                ServiceCode='AWSLambda',
                Filters=filters,
                MaxResults=1
            )
            
            if not response.get('PriceList'):
                logger.warning(f"No pricing found for Lambda in {region}")
                return None
            
            price_item = json.loads(response['PriceList'][0])
            pricing_info = self._extract_lambda_pricing(price_item)
            
            return pricing_info
            
        except Exception as e:
            logger.error(f"Error getting Lambda pricing: {e}")
            return None
    
    def get_data_transfer_pricing(
        self,
        region: str,
        transfer_type: str = 'InterRegion-Out'
    ) -> Optional[Dict[str, Any]]:
        """
        Get data transfer pricing.
        
        Args:
            region: AWS region code
            transfer_type: Type of data transfer ('InterRegion-Out', 'Internet-Out', etc.)
            
        Returns:
            Dictionary with pricing information or None if not found
        """
        try:
            logger.info(f"Getting data transfer pricing for {region}")
            
            location = self._get_location_from_region(region)
            
            filters = [
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': location},
                {'Type': 'TERM_MATCH', 'Field': 'transferType', 'Value': transfer_type}
            ]
            
            response = self.pricing_client.get_products(
                ServiceCode='AWSDataTransfer',
                Filters=filters,
                MaxResults=1
            )
            
            if not response.get('PriceList'):
                logger.warning(f"No data transfer pricing found for {region}")
                return None
            
            price_item = json.loads(response['PriceList'][0])
            pricing_info = self._extract_data_transfer_pricing(price_item)
            
            return pricing_info
            
        except Exception as e:
            logger.error(f"Error getting data transfer pricing: {e}")
            return None
    
    def _get_location_from_region(self, region: str) -> str:
        """
        Convert AWS region code to location name used by Pricing API.
        
        Args:
            region: AWS region code (e.g., 'us-east-1')
            
        Returns:
            Location name (e.g., 'US East (N. Virginia)')
        """
        region_to_location = {
            'us-east-1': 'US East (N. Virginia)',
            'us-east-2': 'US East (Ohio)',
            'us-west-1': 'US West (N. California)',
            'us-west-2': 'US West (Oregon)',
            'ca-central-1': 'Canada (Central)',
            'ca-west-1': 'Canada West (Calgary)',
            'sa-east-1': 'South America (Sao Paulo)',
            'eu-west-1': 'EU (Ireland)',
            'eu-west-2': 'EU (London)',
            'eu-west-3': 'EU (Paris)',
            'eu-central-1': 'EU (Frankfurt)',
            'eu-central-2': 'EU (Zurich)',
            'eu-north-1': 'EU (Stockholm)',
            'eu-south-1': 'EU (Milan)',
            'eu-south-2': 'EU (Spain)',
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
        return region_to_location.get(region, region)
    
    def _extract_ec2_pricing(
        self,
        price_item: Dict[str, Any],
        pricing_model: str
    ) -> Dict[str, Any]:
        """Extract EC2 pricing from price item."""
        try:
            terms = price_item.get('terms', {})
            
            if pricing_model == 'on-demand':
                on_demand_terms = terms.get('OnDemand', {})
                if not on_demand_terms:
                    return {}
                
                # Get the first (and usually only) term
                term_key = list(on_demand_terms.keys())[0]
                term = on_demand_terms[term_key]
                
                # Get price dimensions
                price_dimensions = term.get('priceDimensions', {})
                dimension_key = list(price_dimensions.keys())[0]
                dimension = price_dimensions[dimension_key]
                
                price_per_unit = dimension.get('pricePerUnit', {}).get('USD', '0')
                
                return {
                    'hourly_rate': Decimal(price_per_unit),
                    'unit': dimension.get('unit', 'Hrs'),
                    'description': dimension.get('description', '')
                }
            
            # TODO: Add reserved instance pricing extraction
            return {}
            
        except Exception as e:
            logger.error(f"Error extracting EC2 pricing: {e}")
            return {}
    
    def _extract_s3_pricing(self, price_item: Dict[str, Any]) -> Dict[str, Any]:
        """Extract S3 pricing from price item."""
        try:
            terms = price_item.get('terms', {}).get('OnDemand', {})
            if not terms:
                return {}
            
            term_key = list(terms.keys())[0]
            term = terms[term_key]
            
            price_dimensions = term.get('priceDimensions', {})
            dimension_key = list(price_dimensions.keys())[0]
            dimension = price_dimensions[dimension_key]
            
            price_per_unit = dimension.get('pricePerUnit', {}).get('USD', '0')
            
            return {
                'price_per_gb': Decimal(price_per_unit),
                'unit': dimension.get('unit', 'GB-Mo'),
                'description': dimension.get('description', '')
            }
            
        except Exception as e:
            logger.error(f"Error extracting S3 pricing: {e}")
            return {}
    
    def _extract_rds_pricing(
        self,
        price_item: Dict[str, Any],
        pricing_model: str
    ) -> Dict[str, Any]:
        """Extract RDS pricing from price item."""
        try:
            terms = price_item.get('terms', {})
            
            if pricing_model == 'on-demand':
                on_demand_terms = terms.get('OnDemand', {})
                if not on_demand_terms:
                    return {}
                
                term_key = list(on_demand_terms.keys())[0]
                term = on_demand_terms[term_key]
                
                price_dimensions = term.get('priceDimensions', {})
                dimension_key = list(price_dimensions.keys())[0]
                dimension = price_dimensions[dimension_key]
                
                price_per_unit = dimension.get('pricePerUnit', {}).get('USD', '0')
                
                return {
                    'hourly_rate': Decimal(price_per_unit),
                    'unit': dimension.get('unit', 'Hrs'),
                    'description': dimension.get('description', '')
                }
            
            return {}
            
        except Exception as e:
            logger.error(f"Error extracting RDS pricing: {e}")
            return {}
    
    def _extract_lambda_pricing(self, price_item: Dict[str, Any]) -> Dict[str, Any]:
        """Extract Lambda pricing from price item."""
        try:
            terms = price_item.get('terms', {}).get('OnDemand', {})
            if not terms:
                return {}
            
            term_key = list(terms.keys())[0]
            term = terms[term_key]
            
            price_dimensions = term.get('priceDimensions', {})
            dimension_key = list(price_dimensions.keys())[0]
            dimension = price_dimensions[dimension_key]
            
            price_per_unit = dimension.get('pricePerUnit', {}).get('USD', '0')
            
            return {
                'price_per_gb_second': Decimal(price_per_unit),
                'unit': dimension.get('unit', 'Lambda-GB-Second'),
                'description': dimension.get('description', '')
            }
            
        except Exception as e:
            logger.error(f"Error extracting Lambda pricing: {e}")
            return {}
    
    def _extract_data_transfer_pricing(self, price_item: Dict[str, Any]) -> Dict[str, Any]:
        """Extract data transfer pricing from price item."""
        try:
            terms = price_item.get('terms', {}).get('OnDemand', {})
            if not terms:
                return {}
            
            term_key = list(terms.keys())[0]
            term = terms[term_key]
            
            price_dimensions = term.get('priceDimensions', {})
            dimension_key = list(price_dimensions.keys())[0]
            dimension = price_dimensions[dimension_key]
            
            price_per_unit = dimension.get('pricePerUnit', {}).get('USD', '0')
            
            return {
                'price_per_gb': Decimal(price_per_unit),
                'unit': dimension.get('unit', 'GB'),
                'description': dimension.get('description', '')
            }
            
        except Exception as e:
            logger.error(f"Error extracting data transfer pricing: {e}")
            return {}
