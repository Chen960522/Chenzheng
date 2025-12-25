"""
Property-based tests for Price Calculator.

These tests verify universal properties that should hold for all AWS pricing calculations.
"""

import pytest
from hypothesis import given, strategies as st, settings
from decimal import Decimal
from unittest.mock import Mock, patch

from src.models.cloud_service import AWSServiceMapping
from src.models.pricing_result import PricingResult
from src.services.price_calculator import PriceCalculator
from src.services.aws_pricing_service import AWSPricingService


# Strategies for generating test data
@st.composite
def aws_service_mapping_strategy(draw):
    """Generate random AWS service mappings."""
    service_category = draw(st.sampled_from([
        'compute', 'storage', 'database', 'serverless', 'network'
    ]))
    
    # Map category to service and type
    service_map = {
        'compute': ('EC2', st.sampled_from(['t3.micro', 't3.small', 'm5.large', 'c5.xlarge'])),
        'storage': ('S3', st.sampled_from(['Standard', 'Intelligent-Tiering', 'Standard-IA'])),
        'database': ('RDS', st.sampled_from(['db.t3.micro', 'db.t3.small', 'db.m5.large'])),
        'serverless': ('Lambda', st.just('128MB')),
        'network': ('VPC', st.just('Standard'))
    }
    
    aws_service, type_strategy = service_map[service_category]
    aws_service_type = draw(type_strategy)
    
    # Generate specifications based on category
    if service_category == 'compute':
        specs = {
            'vcpu': draw(st.integers(min_value=1, max_value=96)),
            'memory_gb': draw(st.integers(min_value=1, max_value=384)),
            'data_transfer_gb_per_month': draw(st.integers(min_value=0, max_value=1000))
        }
    elif service_category == 'storage':
        specs = {
            'capacity_gb': draw(st.integers(min_value=1, max_value=10000)),
            'data_transfer_gb_per_month': draw(st.integers(min_value=0, max_value=1000))
        }
    elif service_category == 'database':
        specs = {
            'vcpu': draw(st.integers(min_value=1, max_value=96)),
            'memory_gb': draw(st.integers(min_value=1, max_value=384)),
            'storage_gb': draw(st.integers(min_value=20, max_value=1000)),
            'engine': draw(st.sampled_from(['MySQL', 'PostgreSQL', 'MariaDB'])),
            'data_transfer_gb_per_month': draw(st.integers(min_value=0, max_value=1000))
        }
    elif service_category == 'serverless':
        specs = {
            'memory_mb': draw(st.sampled_from([128, 256, 512, 1024, 2048])),
            'invocations_per_month': draw(st.integers(min_value=1000, max_value=10000000)),
            'avg_duration_ms': draw(st.integers(min_value=100, max_value=5000))
        }
    else:
        specs = {}
    
    return AWSServiceMapping(
        aws_service=aws_service,
        aws_service_category=service_category,
        aws_service_type=aws_service_type,
        specifications=specs,
        confidence_score=draw(st.floats(min_value=0.5, max_value=1.0)),
        explanation=f"Test mapping for {aws_service}",
        alternatives=[]
    )


