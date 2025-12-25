"""
Service Mapper for mapping cloud provider services to AWS services.

This service uses:
- Bedrock Knowledge Base for service mapping rules
- Crawled cloud service data from DynamoDB
- Mapping cache for performance optimization
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import json

from src.models.service_config import ServiceConfig
from src.models.cloud_service import AWSServiceMapping, ServiceMappingCache, CloudService
from src.services.knowledge_base_service import KnowledgeBaseService
from src.services.cloud_service_service import CloudServiceService
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ServiceMapper:
    """
    Service Mapper for mapping cloud provider services to AWS equivalents.
    
    Supports all service categories:
    - Compute, Storage, Database, Network
    - Analytics, ML, Container, Serverless
    - Messaging, Monitoring, Security, CDN
    - IoT, Blockchain, Developer Tools, Management
    - Application Integration, Business Applications
    - End User Computing, Media Services, Game Development
    """
    
    def __init__(
        self,
        knowledge_base_service: Optional[KnowledgeBaseService] = None,
        cloud_service_service: Optional[CloudServiceService] = None
    ):
        """
        Initialize ServiceMapper.
        
        Args:
            knowledge_base_service: Service for querying Knowledge Base
            cloud_service_service: Service for accessing crawled cloud service data
        """
        self.kb_service = knowledge_base_service or KnowledgeBaseService()
        self.db_service = cloud_service_service or CloudServiceService()
        
        # In-memory cache for frequently used mappings
        self.memory_cache: Dict[str, AWSServiceMapping] = {}
        
        # Load service categories
        self.service_categories = ServiceConfig.SUPPORTED_CATEGORIES
        
        logger.info("ServiceMapper initialized")
    
    def map_service(self, service_config: ServiceConfig) -> List[AWSServiceMapping]:
        """
        Map a cloud provider service to AWS equivalent(s).
        
        Args:
            service_config: Configuration of the service to map
            
        Returns:
            List of AWSServiceMapping objects, ranked by suitability
            
        Raises:
            ValueError: If service cannot be mapped
        """
        logger.info(
            f"Mapping service: {service_config.provider}/{service_config.service_name} "
            f"({service_config.service_type})"
        )
        
        # Check memory cache first
        cache_key = self._get_cache_key(service_config)
        if cache_key in self.memory_cache:
            logger.info(f"Found mapping in memory cache: {cache_key}")
            cached_mapping = self.memory_cache[cache_key]
            return [cached_mapping]
        
        # Check DynamoDB cache
        db_cached = self.db_service.get_mapping_cache(
            service_config.provider,
            service_config.service_name
        )
        
        if db_cached:
            logger.info(f"Found mapping in DynamoDB cache: {cache_key}")
            # Update hit count
            self.db_service.update_mapping_cache_hit(
                service_config.provider,
                service_config.service_name
            )
            
            # Convert to AWSServiceMapping
            mapping = db_cached.to_aws_service_mapping(
                explanation=f"Cached mapping from {service_config.provider} {service_config.service_name}"
            )
            
            # Store in memory cache
            self.memory_cache[cache_key] = mapping
            
            return [mapping]
        
        # Get crawled service information from database
        crawled_service = self.db_service.get_cloud_service(
            service_config.provider,
            service_config.service_name
        )
        
        # Build query for Knowledge Base
        query = self._build_mapping_query(service_config, crawled_service)
        
        # Query Knowledge Base for mapping rules
        try:
            kb_results = self.kb_service.query(query, max_results=5, min_score=0.5)
        except Exception as e:
            logger.error(f"Knowledge Base query failed: {e}")
            kb_results = []
        
        # Create mappings from KB results and crawled data
        mappings = self._create_mappings(service_config, crawled_service, kb_results)
        
        if not mappings:
            # If no mappings found, try fallback strategies
            mappings = self._fallback_mapping(service_config, crawled_service)
        
        if not mappings:
            raise ValueError(
                f"Could not find AWS equivalent for {service_config.provider} "
                f"{service_config.service_name}. Please contact AWS support for assistance."
            )
        
        # Rank mappings by suitability
        ranked_mappings = self._rank_mappings(mappings, service_config)
        
        # Cache the best mapping
        if ranked_mappings:
            self._cache_mapping(service_config, ranked_mappings[0])
        
        return ranked_mappings
    
    def _get_cache_key(self, service_config: ServiceConfig) -> str:
        """Generate cache key for a service configuration."""
        # Include provider, service name, and key specifications
        spec_str = json.dumps(service_config.specifications, sort_keys=True)
        return f"{service_config.provider}:{service_config.service_name}:{spec_str}"
    
    def _build_mapping_query(
        self,
        config: ServiceConfig,
        crawled: Optional[CloudService]
    ) -> str:
        """
        Build enhanced query using crawled service data.
        
        Args:
            config: Service configuration
            crawled: Crawled service data (if available)
            
        Returns:
            Query string for Knowledge Base
        """
        if crawled:
            query = f"""Find AWS service equivalent for {config.provider} {config.service_name}.
