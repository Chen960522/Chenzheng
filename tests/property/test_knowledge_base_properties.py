"""
Property-based tests for Knowledge Base query relevance.

Feature: aws-pricing-assistant, Property 15: Knowledge Base query relevance
Validates: Requirements 4.2, 4.3

Property 15: Knowledge Base query relevance
For any query to the Knowledge Base for service mappings or pricing information,
the results should be relevant to the query.
"""

import pytest
from hypothesis import given, strategies as st, settings as hypothesis_settings, assume, HealthCheck
from unittest.mock import Mock, patch
import os
import sys

# Ensure src is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.services.knowledge_base_service import (
    KnowledgeBaseService,
    KnowledgeBaseResult
)


# Test data strategies
cloud_providers = st.sampled_from(['alibaba', 'huawei', 'tencent', 'gcp', 'azure'])
service_names = st.sampled_from([
    'ECS', 'CVM', 'Virtual Machines', 'Compute Engine',
    'OSS', 'COS', 'Blob Storage', 'Cloud Storage',
    'RDS', 'TencentDB', 'Cloud SQL', 'Azure SQL Database',
    'SLB', 'CLB', 'Load Balancer', 'Cloud Load Balancing',
    'CDN', 'CloudFront'
])

aws_services = st.sampled_from([
    'EC2', 'S3', 'RDS', 'Lambda', 'ECS', 'EKS',
    'DynamoDB', 'CloudFront', 'ELB', 'VPC'
])

aws_regions = st.sampled_from([
    'us-east-1', 'us-west-2', 'eu-west-1', 'ap-southeast-1'
])