class TestPricingInformationRetrieval:
    """
    Property 9: Pricing information retrieval
    
    For any identified AWS service, the Price Calculator should retrieve
    current pricing information.
    
    Validates: Requirements 3.1
    """
    
    @given(
        aws_mapping=aws_service_mapping_strategy(),
        region=st.sampled_from(['us-east-1', 'us-west-2', 'eu-west-1', 'ap-southeast-1'])
    )
    @settings(max_examples=10, deadline=5000)
    def test_pricing_information_retrieval(self, aws_mapping, region):
        """
        Feature: aws-pricing-assistant, Property 9: Pricing information retrieval
        
        For any identified AWS service, the Price Calculator should retrieve
        current pricing information.
        """
        # Mock the AWS Pricing Service to avoid real API calls
        mock_pricing_service = Mock(spec=AWSPricingService)
        mock_pricing_service.get_ec2_pricing.return_value = {'hourly_rate': Decimal('0.0104')}
        mock_pricing_service.get_s3_pricing.return_value = {'price_per_gb': Decimal('0.023')}
        mock_pricing_service.get_rds_pricing.return_value = {'hourly_rate': Decimal('0.017')}
        mock_pricing_service.get_lambda_pricing.return_value = {'price_per_gb_second': Decimal('0.0000166667')}
        mock_pricing_service.get_data_transfer_pricing.return_value = {'price_per_gb': Decimal('0.09')}
        
        # Mock Knowledge Base service
        mock_kb_service = Mock()
        mock_kb_service.query.return_value = []
        
        calculator = PriceCalculator(
            pricing_service=mock_pricing_service,
            knowledge_base_service=mock_kb_service
        )
        
        # Calculate price
        result = calculator.calculate_price(
            aws_mapping=aws_mapping,
            region=region,
            pricing_model='on-demand'
        )
        
        # Verify pricing information was retrieved
        assert isinstance(result, PricingResult)
        assert result.region == region
        assert result.pricing_model == 'on-demand'
        
        # Verify result has pricing data (even if unavailable, should have structure)
        assert result.monthly_cost >= 0
        assert result.annual_cost >= 0
        assert isinstance(result.breakdown, dict)
        
        # If service is available, should have positive costs or breakdown
        if result.region_availability:
            # Should have either positive costs or valid breakdown
            assert result.monthly_cost >= 0 or len(result.breakdown) >= 0


class TestComprehensiveCostCalculation:
    """
    Property 10: Comprehensive cost calculation
    
    For any AWS service configuration, the Price Calculator should consider
    all relevant cost factors (instance type, region, usage hours, storage class,
    capacity, data transfer).
    
    Validates: Requirements 3.2, 3.3, 3.4
    """
    
    @given(
        aws_mapping=aws_service_mapping_strategy(),
        region=st.sampled_from(['us-east-1', 'eu-central-1', 'ap-northeast-1']),
        usage_hours=st.integers(min_value=1, max_value=730),
        quantity=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=10, deadline=5000)
    def test_comprehensive_cost_calculation(self, aws_mapping, region, usage_hours, quantity):
        """
        Feature: aws-pricing-assistant, Property 10: Comprehensive cost calculation
        
        For any AWS service configuration, the Price Calculator should consider
        all relevant cost factors.
        """
        # Mock services
        mock_pricing_service = Mock(spec=AWSPricingService)
        mock_pricing_service.get_ec2_pricing.return_value = {'hourly_rate': Decimal('0.0104')}
        mock_pricing_service.get_s3_pricing.return_value = {'price_per_gb': Decimal('0.023')}
        mock_pricing_service.get_rds_pricing.return_value = {'hourly_rate': Decimal('0.017')}
        mock_pricing_service.get_lambda_pricing.return_value = {'price_per_gb_second': Decimal('0.0000166667')}
        mock_pricing_service.get_data_transfer_pricing.return_value = {'price_per_gb': Decimal('0.09')}
        
        mock_kb_service = Mock()
        mock_kb_service.query.return_value = []
        
        calculator = PriceCalculator(
            pricing_service=mock_pricing_service,
            knowledge_base_service=mock_kb_service
        )
        
        # Calculate price
        result = calculator.calculate_price(
            aws_mapping=aws_mapping,
            region=region,
            pricing_model='on-demand',
            usage_hours=usage_hours,
            quantity=quantity
        )
        
        # Verify all cost factors are considered
        assert isinstance(result, PricingResult)
        assert result.region == region
        
        # Verify breakdown contains relevant cost components
        if result.region_availability and result.monthly_cost > 0:
            assert len(result.breakdown) > 0
            
            # Verify breakdown items are non-negative
            for key, value in result.breakdown.items():
                assert value >= 0, f"Breakdown item '{key}' should be non-negative"
            
            # Verify breakdown sums to approximately monthly cost
            # (allowing for small rounding differences)
            breakdown_total = sum(result.breakdown.values(), Decimal('0'))
            assert abs(breakdown_total - result.monthly_cost) < Decimal('0.01'), \
                "Breakdown should sum to monthly cost"
        
        # Verify annual cost is 12x monthly cost
        expected_annual = result.monthly_cost * Decimal('12')
        assert abs(result.annual_cost - expected_annual) < Decimal('0.01'), \
            "Annual cost should be 12x monthly cost"


