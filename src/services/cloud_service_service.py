"""Cloud Service and Service Mapping Cache database operations."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from boto3.dynamodb.conditions import Key
import boto3

from src.models.cloud_service import CloudService, ServiceMappingCache
from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class CloudServiceService:
    """Service for cloud service database operations."""
    
    def __init__(self, dynamodb_client=None):
        """Initialize CloudServiceService with DynamoDB client."""
        if dynamodb_client is None:
            dynamodb_client = boto3.resource('dynamodb', region_name=settings.aws_region)
        self.dynamodb = dynamodb_client
        self.cloud_services_table = self.dynamodb.Table(settings.dynamodb_cloud_services_table)
        self.mapping_cache_table = self.dynamodb.Table(settings.dynamodb_service_mapping_cache_table)
    
    # CloudService CRUD operations
    
    def create_cloud_service(self, service: CloudService) -> CloudService:
        """Create a new cloud service in DynamoDB."""
        try:
            self.cloud_services_table.put_item(Item=service.to_dynamodb_item())
            logger.info(f"Created cloud service: {service.provider}/{service.service_name}")
            return service
        except Exception as e:
            logger.error(f"Failed to create cloud service {service.provider}/{service.service_name}: {e}")
            raise
    
    def get_cloud_service(self, provider: str, service_name: str) -> Optional[CloudService]:
        """Get cloud service by provider and service_name."""
        try:
            response = self.cloud_services_table.get_item(
                Key={
                    'provider': provider,
                    'service_name': service_name
                }
            )
            if 'Item' in response:
                return CloudService.from_dynamodb_item(response['Item'])
            return None
        except Exception as e:
            logger.error(f"Failed to get cloud service {provider}/{service_name}: {e}")
            raise
    
    def get_cloud_service_by_id(self, service_id: str) -> Optional[CloudService]:
        """Get cloud service by service_id (requires scan - use sparingly)."""
        try:
            response = self.cloud_services_table.scan(
                FilterExpression='service_id = :sid',
                ExpressionAttributeValues={':sid': service_id}
            )
            if response['Items']:
                return CloudService.from_dynamodb_item(response['Items'][0])
            return None
        except Exception as e:
            logger.error(f"Failed to get cloud service by ID {service_id}: {e}")
            raise
    
    def list_cloud_services(self, provider: Optional[str] = None) -> List[CloudService]:
        """
        List cloud services, optionally filtered by provider.
        
        Args:
            provider: Optional provider name to filter by
            
        Returns:
            List of CloudService objects
        """
        if provider:
            return self.list_cloud_services_by_provider(provider)
        else:
            # List all services across all providers
            try:
                response = self.cloud_services_table.scan()
                services = [CloudService.from_dynamodb_item(item) for item in response['Items']]
                
                # Handle pagination
                while 'LastEvaluatedKey' in response:
                    response = self.cloud_services_table.scan(
                        ExclusiveStartKey=response['LastEvaluatedKey']
                    )
                    services.extend([CloudService.from_dynamodb_item(item) for item in response['Items']])
                
                return services
            except Exception as e:
                logger.error(f"Failed to list all cloud services: {e}")
                raise
    
    def list_cloud_services_by_provider(self, provider: str) -> List[CloudService]:
        """List all cloud services for a specific provider."""
        try:
            response = self.cloud_services_table.query(
                KeyConditionExpression=Key('provider').eq(provider)
            )
            services = [CloudService.from_dynamodb_item(item) for item in response['Items']]
            
            # Handle pagination
            while 'LastEvaluatedKey' in response:
                response = self.cloud_services_table.query(
                    KeyConditionExpression=Key('provider').eq(provider),
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                services.extend([CloudService.from_dynamodb_item(item) for item in response['Items']])
            
            return services
        except Exception as e:
            logger.error(f"Failed to list cloud services for provider {provider}: {e}")
            raise
    
    def list_cloud_services_by_category(self, service_category: str) -> List[CloudService]:
        """List all cloud services by category using GSI."""
        try:
            response = self.cloud_services_table.query(
                IndexName='category-index',
                KeyConditionExpression=Key('service_category').eq(service_category)
            )
            services = [CloudService.from_dynamodb_item(item) for item in response['Items']]
            
            # Handle pagination
            while 'LastEvaluatedKey' in response:
                response = self.cloud_services_table.query(
                    IndexName='category-index',
                    KeyConditionExpression=Key('service_category').eq(service_category),
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                services.extend([CloudService.from_dynamodb_item(item) for item in response['Items']])
            
            return services
        except Exception as e:
            logger.error(f"Failed to list cloud services by category {service_category}: {e}")
            raise
    
    def list_services_requiring_review(self) -> List[CloudService]:
        """List all services flagged for manual review."""
        try:
            response = self.cloud_services_table.scan(
                FilterExpression='manual_review_required = :true',
                ExpressionAttributeValues={':true': True}
            )
            services = [CloudService.from_dynamodb_item(item) for item in response['Items']]
            
            # Handle pagination
            while 'LastEvaluatedKey' in response:
                response = self.cloud_services_table.scan(
                    FilterExpression='manual_review_required = :true',
                    ExpressionAttributeValues={':true': True},
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                services.extend([CloudService.from_dynamodb_item(item) for item in response['Items']])
            
            return services
        except Exception as e:
            logger.error(f"Failed to list services requiring review: {e}")
            raise
    
    def update_cloud_service(self, service: CloudService) -> CloudService:
        """Update an existing cloud service."""
        try:
            service.last_updated = datetime.utcnow()
            self.cloud_services_table.put_item(Item=service.to_dynamodb_item())
            logger.info(f"Updated cloud service: {service.provider}/{service.service_name}")
            return service
        except Exception as e:
            logger.error(f"Failed to update cloud service {service.provider}/{service.service_name}: {e}")
            raise
    
    def delete_cloud_service(self, provider: str, service_name: str) -> None:
        """Delete a cloud service."""
        try:
            self.cloud_services_table.delete_item(
                Key={
                    'provider': provider,
                    'service_name': service_name
                }
            )
            logger.info(f"Deleted cloud service: {provider}/{service_name}")
        except Exception as e:
            logger.error(f"Failed to delete cloud service {provider}/{service_name}: {e}")
            raise
    
    # ServiceMappingCache CRUD operations
    
    def create_mapping_cache(self, mapping: ServiceMappingCache) -> ServiceMappingCache:
        """Create a new service mapping cache entry."""
        try:
            self.mapping_cache_table.put_item(Item=mapping.to_dynamodb_item())
            logger.info(f"Created mapping cache: {mapping.source_provider}/{mapping.source_service} -> {mapping.aws_service}")
            return mapping
        except Exception as e:
            logger.error(f"Failed to create mapping cache: {e}")
            raise
    
    def get_mapping_cache(self, source_provider: str, source_service: str) -> Optional[ServiceMappingCache]:
        """Get cached mapping by source provider and service."""
        try:
            response = self.mapping_cache_table.get_item(
                Key={
                    'source_provider': source_provider,
                    'source_service': source_service
                }
            )
            if 'Item' in response:
                return ServiceMappingCache.from_dynamodb_item(response['Item'])
            return None
        except Exception as e:
            logger.error(f"Failed to get mapping cache {source_provider}/{source_service}: {e}")
            raise
    
    def update_mapping_cache_hit(self, source_provider: str, source_service: str) -> None:
        """Increment hit count and update last_used timestamp for a cached mapping."""
        try:
            self.mapping_cache_table.update_item(
                Key={
                    'source_provider': source_provider,
                    'source_service': source_service
                },
                UpdateExpression='SET hit_count = hit_count + :inc, last_used = :timestamp',
                ExpressionAttributeValues={
                    ':inc': 1,
                    ':timestamp': datetime.utcnow().isoformat()
                }
            )
            logger.debug(f"Updated mapping cache hit: {source_provider}/{source_service}")
        except Exception as e:
            logger.error(f"Failed to update mapping cache hit: {e}")
            raise
    
    def delete_mapping_cache(self, source_provider: str, source_service: str) -> None:
        """Delete a cached mapping."""
        try:
            self.mapping_cache_table.delete_item(
                Key={
                    'source_provider': source_provider,
                    'source_service': source_service
                }
            )
            logger.info(f"Deleted mapping cache: {source_provider}/{source_service}")
        except Exception as e:
            logger.error(f"Failed to delete mapping cache: {e}")
            raise
    
    def list_all_mapping_caches(self) -> List[ServiceMappingCache]:
        """List all cached mappings."""
        try:
            response = self.mapping_cache_table.scan()
            mappings = [ServiceMappingCache.from_dynamodb_item(item) for item in response['Items']]
            
            # Handle pagination
            while 'LastEvaluatedKey' in response:
                response = self.mapping_cache_table.scan(
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                mappings.extend([ServiceMappingCache.from_dynamodb_item(item) for item in response['Items']])
            
            return mappings
        except Exception as e:
            logger.error(f"Failed to list mapping caches: {e}")
            raise
