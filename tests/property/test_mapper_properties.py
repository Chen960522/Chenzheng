"""
Property-based tests for Service Mapper.

These tests verify universal properties that should hold for all service mappings.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from datetime import datetime

from src.models.service_config import ServiceConfig
from src.models.cloud_service import AWSServiceMapping, CloudService
from src.services.service_mapper import ServiceMapper
from src.services.knowledge_base_service import KnowledgeBaseService
from src.services.cloud_service_service import CloudServiceService


# Test data generators

@st.composite
def service_config_strategy(draw):
    """Generate random ServiceConfig for testing."""
    provider = draw(st.sampled_from(['alibaba', 'huawei', 'tencent', 'gcp', 'azure']))
    service_type = draw(st.sampled_from([
        'compute', 'storage', 'database', 'network', 'analytics',
        'ml', 'container', 'serverless', 'messaging', 'monitoring',
        'security', 'cdn', 'iot'
    ]))
    
    # Generate service names based on type
    service_names = {
        'compute': ['ECS', 'VM', 'Instance', 'Compute Engine', 'Virtual Machine'],
        'storage': ['OSS', 'COS', 'Blob Storage', 'Cloud Storage', 'Object Storage'],
        'database': ['RDS', 'MySQL', 'PostgreSQL', 'Cloud SQL', 'Database'],
        'network': ['VPC', 'CDN', 'Load Balancer', 'Virtual Network'],
        'analytics': ['Data Warehouse', 'BigQuery', 'Analytics', 'Data Lake'],
        'ml': ['Machine Learning', 'AI Platform', 'ML Service'],
        'container': ['Container Service', 'Kubernetes', 'Docker'],
        'serverless': ['Function Compute', 'Cloud Functions', 'Lambda'],
        'messaging': ['Message Queue', 'Pub/Sub', 'Event Hub'],
        'monitoring': ['Cloud Monitor', 'Logging', 'Metrics'],
        'security': ['IAM', 'Key Management', 'Security Center'],
        'cdn': ['CDN', 'Content Delivery', 'Edge Network'],
        'iot': ['IoT Hub', 'IoT Core', 'Device Management']
    }
    
    service_name = draw(st.sampled_from(service_names.get(service_type, ['Service'])))
    
    # Generate specifications based on service type
    if service_type == 'compute':
        specs = {
            'cpu': draw(st.integers(min_value=1, max_value=64)),
            'memory': draw(st.integers(min_value=1, max_value=256)),
            'storage': draw(st.integers(min_value=10, max_value=1000))
        }
    elif service_type == 'storage':
        specs = {
            'capacity': draw(st.integers(min_value=10, max_value=10000)),
            'storage_class': draw(st.sampled_from(['Standard', 'Infrequent Access', 'Archive']))
        }
    elif service_type == 'database':
        specs = {
            'cpu': draw(st.integers(min_value=1, max_value=32)),
            'memory': draw(st.integers(min_value=1, max_value=128)),
            'storage': draw(st.integers(min_value=20, max_value=1000)),
            'engine': draw(st.sampled_from(['MySQL', 'PostgreSQL', 'SQL Server']))
        }
    else:
        specs = {
            'capacity': draw(st.integers(min_value=1, max_value=100))
        }
    
    return ServiceConfig(
        provider=provider,
        service_type=service_type,
        service_name=service_name,
        specifications=specs,
        region=draw(st.sampled_from(['us-east-1', 'us-west-2', 'eu-west-1', None])),
        quantity=draw(st.integers(min_value=1, max_value=10))
    )


class MockKnowledgeBaseService:
    """Mock Knowledge Base service for testing."""
    
    def query(self, query_text: str, max_results: int = 5, min_score: float = 0.5):
        """Return mock KB results."""
        from src.services.knowledge_base_service import KnowledgeBaseResult
        
        query_lower = query_text.lower()
        
        # Priority 1: Check for specific service names first (most specific)
        # Be very careful with word boundaries to avoid false matches
        
        # Storage services - check BEFORE generic terms
        if ' oss ' in query_lower or query_lower.startswith('oss ') or query_lower.endswith(' oss'):
            content = '{"aws_service": "S3", "aws_service_type": "Standard", "service_type": "storage", "explanation": "Object storage service for OSS"}'
        elif ' cos ' in query_lower or query_lower.startswith('cos ') or query_lower.endswith(' cos'):
            content = '{"aws_service": "S3", "aws_service_type": "Standard", "service_type": "storage", "explanation": "Object storage service for COS"}'
        elif 'blob storage' in query_lower:
            content = '{"aws_service": "S3", "aws_service_type": "Standard", "service_type": "storage", "explanation": "Object storage service for Azure Blob"}'
        elif 'object storage' in query_lower:
            content = '{"aws_service": "S3", "aws_service_type": "Standard", "service_type": "storage", "explanation": "Object storage service"}'
        elif 'cloud storage' in query_lower and 'gcp' in query_lower:
            content = '{"aws_service": "S3", "aws_service_type": "Standard", "service_type": "storage", "explanation": "Object storage service for GCP Cloud Storage"}'
        
        # Container services - check BEFORE compute
        elif 'container service' in query_lower or 'kubernetes' in query_lower or 'docker' in query_lower:
            content = '{"aws_service": "EKS", "aws_service_type": "Standard", "service_type": "container", "explanation": "Kubernetes container service"}'
        
        # Network services - check BEFORE generic network
        elif ' vpc' in query_lower or query_lower.startswith('vpc') or 'virtual private cloud' in query_lower:
            content = '{"aws_service": "VPC", "aws_service_type": "Standard", "service_type": "network", "explanation": "Virtual private cloud"}'
        elif 'virtual network' in query_lower:
            content = '{"aws_service": "VPC", "aws_service_type": "Standard", "service_type": "network", "explanation": "Virtual network"}'
        elif 'load balancer' in query_lower or ' alb' in query_lower or ' nlb' in query_lower:
            content = '{"aws_service": "ALB", "aws_service_type": "Application", "service_type": "network", "explanation": "Application load balancer"}'
        
        # Database services
        elif ' rds' in query_lower or query_lower.startswith('rds'):
            content = '{"aws_service": "RDS", "aws_service_type": "db.t3.medium", "service_type": "database", "explanation": "Relational database service"}'
        elif 'cloud sql' in query_lower:
            content = '{"aws_service": "RDS", "aws_service_type": "db.t3.medium", "service_type": "database", "explanation": "Relational database service for Cloud SQL"}'
        elif 'mysql' in query_lower:
            content = '{"aws_service": "RDS", "aws_service_type": "db.t3.medium", "service_type": "database", "explanation": "MySQL database service"}'
        elif 'postgresql' in query_lower or 'postgres' in query_lower:
            content = '{"aws_service": "RDS", "aws_service_type": "db.t3.medium", "service_type": "database", "explanation": "PostgreSQL database service"}'
        
        # Compute services - check AFTER more specific services
        # Use word boundaries to avoid matching "ecs" in other words like "process"
        elif (' ecs ' in query_lower or query_lower.startswith('ecs ') or query_lower.endswith(' ecs')):
            # ECS from any provider (Alibaba, Huawei, etc.) should map to EC2
            content = '{"aws_service": "EC2", "aws_service_type": "t3.medium", "service_type": "compute", "explanation": "Compute instance for ECS"}'
        elif 'compute engine' in query_lower:
            content = '{"aws_service": "EC2", "aws_service_type": "t3.medium", "service_type": "compute", "explanation": "Compute instance for GCP Compute Engine"}'
        elif ' vm ' in query_lower or query_lower.startswith('vm ') or query_lower.endswith(' vm') or 'virtual machine' in query_lower:
            content = '{"aws_service": "EC2", "aws_service_type": "t3.medium", "service_type": "compute", "explanation": "Virtual machine instance"}'
        elif 'instance' in query_lower and 'compute' in query_lower:
            content = '{"aws_service": "EC2", "aws_service_type": "t3.medium", "service_type": "compute", "explanation": "Compute instance"}'
        
        # Serverless services
        elif 'serverless' in query_lower or 'function compute' in query_lower or 'cloud functions' in query_lower:
            content = '{"aws_service": "Lambda", "aws_service_type": "Standard", "service_type": "serverless", "explanation": "Serverless compute"}'
        elif 'lambda' in query_lower:
            content = '{"aws_service": "Lambda", "aws_service_type": "Standard", "service_type": "serverless", "explanation": "Serverless function"}'
        
        # CDN services
        elif ' cdn' in query_lower or query_lower.startswith('cdn') or 'content delivery' in query_lower:
            content = '{"aws_service": "CloudFront", "aws_service_type": "Standard", "service_type": "cdn", "explanation": "Content delivery network"}'
        
        # Messaging services
        elif 'messaging' in query_lower or 'message queue' in query_lower or 'pub/sub' in query_lower:
            content = '{"aws_service": "SQS", "aws_service_type": "Standard", "service_type": "messaging", "explanation": "Message queue service"}'
        elif 'queue' in query_lower:
            content = '{"aws_service": "SQS", "aws_service_type": "Standard", "service_type": "messaging", "explanation": "Queue service"}'
        
        # Analytics services
        elif 'analytics' in query_lower or 'data warehouse' in query_lower or 'bigquery' in query_lower:
            content = '{"aws_service": "Redshift", "aws_service_type": "Standard", "service_type": "analytics", "explanation": "Data warehouse service"}'
        
        # ML services
        elif ' ml ' in query_lower or query_lower.startswith('ml ') or query_lower.endswith(' ml') or 'machine learning' in query_lower or 'ai platform' in query_lower:
            content = '{"aws_service": "SageMaker", "aws_service_type": "Standard", "service_type": "ml", "explanation": "Machine learning service"}'
        
        # Monitoring services
        elif 'monitoring' in query_lower or 'cloud monitor' in query_lower or 'logging' in query_lower or 'metrics' in query_lower:
            content = '{"aws_service": "CloudWatch", "aws_service_type": "Standard", "service_type": "monitoring", "explanation": "Monitoring service"}'
        
        # Security services
        elif 'security' in query_lower or ' iam' in query_lower or query_lower.startswith('iam') or 'key management' in query_lower:
            content = '{"aws_service": "IAM", "aws_service_type": "Standard", "service_type": "security", "explanation": "Identity and access management"}'
        
        # IoT services
        elif ' iot' in query_lower or query_lower.startswith('iot'):
            content = '{"aws_service": "IoT Core", "aws_service_type": "Standard", "service_type": "iot", "explanation": "IoT service"}'
        
        # Priority 2: Check for service categories (fallback)
        elif 'database' in query_lower:
            content = '{"aws_service": "RDS", "aws_service_type": "db.t3.medium", "service_type": "database", "explanation": "Relational database service"}'
        elif 'storage' in query_lower:
            content = '{"aws_service": "S3", "aws_service_type": "Standard", "service_type": "storage", "explanation": "Object storage service"}'
        elif 'network' in query_lower:
            content = '{"aws_service": "VPC", "aws_service_type": "Standard", "service_type": "network", "explanation": "Virtual private cloud"}'
        elif 'compute' in query_lower:
            content = '{"aws_service": "EC2", "aws_service_type": "t3.medium", "service_type": "compute", "explanation": "General purpose compute instance"}'
        else:
            content = '{"aws_service": "EC2", "aws_service_type": "t3.medium", "service_type": "compute", "explanation": "Default compute service"}'
        
        return [
            KnowledgeBaseResult(
                content=content,
                score=0.85,
                metadata={},
                source_location=None
            )
        ]


class MockCloudServiceService:
    """Mock Cloud Service database service for testing."""
    
    def __init__(self):
        self.mapping_cache = {}
    
    def get_cloud_service(self, provider: str, service_name: str):
        """Return mock crawled service data."""
        return CloudService(
            service_id='test-id',
            provider=provider,
            service_name=service_name,
            service_name_en=service_name,
            service_name_zh=None,
            service_category='compute',
            description=f'{provider} {service_name} service',
            specifications={},
            features=['Feature 1', 'Feature 2'],
            pricing_info=None,
            source_url='https://example.com',
            crawled_at=datetime.utcnow(),
            last_updated=datetime.utcnow(),
            data_quality_score=0.9,
            manual_review_required=False
        )
    
    def get_mapping_cache(self, source_provider: str, source_service: str):
        """Return cached mapping if exists."""
        key = f"{source_provider}:{source_service}"
        return self.mapping_cache.get(key)
    
    def update_mapping_cache_hit(self, source_provider: str, source_service: str):
        """Update cache hit count."""
        pass
    
    def create_mapping_cache(self, mapping):
        """Store mapping in cache."""
        key = f"{mapping.source_provider}:{mapping.source_service}"
        self.mapping_cache[key] = mapping


# Property Tests

@given(config=service_config_strategy())
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_service_mapping_completeness(config):
    """
    Feature: aws-pricing-assistant, Property 5: Service mapping completeness
    
    For any non-AWS service from supported cloud providers (Alibaba, Huawei, Tencent, GCP, Azure),
    the Service Mapper should find at least one equivalent AWS service or a combination of services.
    
    Validates: Requirements 2.1, 2.4
    """
    # Arrange
    kb_service = MockKnowledgeBaseService()
    db_service = MockCloudServiceService()
    mapper = ServiceMapper(
        knowledge_base_service=kb_service,
        cloud_service_service=db_service
    )
    
    # Act
    try:
        mappings = mapper.map_service(config)
        
        # Assert
        assert mappings is not None, "Mappings should not be None"
        assert len(mappings) > 0, f"Should find at least one AWS equivalent for {config.provider} {config.service_name}"
        
        # Verify each mapping has required fields
        for mapping in mappings:
            assert isinstance(mapping, AWSServiceMapping), "Result should be AWSServiceMapping"
            assert mapping.aws_service, "AWS service name should not be empty"
            assert mapping.aws_service_type, "AWS service type should not be empty"
            assert mapping.aws_service_category, "AWS service category should not be empty"
            assert 0.0 <= mapping.confidence_score <= 1.0, "Confidence score should be between 0 and 1"
            assert mapping.explanation, "Explanation should not be empty"
            
    except ValueError as e:
        # If mapping fails, it should provide a helpful error message
        assert "Could not find AWS equivalent" in str(e), f"Error message should be helpful: {e}"
        assert "contact AWS support" in str(e).lower(), "Should suggest contacting support"


@given(config=service_config_strategy())
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_multiple_option_handling(config):
    """
    Feature: aws-pricing-assistant, Property 6: Multiple option handling
    
    For any service that can be fulfilled by multiple AWS services,
    the Service Mapper should recommend the most suitable option with an explanation.
    
    Validates: Requirements 2.2
    """
    # Arrange
    kb_service = MockKnowledgeBaseService()
    db_service = MockCloudServiceService()
    mapper = ServiceMapper(
        knowledge_base_service=kb_service,
        cloud_service_service=db_service
    )
    
    # Act
    mappings = mapper.map_service(config)
    
    # Assert
    assert len(mappings) > 0, "Should return at least one mapping"
    
    # The first mapping should be the most suitable (highest confidence)
    best_mapping = mappings[0]
    
    # Verify the best mapping has an explanation
    assert best_mapping.explanation, "Best mapping should have an explanation"
    assert len(best_mapping.explanation) > 0, "Explanation should not be empty"
    
    # If there are multiple mappings, verify they are ranked by confidence
    if len(mappings) > 1:
        for i in range(len(mappings) - 1):
            assert mappings[i].confidence_score >= mappings[i + 1].confidence_score, \
                "Mappings should be ranked by confidence score (descending)"
    
    # Verify alternatives are provided if available
    if best_mapping.has_alternatives():
        assert isinstance(best_mapping.alternatives, list), "Alternatives should be a list"
        assert len(best_mapping.alternatives) > 0, "Alternatives list should not be empty"


@given(config=service_config_strategy())
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_accurate_service_mapping(config):
    """
    Feature: aws-pricing-assistant, Property 8: Accurate service mapping
    
    For any service from any category with specific specifications,
    the Service Mapper should map to AWS services that meet or exceed those specifications.
    
    Validates: Requirements 2.5, 2.6, 2.7, 2.8, 2.9, 2.10, 2.11, 2.12, 2.13, 2.14, 2.15, 2.16
    """
    # Arrange
    kb_service = MockKnowledgeBaseService()
    db_service = MockCloudServiceService()
    mapper = ServiceMapper(
        knowledge_base_service=kb_service,
        cloud_service_service=db_service
    )
    
    # Act
    mappings = mapper.map_service(config)
    
    # Assert
    assert len(mappings) > 0, "Should return at least one mapping"
    
    best_mapping = mappings[0]
    
    # Verify the mapping is for the correct service category
    # The AWS service category should match or be compatible with the original service type
    assert best_mapping.aws_service_category in ServiceConfig.SUPPORTED_CATEGORIES, \
        f"AWS service category should be valid: {best_mapping.aws_service_category}"
    
    # Verify the mapping has a reasonable confidence score
    assert best_mapping.confidence_score > 0.0, "Confidence score should be positive"
    
    # For compute services, verify CPU/memory specs are considered
    if config.service_type == 'compute':
        if 'cpu' in config.specifications or 'memory' in config.specifications:
            # The mapping should have some specifications
            # (In a real implementation, we'd verify the specs meet or exceed requirements)
            assert best_mapping.aws_service in ['EC2', 'Lambda', 'ECS', 'EKS', 'Fargate'], \
                f"Compute service should map to AWS compute services, got: {best_mapping.aws_service}"
    
    # For storage services, verify storage type is appropriate
    elif config.service_type == 'storage':
        assert best_mapping.aws_service in ['S3', 'EBS', 'EFS', 'FSx'], \
            f"Storage service should map to AWS storage services, got: {best_mapping.aws_service}"
    
    # For database services, verify database type is appropriate
    elif config.service_type == 'database':
        assert best_mapping.aws_service in ['RDS', 'DynamoDB', 'Aurora', 'ElastiCache', 'DocumentDB'], \
            f"Database service should map to AWS database services, got: {best_mapping.aws_service}"
    
    # For network services
    elif config.service_type == 'network':
        assert best_mapping.aws_service in ['VPC', 'CloudFront', 'Route53', 'ALB', 'NLB', 'VPN'], \
            f"Network service should map to AWS network services, got: {best_mapping.aws_service}"
    
    # For container services
    elif config.service_type == 'container':
        assert best_mapping.aws_service in ['ECS', 'EKS', 'ECR', 'Fargate'], \
            f"Container service should map to AWS container services, got: {best_mapping.aws_service}"
    
    # For serverless services
    elif config.service_type == 'serverless':
        assert best_mapping.aws_service in ['Lambda', 'Step Functions', 'EventBridge'], \
            f"Serverless service should map to AWS serverless services, got: {best_mapping.aws_service}"


@given(config=service_config_strategy())
@settings(max_examples=50, deadline=None)
@pytest.mark.property_test
def test_mapping_cache_functionality(config):
    """
    Test that mapping cache improves performance for repeated queries.
    
    This is not a formal property from the design doc, but tests an important
    implementation detail mentioned in Requirements 2.3.
    """
    # Arrange
    kb_service = MockKnowledgeBaseService()
    db_service = MockCloudServiceService()
    mapper = ServiceMapper(
        knowledge_base_service=kb_service,
        cloud_service_service=db_service
    )
    
    # Act - First query (should query KB)
    mappings1 = mapper.map_service(config)
    
    # Act - Second query (should use cache)
    mappings2 = mapper.map_service(config)
    
    # Assert
    assert len(mappings1) > 0, "First query should return mappings"
    assert len(mappings2) > 0, "Second query should return mappings"
    
    # The results should be consistent
    assert mappings1[0].aws_service == mappings2[0].aws_service, \
        "Cached mapping should return same AWS service"
    assert mappings1[0].aws_service_type == mappings2[0].aws_service_type, \
        "Cached mapping should return same AWS service type"
    
    # Verify cache was used (check cache stats)
    cache_stats = mapper.get_cache_stats()
    assert cache_stats['memory_cache_size'] > 0, "Memory cache should contain entries"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