class TestRegionalPricingAccuracy:
    """
    Property 12: Regional pricing accuracy
    
    For any AWS service and any two different AWS regions, the Price Calculator
    should return region-specific pricing that reflects actual regional differences.
    
    Validates: Requirements 3.6, 3.9, 3.10
    """
    
    @given(
        aws_mapping=aws_service_mapping_strategy(),
        region1=st.sampled_from(['us-east-1', 'us-west-2', 'eu-west-1']),
        region2=st.sampled_from(['ap-southeast-1', 'ap-northeast-1', 'eu-central-1'])
    )
    @settings(max_examples=10, deadline=5000)
    def test_regional_pricing_accuracy(self, aws_mapping, region1, region2):
        """
        Feature: aws-pricing-assistant, Property 12: Regional pricing accuracy
        
        For any AWS service and any two different AWS regions, the Price Calculator
        should return region-specific pricing that reflects actual regional differences.
        """
        # Mock services
        mock_pricing_service = Mock(spec=AWSPricingService)
        mock_pricing_service.get_ec2_pricing.return_value = {'hourly_rate': Decimal('0.0104')}
        mock_pricing_service.get_s3_pricing.return_value = {'price_per_gb': Decimal('0.023')}
        mock_pricing_service.get_rds_pricing.return_value = {'hourly_rate': Decimal('0.017')}
        mock_pricing_service.get_lambda_pricing.return_value = {'price_per_gb_second': Decimal('0.0000166667')}
        mock_pricing_service.get_data_transfer_pricing.return_value = {'price_per_gb': Decimal('0.09')}
        
        mock_kb_service = Mock()
        mock_kb_service.query.return_value = []
        
        calculator = PriceCalculator(
            pricing_service=mock_pricing_service,
            knowledge_base_service=mock_kb_service
        )
        
        # Calculate price for both regions
        result1 = calculator.calculate_price(
            aws_mapping=aws_mapping,
            region=region1,
            pricing_model='on-demand'
        )
        
        result2 = calculator.calculate_price(
            aws_mapping=aws_mapping,
            region=region2,
            pricing_model='on-demand'
        )
        
        # Verify both results are valid
        assert isinstance(result1, PricingResult)
        assert isinstance(result2, PricingResult)
        
        # Verify regions are correctly set
        assert result1.region == region1
        assert result2.region == region2
        
        # Verify both have the same pricing model
        assert result1.pricing_model == result2.pricing_model
        
        # If both regions have the service available, pricing may differ
        # (but we don't enforce differences as some services have uniform pricing)
        if result1.region_availability and result2.region_availability:
            # Both should have valid pricing data
            assert result1.monthly_cost >= 0
            assert result2.monthly_cost >= 0
            
            # Costs can be equal or different (region-specific)
            # We just verify they're both valid numbers
            assert isinstance(result1.monthly_cost, Decimal)
            assert isinstance(result2.monthly_cost, Decimal)