class TestKnowledgeBaseQueryRelevance:
    """Property tests for Knowledge Base query relevance."""
    
    @pytest.fixture
    def kb_service(self):
        """Create Knowledge Base service instance."""
        # Skip if Knowledge Base ID not configured
        if not os.getenv('BEDROCK_KNOWLEDGE_BASE_ID'):
            pytest.skip("Knowledge Base ID not configured")
        
        return KnowledgeBaseService()
    
    @pytest.fixture
    def mock_kb_service(self):
        """Create mock Knowledge Base service for testing without AWS."""
        service = KnowledgeBaseService()
        
        # Mock the client
        service.client = Mock()
        service.kb_id = "test-kb-id"
        
        return service
    
    @given(
        provider=cloud_providers,
        service_name=service_names
    )
    @hypothesis_settings(
        max_examples=20,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_service_mapping_query_returns_relevant_results(
        self,
        mock_kb_service,
        provider,
        service_name
    ):
        """
        Property 15: Knowledge Base query relevance (service mappings)
        
        For any query to the Knowledge Base for service mappings,
        the results should contain relevant information about the queried service.
        
        **Validates: Requirements 4.2, 4.3**
        """
        # Mock response with relevant results
        mock_results = [
            {
                'score': 0.85,
                'content': {
                    'text': f'{provider} {service_name} maps to AWS EC2 instances'
                },
                'metadata': {
                    'provider': provider,
                    'service': service_name
                },
                'location': {
                    's3Location': {
                        'uri': f's3://bucket/service_mappings/{provider}_mappings.json'
                    }
                }
            }
        ]
        
        mock_kb_service.client.retrieve.return_value = {
            'retrievalResults': mock_results
        }
        
        # Query for service mapping
        results = mock_kb_service.query_service_mapping(provider, service_name)
        
        # Property: Results should be relevant to the query
        assert len(results) > 0, "Query should return at least one result"
        
        # Check that results contain relevant information
        for result in results:
            # Result should have content
            assert result.content, "Result should have content"
            
            # Result should have a relevance score
            assert 0.0 <= result.score <= 1.0, "Score should be between 0 and 1"
            
            # Content should mention either the provider or service
            content_lower = result.content.lower()
            provider_lower = provider.lower()
            service_lower = service_name.lower()
            
            # At least one of these should be true for relevance
            is_relevant = (
                provider_lower in content_lower or
                service_lower in content_lower or
                'aws' in content_lower or
                'ec2' in content_lower or
                's3' in content_lower or
                'rds' in content_lower
            )
            
            assert is_relevant, f"Result content should be relevant to query: {provider} {service_name}"
    
    @given(
        aws_service=aws_services,
        region=aws_regions
    )
    @hypothesis_settings(
        max_examples=20,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_pricing_query_returns_relevant_results(
        self,
        mock_kb_service,
        aws_service,
        region
    ):
        """
        Property 15: Knowledge Base query relevance (pricing information)
        
        For any query to the Knowledge Base for pricing information,
        the results should contain relevant pricing data for the queried service.
        
        **Validates: Requirements 4.2, 4.3**
        """
        # Mock response with relevant pricing results
        mock_results = [
            {
                'score': 0.90,
                'content': {
                    'text': f'AWS {aws_service} pricing in {region}: $0.10 per hour'
                },
                'metadata': {
                    'service': aws_service,
                    'region': region,
                    'category': 'pricing'
                },
                'location': {
                    's3Location': {
                        'uri': 's3://bucket/pricing_data/compute_pricing.json'
                    }
                }
            }
        ]
        
        mock_kb_service.client.retrieve.return_value = {
            'retrievalResults': mock_results
        }
        
        # Query for pricing information
        results = mock_kb_service.query_pricing_info(aws_service, region=region)
        
        # Property: Results should be relevant to the pricing query
        assert len(results) > 0, "Pricing query should return at least one result"
        
        for result in results:
            # Result should have content
            assert result.content, "Result should have content"
            
            # Result should have a high relevance score for pricing queries
            assert result.score >= 0.5, "Pricing results should have score >= 0.5"
            
            # Content should mention the service or pricing
            content_lower = result.content.lower()
            service_lower = aws_service.lower()
            
            # Check for pricing-related keywords
            has_pricing_info = (
                service_lower in content_lower or
                'pricing' in content_lower or
                'price' in content_lower or
                'cost' in content_lower or
                '$' in content_lower or
                'hour' in content_lower or
                'month' in content_lower
            )
            
            assert has_pricing_info, f"Result should contain pricing information for {aws_service}"
    
    @given(
        aws_service=aws_services
    )
    @hypothesis_settings(
        max_examples=15,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_service_description_query_returns_relevant_results(
        self,
        mock_kb_service,
        aws_service
    ):
        """
        Property 15: Knowledge Base query relevance (service descriptions)
        
        For any query to the Knowledge Base for service descriptions,
        the results should contain relevant information about the service.
        
        **Validates: Requirements 4.2, 4.3**
        """
        # Mock response with service description
        mock_results = [
            {
                'score': 0.88,
                'content': {
                    'text': f'AWS {aws_service} is a managed service that provides scalable computing capacity'
                },
                'metadata': {
                    'service': aws_service,
                    'category': 'service_description'
                },
                'location': {
                    's3Location': {
                        'uri': 's3://bucket/aws_services/compute_services.json'
                    }
                }
            }
        ]
        
        mock_kb_service.client.retrieve.return_value = {
            'retrievalResults': mock_results
        }
        
        # Query for service description
        results = mock_kb_service.query_service_description(aws_service)
        
        # Property: Results should describe the service
        assert len(results) > 0, "Service description query should return results"
        
        for result in results:
            # Result should have content
            assert result.content, "Result should have content"
            
            # Content should mention the service
            content_lower = result.content.lower()
            service_lower = aws_service.lower()
            
            # Check for service-related information
            has_service_info = (
                service_lower in content_lower or
                'service' in content_lower or
                'aws' in content_lower or
                'amazon' in content_lower
            )
            
            assert has_service_info, f"Result should contain information about {aws_service}"
    
    @given(
        query_text=st.text(min_size=5, max_size=100)
    )
    @hypothesis_settings(
        max_examples=10,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_query_results_have_valid_structure(
        self,
        mock_kb_service,
        query_text
    ):
        """
        Property: All query results should have valid structure.
        
        For any query text, all returned results should have:
        - Non-empty content
        - Valid score (0.0 to 1.0)
        - Metadata dictionary
        """
        # Filter out queries that are just whitespace or special characters
        assume(query_text.strip())
        assume(any(c.isalnum() for c in query_text))
        
        # Mock response
        mock_results = [
            {
                'score': 0.75,
                'content': {
                    'text': 'Sample result content'
                },
                'metadata': {
                    'key': 'value'
                },
                'location': {
                    's3Location': {
                        'uri': 's3://bucket/file.json'
                    }
                }
            }
        ]
        
        mock_kb_service.client.retrieve.return_value = {
            'retrievalResults': mock_results
        }
        
        # Query Knowledge Base
        results = mock_kb_service.query(query_text, max_results=5)
        
        # Property: All results should have valid structure
        for result in results:
            # Check content
            assert isinstance(result.content, str), "Content should be a string"
            assert result.content, "Content should not be empty"
            
            # Check score
            assert isinstance(result.score, (int, float)), "Score should be numeric"
            assert 0.0 <= result.score <= 1.0, "Score should be between 0 and 1"
            
            # Check metadata
            assert isinstance(result.metadata, dict), "Metadata should be a dictionary"
            
            # Check source location (optional)
            if result.source_location:
                assert isinstance(result.source_location, str), "Source location should be a string"
    
    def test_query_with_min_score_filters_results(self, mock_kb_service):
        """
        Property: Query with min_score should filter out low-scoring results.
        
        For any min_score threshold, all returned results should have
        score >= min_score.
        """
        # Mock response with varying scores
        mock_results = [
            {
                'score': 0.9,
                'content': {'text': 'High relevance result'},
                'metadata': {}
            },
            {
                'score': 0.7,
                'content': {'text': 'Medium relevance result'},
                'metadata': {}
            },
            {
                'score': 0.4,
                'content': {'text': 'Low relevance result'},
                'metadata': {}
            }
        ]
        
        mock_kb_service.client.retrieve.return_value = {
            'retrievalResults': mock_results
        }
        
        # Query with min_score threshold
        min_score = 0.6
        results = mock_kb_service.query("test query", min_score=min_score)
        
        # Property: All results should meet minimum score
        assert len(results) == 2, "Should filter out low-scoring results"
        
        for result in results:
            assert result.score >= min_score, f"Result score {result.score} should be >= {min_score}"


# Integration test (requires actual Knowledge Base)
@pytest.mark.integration
class TestKnowledgeBaseIntegration:
    """Integration tests for Knowledge Base (requires AWS setup)."""
    
    def test_knowledge_base_connection(self):
        """Test that Knowledge Base is accessible."""
        if not os.getenv('BEDROCK_KNOWLEDGE_BASE_ID'):
            pytest.skip("Knowledge Base ID not configured")
        
        service = KnowledgeBaseService()
        assert service.test_connection(), "Should be able to connect to Knowledge Base"
    
    def test_query_returns_results(self):
        """Test that queries return actual results."""
        if not os.getenv('BEDROCK_KNOWLEDGE_BASE_ID'):
            pytest.skip("Knowledge Base ID not configured")
        
        service = KnowledgeBaseService()
        results = service.query("AWS EC2 pricing", max_results=3)
        
        assert len(results) > 0, "Should return results for EC2 pricing query"
        assert all(r.score > 0 for r in results), "All results should have positive scores"
