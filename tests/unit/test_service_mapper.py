"""
Unit tests for Service Mapper.

These tests verify specific service mappings and functionality.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock

from src.models.service_config import ServiceConfig
from src.models.cloud_service import AWSServiceMapping, ServiceMappingCache, CloudService
from src.services.service_mapper import ServiceMapper
from src.services.knowledge_base_service import KnowledgeBaseResult


class TestServiceMapper:
    """Unit tests for ServiceMapper class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create mock services
        self.mock_kb_service = Mock()
        self.mock_db_service = Mock()
        
        # Create mapper with mocks
        self.mapper = ServiceMapper(
            knowledge_base_service=self.mock_kb_service,
            cloud_service_service=self.mock_db_service
        )
    
    def test_alibaba_ecs_to_aws_ec2(self):
        """Test mapping Alibaba ECS to AWS EC2."""
        # Arrange
        config = ServiceConfig(
            provider='alibaba',
            service_type='compute',
            service_name='ECS',
            specifications={'cpu': 4, 'memory': 8, 'storage': 100}
        )
        
        # Mock crawled service data
        crawled_service = CloudService(
            service_id='test-id',
            provider='alibaba',
            service_name='ECS',
            service_name_en='Elastic Compute Service',
            service_name_zh='弹性计算服务',
            service_category='compute',
            description='Alibaba Cloud ECS provides scalable computing capacity',
            specifications={'cpu': 4, 'memory': 8},
            features=['Auto Scaling', 'Load Balancing'],
            pricing_info=None,
            source_url='https://www.alibabacloud.com/product/ecs',
            crawled_at=datetime.now(),
            last_updated=datetime.now(),
            data_quality_score=0.9,
            manual_review_required=False
        )
        
        # Mock KB result
        kb_result = KnowledgeBaseResult(
            content='{"aws_service": "EC2", "aws_service_type": "t3.large", "service_type": "compute", "notes": "General purpose compute instance"}',
            score=0.9,
            metadata={},
            source_location=None
        )
        
        self.mock_db_service.get_mapping_cache.return_value = None
        self.mock_db_service.get_cloud_service.return_value = crawled_service
        self.mock_kb_service.query.return_value = [kb_result]
        self.mock_db_service.create_mapping_cache.return_value = None
        
        # Act
        mappings = self.mapper.map_service(config)
        
        # Assert
        assert len(mappings) > 0
        assert mappings[0].aws_service == 'EC2'
        assert mappings[0].aws_service_type == 't3.large'
        assert mappings[0].aws_service_category == 'compute'
        assert mappings[0].confidence_score == 0.9
    
    def test_alibaba_oss_to_aws_s3(self):
        """Test mapping Alibaba OSS to AWS S3."""
        # Arrange
        config = ServiceConfig(
            provider='alibaba',
            service_type='storage',
            service_name='OSS',
            specifications={'capacity': 1000, 'storage_class': 'Standard'}
        )
        
        # Mock KB result
        kb_result = KnowledgeBaseResult(
            content='{"aws_service": "S3", "aws_service_type": "Standard", "service_type": "storage", "notes": "Object storage service"}',
            score=0.95,
            metadata={},
            source_location=None
        )
        
        self.mock_db_service.get_mapping_cache.return_value = None
        self.mock_db_service.get_cloud_service.return_value = None
        self.mock_kb_service.query.return_value = [kb_result]
        self.mock_db_service.create_mapping_cache.return_value = None
        
        # Act
        mappings = self.mapper.map_service(config)
        
        # Assert
        assert len(mappings) > 0
        assert mappings[0].aws_service == 'S3'
        assert mappings[0].aws_service_type == 'Standard'
        assert mappings[0].aws_service_category == 'storage'
    
    def test_cache_functionality(self):
        """Test that mapping cache is used for repeated queries."""
        # Arrange
        config = ServiceConfig(
            provider='huawei',
            service_type='database',
            service_name='RDS',
            specifications={'cpu': 2, 'memory': 4, 'storage': 50}
        )
        
        # Mock cached mapping
        cached_mapping = ServiceMappingCache(
            mapping_id='cached-id',
            source_provider='huawei',
            source_service='RDS',
            source_specs={'cpu': 2, 'memory': 4, 'storage': 50},
            aws_service='RDS',
            aws_service_type='db.t3.small',
            aws_specs={'cpu': 2, 'memory': 4},
            confidence_score=0.85,
            created_at=datetime.now(),
            hit_count=5,
            last_used=datetime.now()
        )
        
        self.mock_db_service.get_mapping_cache.return_value = cached_mapping
        self.mock_db_service.update_mapping_cache_hit.return_value = None
        
        # Act
        mappings = self.mapper.map_service(config)
        
        # Assert
        assert len(mappings) > 0
        assert mappings[0].aws_service == 'RDS'
        assert mappings[0].aws_service_type == 'db.t3.small'
        
        # Verify cache was used (KB was not queried)
        self.mock_kb_service.query.assert_not_called()
        self.mock_db_service.update_mapping_cache_hit.assert_called_once()
    
    def test_knowledge_base_integration(self):
        """Test Knowledge Base query integration."""
        # Arrange
        config = ServiceConfig(
            provider='tencent',
            service_type='network',
            service_name='CDN',
            specifications={'bandwidth': 100}
        )
        
        # Mock KB result
        kb_result = KnowledgeBaseResult(
            content='{"aws_service": "CloudFront", "aws_service_type": "Standard", "service_type": "cdn", "notes": "Content delivery network"}',
            score=0.88,
            metadata={},
            source_location=None
        )
        
        self.mock_db_service.get_mapping_cache.return_value = None
        self.mock_db_service.get_cloud_service.return_value = None
        self.mock_kb_service.query.return_value = [kb_result]
        self.mock_db_service.create_mapping_cache.return_value = None
        
        # Act
        mappings = self.mapper.map_service(config)
        
        # Assert
        assert len(mappings) > 0
        assert mappings[0].aws_service == 'CloudFront'
        
        # Verify KB was queried
        self.mock_kb_service.query.assert_called_once()
        query_arg = self.mock_kb_service.query.call_args[0][0]
        assert 'tencent' in query_arg.lower()
        assert 'cdn' in query_arg.lower()
    
    def test_fallback_mapping_for_compute(self):
        """Test fallback mapping when KB returns no results."""
        # Arrange
        config = ServiceConfig(
            provider='gcp',
            service_type='compute',
            service_name='Instance',  # Use keyword that matches fallback rules
            specifications={'cpu': 2, 'memory': 4}
        )
        
        self.mock_db_service.get_mapping_cache.return_value = None
        self.mock_db_service.get_cloud_service.return_value = None
        self.mock_kb_service.query.return_value = []  # No KB results
        self.mock_db_service.create_mapping_cache.return_value = None
        
        # Act
        mappings = self.mapper.map_service(config)
        
        # Assert
        assert len(mappings) > 0
        # Fallback should map compute to EC2
        assert mappings[0].aws_service == 'EC2'
        assert mappings[0].confidence_score < 0.7  # Lower confidence for fallback
    
    def test_fallback_mapping_for_storage(self):
        """Test fallback mapping for storage services."""
        # Arrange
        config = ServiceConfig(
            provider='azure',
            service_type='storage',
            service_name='Blob Storage',
            specifications={'capacity': 500}
        )
        
        self.mock_db_service.get_mapping_cache.return_value = None
        self.mock_db_service.get_cloud_service.return_value = None
        self.mock_kb_service.query.return_value = []  # No KB results
        self.mock_db_service.create_mapping_cache.return_value = None
        
        # Act
        mappings = self.mapper.map_service(config)
        
        # Assert
        assert len(mappings) > 0
        # Fallback should map storage to S3
        assert mappings[0].aws_service == 'S3'
    
    def test_multiple_kb_results_ranked_by_confidence(self):
        """Test that multiple KB results are ranked by confidence score."""
        # Arrange
        config = ServiceConfig(
            provider='alibaba',
            service_type='container',
            service_name='Container Service',
            specifications={'capacity': 10}
        )
        
        # Mock multiple KB results with different scores - include explanation
        kb_results = [
            KnowledgeBaseResult(
                content='{"aws_service": "ECS", "aws_service_type": "Standard", "service_type": "container", "explanation": "Elastic Container Service"}',
                score=0.75,
                metadata={},
                source_location=None
            ),
            KnowledgeBaseResult(
                content='{"aws_service": "EKS", "aws_service_type": "Standard", "service_type": "container", "explanation": "Elastic Kubernetes Service"}',
                score=0.90,
                metadata={},
                source_location=None
            ),
            KnowledgeBaseResult(
                content='{"aws_service": "Fargate", "aws_service_type": "Standard", "service_type": "container", "explanation": "Serverless container service"}',
                score=0.65,
                metadata={},
                source_location=None
            )
        ]
        
        self.mock_db_service.get_mapping_cache.return_value = None
        self.mock_db_service.get_cloud_service.return_value = None
        self.mock_kb_service.query.return_value = kb_results
        self.mock_db_service.create_mapping_cache.return_value = None
        
        # Act
        mappings = self.mapper.map_service(config)
        
        # Assert
        assert len(mappings) == 3
        # Should be ranked by confidence (descending)
        assert mappings[0].aws_service == 'EKS'  # Highest score (0.90)
        assert mappings[0].confidence_score == 0.90
        assert mappings[1].aws_service == 'ECS'  # Second highest (0.75)
        assert mappings[1].confidence_score == 0.75
        assert mappings[2].aws_service == 'Fargate'  # Lowest (0.65)
        assert mappings[2].confidence_score == 0.65
    
    def test_memory_cache_functionality(self):
        """Test that memory cache improves performance."""
        # Arrange
        config = ServiceConfig(
            provider='alibaba',
            service_type='compute',
            service_name='ECS',
            specifications={'cpu': 2, 'memory': 4}
        )
        
        kb_result = KnowledgeBaseResult(
            content='{"aws_service": "EC2", "aws_service_type": "t3.small", "service_type": "compute"}',
            score=0.85,
            metadata={},
            source_location=None
        )
        
        self.mock_db_service.get_mapping_cache.return_value = None
        self.mock_db_service.get_cloud_service.return_value = None
        self.mock_kb_service.query.return_value = [kb_result]
        self.mock_db_service.create_mapping_cache.return_value = None
        
        # Act - First call
        mappings1 = self.mapper.map_service(config)
        
        # Act - Second call (should use memory cache)
        mappings2 = self.mapper.map_service(config)
        
        # Assert
        assert mappings1[0].aws_service == mappings2[0].aws_service
        # KB should only be queried once (first call)
        assert self.mock_kb_service.query.call_count == 1
        
        # Check cache stats
        cache_stats = self.mapper.get_cache_stats()
        assert cache_stats['memory_cache_size'] > 0
    
    def test_clear_memory_cache(self):
        """Test clearing the memory cache."""
        # Arrange
        config = ServiceConfig(
            provider='alibaba',
            service_type='compute',
            service_name='ECS',
            specifications={'cpu': 2, 'memory': 4}
        )
        
        kb_result = KnowledgeBaseResult(
            content='{"aws_service": "EC2", "aws_service_type": "t3.small", "service_type": "compute"}',
            score=0.85,
            metadata={},
            source_location=None
        )
        
        self.mock_db_service.get_mapping_cache.return_value = None
        self.mock_db_service.get_cloud_service.return_value = None
        self.mock_kb_service.query.return_value = [kb_result]
        self.mock_db_service.create_mapping_cache.return_value = None
        
        # Act
        self.mapper.map_service(config)
        assert self.mapper.get_cache_stats()['memory_cache_size'] > 0
        
        self.mapper.clear_memory_cache()
        
        # Assert
        assert self.mapper.get_cache_stats()['memory_cache_size'] == 0
    
    def test_error_when_no_mapping_found(self):
        """Test that appropriate error is raised when no mapping can be found."""
        # Arrange - use valid provider but service that won't match fallback
        config = ServiceConfig(
            provider='gcp',
            service_type='iot',  # Valid type but no fallback rule
            service_name='Unknown IoT Service',
            specifications={}
        )
        
        self.mock_db_service.get_mapping_cache.return_value = None
        self.mock_db_service.get_cloud_service.return_value = None
        self.mock_kb_service.query.return_value = []  # No KB results
        
        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            self.mapper.map_service(config)
        
        assert "Could not find AWS equivalent" in str(exc_info.value)
        assert "contact aws support" in str(exc_info.value).lower()
    
    def test_crawled_service_data_enhances_query(self):
        """Test that crawled service data is used to enhance KB query."""
        # Arrange
        config = ServiceConfig(
            provider='alibaba',
            service_type='database',
            service_name='PolarDB',
            specifications={'cpu': 4, 'memory': 16}
        )
        
        crawled_service = CloudService(
            service_id='test-id',
            provider='alibaba',
            service_name='PolarDB',
            service_name_en='PolarDB',
            service_name_zh='云原生数据库',
            service_category='database',
            description='Cloud-native relational database compatible with MySQL',
            specifications={'cpu': 4, 'memory': 16},
            features=['MySQL Compatible', 'High Availability', 'Auto Scaling'],
            pricing_info=None,
            source_url='https://www.alibabacloud.com/product/polardb',
            crawled_at=datetime.now(),
            last_updated=datetime.now(),
            data_quality_score=0.95,
            manual_review_required=False
        )
        
        kb_result = KnowledgeBaseResult(
            content='{"aws_service": "Aurora", "aws_service_type": "MySQL", "service_type": "database", "explanation": "MySQL-compatible cloud-native database"}',
            score=0.92,
            metadata={},
            source_location=None
        )
        
        self.mock_db_service.get_mapping_cache.return_value = None
        self.mock_db_service.get_cloud_service.return_value = crawled_service
        self.mock_kb_service.query.return_value = [kb_result]
        self.mock_db_service.create_mapping_cache.return_value = None
        
        # Act
        mappings = self.mapper.map_service(config)
        
        # Assert
        assert len(mappings) > 0
        assert mappings[0].aws_service == 'Aurora'
        
        # Verify KB query included crawled data
        query_arg = self.mock_kb_service.query.call_args[0][0]
        assert 'PolarDB' in query_arg
        assert 'database' in query_arg.lower()
        assert 'Cloud-native relational database' in query_arg


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