Service category: {crawled.service_category}
Description: {crawled.description}
Specifications: {json.dumps(config.specifications)}
Features: {', '.join(crawled.features[:5])}"""  # Limit features to avoid too long query
        else:
            query = f"""Find AWS service equivalent for {config.provider} {config.service_name}.
Service type: {config.service_type}
Specifications: {json.dumps(config.specifications)}"""
        
        return query
    
    def _create_mappings(
        self,
        config: ServiceConfig,
        crawled: Optional[CloudService],
        kb_results: List
    ) -> List[AWSServiceMapping]:
        """
        Create AWS service mappings from KB results and crawled data.
        
        Args:
            config: Service configuration
            crawled: Crawled service data
            kb_results: Knowledge Base query results
            
        Returns:
            List of AWSServiceMapping objects
        """
        mappings = []
        
        for result in kb_results:
            try:
                # Parse KB result content
                mapping_data = self._parse_kb_result(result.content, config, crawled)
                
                if mapping_data:
                    mapping = AWSServiceMapping(
                        aws_service=mapping_data['aws_service'],
                        aws_service_category=mapping_data.get('aws_service_category', config.service_type),
                        aws_service_type=mapping_data['aws_service_type'],
                        specifications=mapping_data.get('specifications', {}),
                        confidence_score=result.score,
                        explanation=mapping_data.get('explanation', ''),
                        alternatives=mapping_data.get('alternatives', [])
                    )
                    mappings.append(mapping)
                    
            except Exception as e:
                logger.warning(f"Failed to parse KB result: {e}")
                continue
        
        return mappings
    
    def _parse_kb_result(
        self,
        content: str,
        config: ServiceConfig,
        crawled: Optional[CloudService]
    ) -> Optional[Dict[str, Any]]:
        """
        Parse Knowledge Base result content to extract mapping information.
        
        Args:
            content: KB result content
            config: Service configuration
            crawled: Crawled service data
            
        Returns:
            Dictionary with mapping data or None if parsing fails
        """
        try:
            # Try to parse as JSON first
            data = json.loads(content)
            
            # Validate required fields
            if 'aws_equivalent' in data or 'aws_service' in data:
                aws_service = data.get('aws_equivalent') or data.get('aws_service')
                
                return {
                    'aws_service': aws_service,
                    'aws_service_category': data.get('service_type', config.service_type),
                    'aws_service_type': data.get('aws_service_type', ''),
                    'specifications': data.get('specifications', {}),
                    'explanation': data.get('notes', data.get('explanation', '')),
                    'alternatives': data.get('alternatives', [])
                }
        except json.JSONDecodeError:
            # If not JSON, try to extract information from text
            return self._parse_text_result(content, config)
        
        return None
    
    def _parse_text_result(
        self,
        content: str,
        config: ServiceConfig
    ) -> Optional[Dict[str, Any]]:
        """
        Parse text-based Knowledge Base result.
        
        Args:
            content: Text content
            config: Service configuration
            
        Returns:
            Dictionary with mapping data or None
        """
        # Simple text parsing logic
        # Look for AWS service names in the content
        aws_services = [
            'EC2', 'S3', 'RDS', 'Lambda', 'ECS', 'EKS', 'DynamoDB',
            'Aurora', 'ElastiCache', 'CloudFront', 'Route53', 'VPC',
            'SQS', 'SNS', 'Kinesis', 'EMR', 'Athena', 'Glue',
            'SageMaker', 'CloudWatch', 'IAM', 'KMS', 'EBS', 'EFS'
        ]
        
        for service in aws_services:
            if service in content:
                return {
                    'aws_service': service,
                    'aws_service_category': config.service_type,
                    'aws_service_type': '',  # Will need to be determined
                    'specifications': {},
                    'explanation': content[:200],  # First 200 chars as explanation
                    'alternatives': []
                }
        
        return None
    
    def _fallback_mapping(
        self,
        config: ServiceConfig,
        crawled: Optional[CloudService]
    ) -> List[AWSServiceMapping]:
        """
        Fallback mapping strategy when Knowledge Base returns no results.
        
        Uses simple rule-based mapping for common services.
        
        Args:
            config: Service configuration
            crawled: Crawled service data
            
        Returns:
            List of AWSServiceMapping objects
        """
        logger.info(f"Using fallback mapping for {config.provider}/{config.service_name}")
        
        # Simple rule-based mappings for common services
        fallback_rules = {
            'compute': {
                'ECS': ('EC2', 't3.medium', 'General purpose compute instance'),
                'VM': ('EC2', 't3.medium', 'Virtual machine instance'),
                'Instance': ('EC2', 't3.medium', 'Compute instance'),
            },
            'storage': {
                'OSS': ('S3', 'Standard', 'Object storage service'),
                'COS': ('S3', 'Standard', 'Cloud object storage'),
                'Blob': ('S3', 'Standard', 'Blob storage service'),
                'Storage': ('S3', 'Standard', 'General storage service'),
            },
            'database': {
                'RDS': ('RDS', 'db.t3.medium', 'Relational database service'),
                'MySQL': ('RDS', 'db.t3.medium', 'MySQL database'),
                'PostgreSQL': ('RDS', 'db.t3.medium', 'PostgreSQL database'),
                'NoSQL': ('DynamoDB', 'On-Demand', 'NoSQL database'),
            },
            'network': {
                'CDN': ('CloudFront', 'Standard', 'Content delivery network'),
                'LoadBalancer': ('ALB', 'Application', 'Application load balancer'),
                'VPN': ('VPN', 'Site-to-Site', 'VPN connection'),
            }
        }
        
        # Try to find a match in fallback rules
        category_rules = fallback_rules.get(config.service_type, {})
        
        for keyword, (aws_service, aws_type, explanation) in category_rules.items():
            if keyword.lower() in config.service_name.lower():
                mapping = AWSServiceMapping(
                    aws_service=aws_service,
                    aws_service_category=config.service_type,
                    aws_service_type=aws_type,
                    specifications={},
                    confidence_score=0.6,  # Lower confidence for fallback
                    explanation=f"Fallback mapping: {explanation}",
                    alternatives=[]
                )
                return [mapping]
        
        return []
    
    def _rank_mappings(
        self,
        mappings: List[AWSServiceMapping],
        config: ServiceConfig
    ) -> List[AWSServiceMapping]:
        """
        Rank mappings by suitability.
        
        Ranking factors:
        - Confidence score from Knowledge Base
        - Specification match
        - Cost efficiency
        
        Args:
            mappings: List of mappings to rank
            config: Original service configuration
            
        Returns:
            Sorted list of mappings (best first)
        """
        # Sort by confidence score (descending)
        ranked = sorted(mappings, key=lambda m: m.confidence_score, reverse=True)
        
        logger.info(f"Ranked {len(ranked)} mappings")
        for i, mapping in enumerate(ranked[:3]):  # Log top 3
            logger.info(
                f"  {i+1}. {mapping.aws_service} ({mapping.aws_service_type}) "
                f"- confidence: {mapping.confidence_score:.2f}"
            )
        
        return ranked
    
    def _cache_mapping(self, config: ServiceConfig, mapping: AWSServiceMapping) -> None:
        """
        Cache successful mapping for faster future lookups.
        
        Args:
            config: Service configuration
            mapping: AWS service mapping to cache
        """
        cache_key = self._get_cache_key(config)
        
        # Store in memory cache
        self.memory_cache[cache_key] = mapping
        
        # Store in DynamoDB cache
        try:
            cache_entry = ServiceMappingCache(
                mapping_id=mapping.mapping_id,
                source_provider=config.provider,
                source_service=config.service_name,
                source_specs=config.specifications,
                aws_service=mapping.aws_service,
                aws_service_type=mapping.aws_service_type,
                aws_specs=mapping.specifications,
                confidence_score=mapping.confidence_score,
                created_at=datetime.utcnow(),
                hit_count=1,
                last_used=datetime.utcnow()
            )
            
            self.db_service.create_mapping_cache(cache_entry)
            logger.info(f"Cached mapping: {cache_key}")
            
        except Exception as e:
            logger.warning(f"Failed to cache mapping in DynamoDB: {e}")
    
    def clear_memory_cache(self) -> None:
        """Clear the in-memory cache."""
        self.memory_cache.clear()
        logger.info("Memory cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        return {
            'memory_cache_size': len(self.memory_cache),
            'memory_cache_keys': list(self.memory_cache.keys())
        }


# Global instance
service_mapper = ServiceMapper()
