"""Property-based tests for web crawler functionality."""

import pytest
from hypothesis import given, strategies as st, settings
from unittest.mock import Mock, patch

from src.services.crawlers.web_crawler import WebCrawler
from src.services.crawlers.alibaba_crawler import AlibabaCloudCrawler
from src.services.crawlers.huawei_crawler import HuaweiCloudCrawler
from src.services.crawlers.tencent_crawler import TencentCloudCrawler
from src.services.crawlers.gcp_crawler import GCPCrawler
from src.services.crawlers.azure_crawler import AzureCrawler


# Feature: aws-pricing-assistant, Property 48: Multi-provider crawling
# For any scheduled crawling task, the Web Crawler should successfully fetch
# service information from all supported cloud providers
@given(
    providers=st.lists(
        st.sampled_from(['alibaba', 'huawei', 'tencent', 'gcp', 'azure']),
        min_size=1,
        max_size=5,
        unique=True
    )
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_multi_provider_crawling(providers):
    """
    Feature: aws-pricing-assistant, Property 48: Multi-provider crawling
    
    For any scheduled crawling task, the Web Crawler should successfully fetch
    service information from all supported cloud providers (Alibaba, Huawei,
    Tencent, GCP, Azure).
    
    Validates: Requirements 14.1
    """
    # Create mock database service
    mock_db = Mock()
    mock_db.get_cloud_service.return_value = None  # No existing services
    mock_db.create_cloud_service.return_value = None
    
    # Create crawler with mocked database
    crawler = WebCrawler(db_service=mock_db)
    
    # Verify crawler has all required providers
    for provider in providers:
        assert provider in crawler.crawlers, f"Crawler missing provider: {provider}"
        assert crawler.crawlers[provider] is not None
    
    # Verify each provider crawler can extract services
    for provider in providers:
        provider_crawler = crawler.crawlers[provider]
        
        # Each crawler should have the required methods
        assert hasattr(provider_crawler, 'extract_services')
        assert hasattr(provider_crawler, 'get_provider_name')
        assert hasattr(provider_crawler, 'get_service_list_url')
        
        # Provider name should match
        assert provider_crawler.get_provider_name() == provider
        
        # Service list URL should be valid
        url = provider_crawler.get_service_list_url()
        assert url.startswith('http://') or url.startswith('https://')


# Feature: aws-pricing-assistant, Property 49: Service information extraction
# For any crawled service page, the Web Crawler should extract service names,
# specifications, features, and pricing information when available
@given(
    service_name=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
    service_category=st.sampled_from(['compute', 'storage', 'database', 'network', 'analytics', 'ml']),
    has_specs=st.booleans(),
    has_features=st.booleans(),
    has_pricing=st.booleans()
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_service_information_extraction(service_name, service_category, has_specs, has_features, has_pricing):
    """
    Feature: aws-pricing-assistant, Property 49: Service information extraction
    
    For any crawled service page, the Web Crawler should extract service names,
    specifications, features, and pricing information when available.
    
    Validates: Requirements 14.2
    """
    # Create a test crawler (using Alibaba as example)
    crawler = AlibabaCloudCrawler()
    
    # Create test service data
    specifications = {'cpu': '4', 'memory': '8GB'} if has_specs else {}
    features = ['Feature 1', 'Feature 2'] if has_features else []
    pricing_info = {'monthly': '100'} if has_pricing else None
    
    # Use the create_service_dict method to create standardized service data
    service_dict = crawler.create_service_dict(
        service_name=service_name,
        service_name_en=service_name,
        service_category=service_category,
        description=f"Test service {service_name}",
        source_url="https://example.com/service",
        specifications=specifications,
        features=features,
        pricing_info=pricing_info
    )
    
    # Verify all required fields are present
    assert 'service_name' in service_dict
    assert 'service_name_en' in service_dict
    assert 'service_category' in service_dict
    assert 'description' in service_dict
    assert 'specifications' in service_dict
    assert 'features' in service_dict
    assert 'source_url' in service_dict
    assert 'crawled_at' in service_dict
    assert 'data_quality_score' in service_dict
    
    # Verify extracted data matches input
    assert service_dict['service_name'] == service_name
    assert service_dict['service_name_en'] == service_name
    
    # Verify specifications are extracted when present
    if has_specs:
        assert len(service_dict['specifications']) > 0
        assert service_dict['specifications'] == specifications
    
    # Verify features are extracted when present
    if has_features:
        assert len(service_dict['features']) > 0
        assert service_dict['features'] == features
    
    # Verify pricing info is extracted when present
    if has_pricing:
        assert service_dict['pricing_info'] is not None
        assert service_dict['pricing_info'] == pricing_info
    
    # Verify data quality score is calculated
    assert 0.0 <= service_dict['data_quality_score'] <= 1.0
    
    # Services with more information should have higher quality scores
    if has_specs and has_features and has_pricing:
        assert service_dict['data_quality_score'] >= 0.6


# Property: Data quality scoring consistency
@given(
    has_description=st.booleans(),
    has_specs=st.booleans(),
    has_features=st.booleans(),
    has_pricing=st.booleans(),
    has_bilingual=st.booleans()
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_data_quality_scoring_consistency(has_description, has_specs, has_features, has_pricing, has_bilingual):
    """
    For any service data, the quality score should be consistent and deterministic
    based on the presence of key information fields.
    """
    crawler = AlibabaCloudCrawler()
    
    # Create service data with varying completeness
    service_data = {
        'description': 'Test description' if has_description else '',
        'specifications': {'cpu': '4'} if has_specs else {},
        'features': ['Feature 1'] if has_features else [],
        'pricing_info': {'price': '100'} if has_pricing else None,
        'service_name_en': 'Test Service',
        'service_name_zh': '测试服务' if has_bilingual else None
    }
    
    # Calculate quality score
    score = crawler.calculate_data_quality_score(service_data)
    
    # Score should be between 0 and 1
    assert 0.0 <= score <= 1.0
    
    # Score should be deterministic - calculate again and verify
    score2 = crawler.calculate_data_quality_score(service_data)
    assert score == score2
    
    # Calculate expected score based on criteria
    expected_score = 0.0
    if has_description and len(service_data['description']) > 10:
        expected_score += 0.2
    if has_specs and len(service_data['specifications']) > 0:
        expected_score += 0.2
    if has_features and len(service_data['features']) > 0:
        expected_score += 0.2
    if has_pricing:
        expected_score += 0.2
    if has_bilingual:
        expected_score += 0.2
    
    assert score == round(expected_score, 2)


# Property: Service category normalization
@given(
    raw_category=st.sampled_from([
        'compute', 'computing', 'virtual machine', 'vm',
        'storage', 'object storage', 'block storage',
        'database', 'db', 'rds', 'nosql',
        'network', 'networking', 'cdn', 'load balancer',
        'analytics', 'big data', 'data warehouse',
        'machine learning', 'ml', 'ai',
        'container', 'kubernetes', 'docker',
        'serverless', 'function', 'lambda',
        'unknown category'
    ])
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_service_category_normalization(raw_category):
    """
    For any service category string, the crawler should normalize it to
    a standard category or 'other' if unknown.
    """
    crawler = AlibabaCloudCrawler()
    
    normalized = crawler.normalize_service_category(raw_category)
    
    # Normalized category should be one of the standard categories
    standard_categories = [
        'compute', 'storage', 'database', 'network', 'analytics', 'ml',
        'container', 'serverless', 'messaging', 'monitoring', 'security',
        'cdn', 'iot', 'blockchain', 'developer-tools', 'management',
        'integration', 'business', 'media', 'gaming', 'other'
    ]
    
    assert normalized in standard_categories
    
    # Normalization should be consistent
    normalized2 = crawler.normalize_service_category(raw_category)
    assert normalized == normalized2
    
    # Known categories should map correctly
    if raw_category in ['compute', 'computing', 'virtual machine', 'vm']:
        assert normalized == 'compute'
    elif raw_category in ['storage', 'object storage', 'block storage']:
        assert normalized == 'storage'
    elif raw_category in ['database', 'db', 'rds', 'nosql']:
        assert normalized == 'database'
