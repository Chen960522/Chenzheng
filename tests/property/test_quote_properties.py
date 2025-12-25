"""Property-based tests for Quote Generator."""

import pytest
from hypothesis import given, strategies as st, settings
from decimal import Decimal
from datetime import datetime

from src.models.quote import Quote, AWSServiceMapping
from src.models.service_config import ServiceConfig
from src.models.pricing_result import PricingResult
from src.services.quote_generator import QuoteGenerator


# Strategies for generating test data
@st.composite
def service_config_strategy(draw):
    """Generate random ServiceConfig."""
    provider = draw(st.sampled_from(['alibaba', 'huawei', 'tencent', 'gcp', 'azure']))
    service_type = draw(st.sampled_from(['compute', 'storage', 'database', 'network']))
    service_name = draw(st.text(min_size=3, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll'))))
    
    specs = draw(st.dictionaries(
        keys=st.sampled_from(['cpu', 'memory', 'storage', 'bandwidth']),
        values=st.integers(min_value=1, max_value=1000),
        min_size=1,
        max_size=4
    ))
    
    return ServiceConfig(
        provider=provider,
        service_type=service_type,
        service_name=service_name,
        specifications=specs,
        quantity=draw(st.integers(min_value=1, max_value=10))
    )


@st.composite
def aws_mapping_strategy(draw):
    """Generate random AWSServiceMapping."""
    aws_service = draw(st.sampled_from(['EC2', 'S3', 'RDS', 'Lambda', 'DynamoDB']))
    category = draw(st.sampled_from(['compute', 'storage', 'database', 'serverless']))
    service_type = draw(st.text(min_size=5, max_size=20))
    
    specs = draw(st.dictionaries(
        keys=st.sampled_from(['instance_type', 'storage_class', 'engine']),
        values=st.text(min_size=3, max_size=15),
        min_size=1,
        max_size=3
    ))
    
    return AWSServiceMapping(
        aws_service=aws_service,
        aws_service_category=category,
        aws_service_type=service_type,
        specifications=specs,
        confidence_score=draw(st.floats(min_value=0.5, max_value=1.0)),
        explanation=draw(st.text(min_size=10, max_size=100)),
        alternatives=draw(st.lists(st.text(min_size=3, max_size=15), max_size=3))
    )


@st.composite
def pricing_result_strategy(draw):
    """Generate random PricingResult."""
    monthly_cost = draw(st.decimals(min_value=Decimal('1.0'), max_value=Decimal('10000.0'), places=2))
    
    return PricingResult(
        monthly_cost=monthly_cost,
        annual_cost=monthly_cost * 12,
        pricing_model=draw(st.sampled_from(['on-demand', 'reserved', 'savings-plan'])),
        region=draw(st.sampled_from(['us-east-1', 'us-west-2', 'eu-west-1', 'ap-southeast-1'])),
        breakdown={
            'compute': monthly_cost * Decimal('0.6'),
            'storage': monthly_cost * Decimal('0.3'),
            'data_transfer': monthly_cost * Decimal('0.1')
        }
    )


@pytest.mark.property_test
@given(
    user_id=st.text(min_size=10, max_size=50),
    original_input=st.text(min_size=20, max_size=500),
    services=st.lists(service_config_strategy(), min_size=1, max_size=5),
    mappings=st.lists(aws_mapping_strategy(), min_size=1, max_size=5),
    pricing=st.lists(pricing_result_strategy(), min_size=1, max_size=5),
    language=st.sampled_from(['en', 'zh'])
)
@settings(max_examples=100, deadline=None)
def test_complete_quote_content(user_id, original_input, services, mappings, pricing, language):
    """
    Feature: aws-pricing-assistant, Property 26: Complete quote content
    
    For any generated quote, it should include original service specifications,
    mapped AWS services, itemized pricing breakdown, total costs, service
    descriptions, and disclaimers.
    
    Validates: Requirements 6.2, 6.3, 6.4, 6.5, 6.8
    """
    # Ensure lists have same length for valid quote
    min_len = min(len(services), len(mappings), len(pricing))
    services = services[:min_len]
    mappings = mappings[:min_len]
    pricing = pricing[:min_len]
    
    # Generate quote
    generator = QuoteGenerator()
    quote = generator.generate_quote(
        user_id=user_id,
        original_input=original_input,
        parsed_services=services,
        aws_mappings=mappings,
        pricing_results=pricing,
        language=language
    )
    
    # Verify quote contains all required information
    
    # 1. Original service specifications (Requirement 6.2)
    assert quote.original_input == original_input
    assert len(quote.parsed_services) == len(services)
    for i, service in enumerate(services):
        parsed = quote.parsed_services[i]
        assert parsed['provider'] == service.provider
        assert parsed['service_name'] == service.service_name
        assert parsed['service_type'] == service.service_type
        assert parsed['specifications'] == service.specifications
    
    # 2. Mapped AWS services (Requirement 6.2)
    assert len(quote.aws_mappings) == len(mappings)
    for i, mapping in enumerate(mappings):
        aws_map = quote.aws_mappings[i]
        assert aws_map['aws_service'] == mapping.aws_service
        assert aws_map['aws_service_category'] == mapping.aws_service_category
        assert aws_map['explanation'] == mapping.explanation
    
    # 3. Itemized pricing breakdown (Requirement 6.3)
    assert len(quote.pricing_results) == len(pricing)
    for i, price in enumerate(pricing):
        pricing_result = quote.pricing_results[i]
        assert pricing_result['monthly_cost'] == float(price.monthly_cost)
        assert pricing_result['annual_cost'] == float(price.annual_cost)
        assert pricing_result['pricing_model'] == price.pricing_model
        assert pricing_result['region'] == price.region
        assert 'breakdown' in pricing_result
    
    # 4. Total costs (Requirement 6.4)
    expected_monthly = sum(p.monthly_cost for p in pricing)
    expected_annual = sum(p.annual_cost for p in pricing)
    assert quote.total_monthly_cost == expected_monthly
    assert quote.total_annual_cost == expected_annual
    
    # 5. Get quote content and verify completeness
    content = generator.get_quote_content(quote)
    
    # Verify service descriptions are included (Requirement 6.5)
    assert 'descriptions' in content
    assert 'title' in content['descriptions']
    assert 'services' in content['descriptions']
    
    # Verify disclaimers are included (Requirement 6.8)
    assert 'disclaimers' in content
    assert 'title' in content['disclaimers']
    assert 'items' in content['disclaimers']
    assert len(content['disclaimers']['items']) > 0
    
    # Verify all major sections are present
    assert 'header' in content
    assert 'original_services' in content
    assert 'aws_mappings' in content
    assert 'pricing' in content
    assert 'benefits' in content
    
    # Verify header information
    assert content['header']['quote_id'] == quote.quote_id
    assert content['header']['language'] == language
    
    # Verify pricing totals in content
    assert content['pricing']['total_monthly']['value'] == float(quote.total_monthly_cost)
    assert content['pricing']['total_annual']['value'] == float(quote.total_annual_cost)


@pytest.mark.property_test
@given(
    user_id=st.text(min_size=10, max_size=50),
    original_input=st.text(min_size=20, max_size=500),
    services=st.lists(service_config_strategy(), min_size=1, max_size=3),
    mappings=st.lists(aws_mapping_strategy(), min_size=1, max_size=3),
    pricing=st.lists(pricing_result_strategy(), min_size=1, max_size=3),
    language=st.sampled_from(['en', 'zh'])
)
@settings(max_examples=100, deadline=None)
def test_quote_validation(user_id, original_input, services, mappings, pricing, language):
    """
    Test that quote validation correctly identifies complete quotes.
    
    For any generated quote with all required fields, validation should pass.
    """
    # Ensure lists have same length
    min_len = min(len(services), len(mappings), len(pricing))
    services = services[:min_len]
    mappings = mappings[:min_len]
    pricing = pricing[:min_len]
    
    # Generate quote
    generator = QuoteGenerator()
    quote = generator.generate_quote(
        user_id=user_id,
        original_input=original_input,
        parsed_services=services,
        aws_mappings=mappings,
        pricing_results=pricing,
        language=language
    )
    
    # Validate quote completeness
    is_valid, missing = generator.validate_quote_completeness(quote)
    
    # Quote should be valid
    assert is_valid, f"Quote validation failed. Missing: {missing}"
    assert len(missing) == 0


@pytest.mark.property_test
@given(
    user_id=st.text(min_size=10, max_size=50),
    original_input=st.text(min_size=20, max_size=500),
    services=st.lists(service_config_strategy(), min_size=1, max_size=3),
    mappings=st.lists(aws_mapping_strategy(), min_size=1, max_size=3),
    pricing=st.lists(pricing_result_strategy(), min_size=1, max_size=3),
    language=st.sampled_from(['en', 'zh'])
)
@settings(max_examples=100, deadline=None)
def test_quote_text_formatting(user_id, original_input, services, mappings, pricing, language):
    """
    Test that quote text formatting includes all required sections.
    
    For any generated quote, the formatted text should contain all major sections.
    """
    # Ensure lists have same length
    min_len = min(len(services), len(mappings), len(pricing))
    services = services[:min_len]
    mappings = mappings[:min_len]
    pricing = pricing[:min_len]
    
    # Generate quote
    generator = QuoteGenerator()
    quote = generator.generate_quote(
        user_id=user_id,
        original_input=original_input,
        parsed_services=services,
        aws_mappings=mappings,
        pricing_results=pricing,
        language=language
    )
    
    # Format as text
    text = generator.format_quote_text(quote)
    
    # Verify text contains key information
    assert quote.quote_id in text
    assert str(quote.total_monthly_cost) in text or f"{float(quote.total_monthly_cost):.2f}" in text
    
    # Verify text is not empty
    assert len(text) > 100
    
    # Verify text contains section separators
    assert '=' in text or '-' in text


@pytest.mark.property_test
@given(
    user_id=st.text(min_size=10, max_size=50),
    original_input=st.text(min_size=20, max_size=500),
    services=st.lists(service_config_strategy(), min_size=1, max_size=3),
    mappings=st.lists(aws_mapping_strategy(), min_size=1, max_size=3),
    pricing=st.lists(pricing_result_strategy(), min_size=1, max_size=3)
)
@settings(max_examples=100, deadline=None)
def test_quote_language_support(user_id, original_input, services, mappings, pricing):
    """
    Test that quotes support both English and Chinese output.
    
    For any quote, both English and Chinese versions should be generated correctly.
    """
    # Ensure lists have same length
    min_len = min(len(services), len(mappings), len(pricing))
    services = services[:min_len]
    mappings = mappings[:min_len]
    pricing = pricing[:min_len]
    
    generator = QuoteGenerator()
    
    # Generate English quote
    quote_en = generator.generate_quote(
        user_id=user_id,
        original_input=original_input,
        parsed_services=services,
        aws_mappings=mappings,
        pricing_results=pricing,
        language='en'
    )
    
    # Generate Chinese quote
    quote_zh = generator.generate_quote(
        user_id=user_id,
        original_input=original_input,
        parsed_services=services,
        aws_mappings=mappings,
        pricing_results=pricing,
        language='zh'
    )
    
    # Both should have same data, different language
    assert quote_en.language == 'en'
    assert quote_zh.language == 'zh'
    
    # Get content for both
    content_en = generator.get_quote_content(quote_en)
    content_zh = generator.get_quote_content(quote_zh)
    
    # Titles should be different (translated)
    assert content_en['header']['title'] != content_zh['header']['title']
    
    # But data should be the same
    assert len(content_en['original_services']['services']) == len(content_zh['original_services']['services'])
    assert len(content_en['aws_mappings']['mappings']) == len(content_zh['aws_mappings']['mappings'])
    assert content_en['pricing']['total_monthly']['value'] == content_zh['pricing']['total_monthly']['value']