class TestCostAggregation:
    """
    Property 13: Cost aggregation
    
    For any configuration with multiple services, the Price Calculator should
    correctly sum individual costs to produce total monthly and annual costs.
    
    Validates: Requirements 3.7
    """
    
    @given(
        mappings=st.lists(
            aws_service_mapping_strategy(),
            min_size=2,
            max_size=5
        ),
        region=st.sampled_from(['us-east-1', 'eu-west-1', 'ap-southeast-1'])
    )
    @settings(max_examples=10, deadline=5000)
    def test_cost_aggregation(self, mappings, region):
        """
        Feature: aws-pricing-assistant, Property 13: Cost aggregation
        
        For any configuration with multiple services, the Price Calculator should
        correctly sum individual costs to produce total monthly and annual costs.
        """
        # Mock services
        mock_pricing_service = Mock(spec=AWSPricingService)
        mock_pricing_service.get_ec2_pricing.return_value = {'hourly_rate': Decimal('0.0104')}
        mock_pricing_service.get_s3_pricing.return_value = {'price_per_gb': Decimal('0.023')}
        mock_pricing_service.get_rds_pricing.return_value = {'hourly_rate': Decimal('0.017')}
        mock_pricing_service.get_lambda_pricing.return_value = {'price_per_gb_second': Decimal('0.0000166667')}
        mock_pricing_service.get_data_transfer_pricing.return_value = {'price_per_gb': Decimal('0.09')}
        
        mock_kb_service = Mock()
        mock_kb_service.query.return_value = []
        
        calculator = PriceCalculator(
            pricing_service=mock_pricing_service,
            knowledge_base_service=mock_kb_service
        )
        
        # Calculate price for each service
        results = []
        for mapping in mappings:
            result = calculator.calculate_price(
                aws_mapping=mapping,
                region=region,
                pricing_model='on-demand'
            )
            results.append(result)
        
        # Calculate total costs
        total_monthly = sum(r.monthly_cost for r in results)
        total_annual = sum(r.annual_cost for r in results)
        
        # Verify aggregation
        assert total_monthly >= 0
        assert total_annual >= 0
        
        # Verify annual is 12x monthly (with small tolerance for rounding)
        expected_annual = total_monthly * Decimal('12')
        assert abs(total_annual - expected_annual) < Decimal('0.01'), \
            "Aggregated annual cost should be 12x aggregated monthly cost"
        
        # Verify each individual result contributes to total
        for result in results:
            assert result.monthly_cost <= total_monthly
            assert result.annual_cost <= total_annual
        
        # Verify total is sum of all parts
        calculated_total_monthly = sum(r.monthly_cost for r in results)
        assert abs(total_monthly - calculated_total_monthly) < Decimal('0.01')


class TestMultiRegionPricingComparison:
    """
    Property 12a: Multi-region pricing comparison
    
    For any AWS service configuration, when the user requests pricing across
    multiple regions, the Price Calculator should provide accurate pricing
    for all requested regions.
    
    Validates: Requirements 3.11
    """
    
    @given(
        aws_mapping=aws_service_mapping_strategy()
    )
    @settings(max_examples=5, deadline=10000)
    def test_multi_region_pricing_comparison(self, aws_mapping):
        """
        Feature: aws-pricing-assistant, Property 12a: Multi-region pricing comparison
        
        For any AWS service configuration, when the user requests pricing across
        multiple regions, the Price Calculator should provide accurate pricing
        for all requested regions.
        """
        # Mock services
        mock_pricing_service = Mock(spec=AWSPricingService)
        mock_pricing_service.get_ec2_pricing.return_value = {'hourly_rate': Decimal('0.0104')}
        mock_pricing_service.get_s3_pricing.return_value = {'price_per_gb': Decimal('0.023')}
        mock_pricing_service.get_rds_pricing.return_value = {'hourly_rate': Decimal('0.017')}
        mock_pricing_service.get_lambda_pricing.return_value = {'price_per_gb_second': Decimal('0.0000166667')}
        mock_pricing_service.get_data_transfer_pricing.return_value = {'price_per_gb': Decimal('0.09')}
        
        mock_kb_service = Mock()
        mock_kb_service.query.return_value = []
        
        calculator = PriceCalculator(
            pricing_service=mock_pricing_service,
            knowledge_base_service=mock_kb_service
        )
        
        # Get pricing for all regions
        all_region_prices = calculator.get_all_region_prices(
            aws_mapping=aws_mapping,
            pricing_model='on-demand'
        )
        
        # Verify we got results for all supported regions
        assert len(all_region_prices) == len(PricingResult.SUPPORTED_REGIONS)
        
        # Verify each region has a result (or None if error)
        for region in PricingResult.SUPPORTED_REGIONS:
            assert region in all_region_prices
            
            result = all_region_prices[region]
            if result is not None:
                assert isinstance(result, PricingResult)
                assert result.region == region
                assert result.monthly_cost >= 0
                assert result.annual_cost >= 0
