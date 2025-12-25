"""
Unit tests for Price Calculator.

These tests verify specific pricing calculations for different AWS services and regions.
"""

import pytest
from decimal import Decimal
from unittest.mock import Mock

from src.models.cloud_service import AWSServiceMapping
from src.models.pricing_result import PricingResult
from src.services.price_calculator import PriceCalculator
from src.services.aws_pricing_service import AWSPricingService


class TestPriceCalculatorEC2:
    """Test EC2 pricing calculations."""
    
    def test_ec2_on_demand_pricing(self):
        """Test EC2 on-demand pricing calculation."""
        # Mock services
        mock_pricing_service = Mock(spec=AWSPricingService)
        mock_pricing_service.get_ec2_pricing.return_value = {
            'hourly_rate': Decimal('0.0104')
        }
        mock_pricing_service.get_data_transfer_pricing.return_value = {
            'price_per_gb': Decimal('0.09')
        }
        
        mock_kb_service = Mock()
        mock_kb_service.query.return_value = []
        
        calculator = PriceCalculator(
            pricing_service=mock_pricing_service,
            knowledge_base_service=mock_kb_service
        )
        
        # Create EC2 mapping
        mapping = AWSServiceMapping(
            aws_service='EC2',
            aws_service_category='compute',
            aws_service_type='t3.micro',
            specifications={'vcpu': 2, 'memory_gb': 1},
            confidence_score=0.9,
            explanation='Test mapping'
        )
        
        # Calculate price
        result = calculator.calculate_price(
            aws_mapping=mapping,
            region='us-east-1',
            pricing_model='on-demand',
            usage_hours=730,
            quantity=1
        )
        
        # Verify result
        assert isinstance(result, PricingResult)
        assert result.region == 'us-east-1'
        assert result.pricing_model == 'on-demand'
        assert result.monthly_cost > 0
        assert result.annual_cost == result.monthly_cost * 12
        assert 'compute' in result.breakdown
    
    def test_ec2_multiple_instances(self):
        """Test EC2 pricing with multiple instances."""
        mock_pricing_service = Mock(spec=AWSPricingService)
        mock_pricing_service.get_ec2_pricing.return_value = {
            'hourly_rate': Decimal('0.0104')
        }
        mock_pricing_service.get_data_transfer_pricing.return_value = {
            'price_per_gb': Decimal('0.09')
        }
        
        mock_kb_service = Mock()
        mock_kb_service.query.return_value = []
        
        calculator = PriceCalculator(
            pricing_service=mock_pricing_service,
            knowledge_base_service=mock_kb_service
        )
        
        mapping = AWSServiceMapping(
            aws_service='EC2',
            aws_service_category='compute',
            aws_service_type='t3.micro',
            specifications={'vcpu': 2, 'memory_gb': 1},
            confidence_score=0.9,
            explanation='Test mapping'
        )
        
        # Calculate for 3 instances
        result = calculator.calculate_price(
            aws_mapping=mapping,
            region='us-east-1',
            pricing_model='on-demand',
            usage_hours=730,
            quantity=3
        )
        
        # Cost should be 3x single instance
        single_result = calculator.calculate_price(
            aws_mapping=mapping,
            region='us-east-1',
            pricing_model='on-demand',
            usage_hours=730,
            quantity=1
        )
        
        assert result.monthly_cost == single_result.monthly_cost * 3


class TestPriceCalculatorS3:
    """Test S3 pricing calculations."""
    
    def test_s3_standard_pricing(self):
        """Test S3 Standard storage pricing."""
        mock_pricing_service = Mock(spec=AWSPricingService)
        mock_pricing_service.get_s3_pricing.return_value = {
            'price_per_gb': Decimal('0.023')
        }
        mock_pricing_service.get_data_transfer_pricing.return_value = {
            'price_per_gb': Decimal('0.09')
        }
        
        mock_kb_service = Mock()
        mock_kb_service.query.return_value = []
        
        calculator = PriceCalculator(
            pricing_service=mock_pricing_service,
            knowledge_base_service=mock_kb_service
        )
        
        mapping = AWSServiceMapping(
            aws_service='S3',
            aws_service_category='storage',
            aws_service_type='Standard',
            specifications={'capacity_gb': 100},
            confidence_score=0.9,
            explanation='Test mapping'
        )
        
        result = calculator.calculate_price(
            aws_mapping=mapping,
            region='us-east-1',
            pricing_model='on-demand',
            quantity=1
        )
        
        assert isinstance(result, PricingResult)
        assert result.monthly_cost > 0
        assert 'storage' in result.breakdown


class TestPriceCalculatorRDS:
    """Test RDS pricing calculations."""
    
    def test_rds_mysql_pricing(self):
        """Test RDS MySQL pricing."""
        mock_pricing_service = Mock(spec=AWSPricingService)
        mock_pricing_service.get_rds_pricing.return_value = {
            'hourly_rate': Decimal('0.017')
        }
        mock_pricing_service.get_data_transfer_pricing.return_value = {
            'price_per_gb': Decimal('0.09')
        }
        
        mock_kb_service = Mock()
        mock_kb_service.query.return_value = []
        
        calculator = PriceCalculator(
            pricing_service=mock_pricing_service,
            knowledge_base_service=mock_kb_service
        )
        
        mapping = AWSServiceMapping(
            aws_service='RDS',
            aws_service_category='database',
            aws_service_type='db.t3.micro',
            specifications={'vcpu': 2, 'memory_gb': 1, 'storage_gb': 20, 'engine': 'MySQL'},
            confidence_score=0.9,
            explanation='Test mapping'
        )
        
        result = calculator.calculate_price(
            aws_mapping=mapping,
            region='us-east-1',
            pricing_model='on-demand',
            usage_hours=730,
            quantity=1
        )
        
        assert isinstance(result, PricingResult)
        assert result.monthly_cost > 0
        assert 'instance' in result.breakdown
        assert 'storage' in result.breakdown


class TestPriceCalculatorLambda:
    """Test Lambda pricing calculations."""
    
    def test_lambda_pricing(self):
        """Test Lambda pricing calculation."""
        mock_pricing_service = Mock(spec=AWSPricingService)
        mock_pricing_service.get_lambda_pricing.return_value = {
            'price_per_gb_second': Decimal('0.0000166667')
        }
        
        mock_kb_service = Mock()
        mock_kb_service.query.return_value = []
        
        calculator = PriceCalculator(
            pricing_service=mock_pricing_service,
            knowledge_base_service=mock_kb_service
        )
        
        mapping = AWSServiceMapping(
            aws_service='Lambda',
            aws_service_category='serverless',
            aws_service_type='128MB',
            specifications={
                'memory_mb': 128,
                'invocations_per_month': 1000000,
                'avg_duration_ms': 200
            },
            confidence_score=0.9,
            explanation='Test mapping'
        )
        
        result = calculator.calculate_price(
            aws_mapping=mapping,
            region='us-east-1',
            pricing_model='on-demand',
            quantity=1
        )
        
        assert isinstance(result, PricingResult)
        assert result.monthly_cost > 0
        assert 'compute' in result.breakdown
        assert 'requests' in result.breakdown


class TestPriceCalculatorRegions:
    """Test pricing across different regions."""
    
    def test_different_regions(self):
        """Test pricing in different AWS regions."""
        mock_pricing_service = Mock(spec=AWSPricingService)
        mock_pricing_service.get_ec2_pricing.return_value = {
            'hourly_rate': Decimal('0.0104')
        }
        mock_pricing_service.get_data_transfer_pricing.return_value = {
            'price_per_gb': Decimal('0.09')
        }
        
        mock_kb_service = Mock()
        mock_kb_service.query.return_value = []
        
        calculator = PriceCalculator(
            pricing_service=mock_pricing_service,
            knowledge_base_service=mock_kb_service
        )
        
        mapping = AWSServiceMapping(
            aws_service='EC2',
            aws_service_category='compute',
            aws_service_type='t3.micro',
            specifications={'vcpu': 2, 'memory_gb': 1},
            confidence_score=0.9,
            explanation='Test mapping'
        )
        
        regions = ['us-east-1', 'eu-west-1', 'ap-southeast-1']
        
        for region in regions:
            result = calculator.calculate_price(
                aws_mapping=mapping,
                region=region,
                pricing_model='on-demand'
            )
            
            assert result.region == region
            assert result.monthly_cost >= 0
    
    def test_invalid_region(self):
        """Test that invalid region raises error."""
        mock_pricing_service = Mock(spec=AWSPricingService)
        mock_kb_service = Mock()
        
        calculator = PriceCalculator(
            pricing_service=mock_pricing_service,
            knowledge_base_service=mock_kb_service
        )
        
        mapping = AWSServiceMapping(
            aws_service='EC2',
            aws_service_category='compute',
            aws_service_type='t3.micro',
            specifications={'vcpu': 2, 'memory_gb': 1},
            confidence_score=0.9,
            explanation='Test mapping'
        )
        
        with pytest.raises(ValueError, match="Unsupported region"):
            calculator.calculate_price(
                aws_mapping=mapping,
                region='invalid-region',
                pricing_model='on-demand'
            )


class TestPriceCalculatorMultiRegion:
    """Test multi-region pricing comparison."""
    
    def test_get_all_region_prices(self):
        """Test getting prices for all regions."""
        mock_pricing_service = Mock(spec=AWSPricingService)
        mock_pricing_service.get_ec2_pricing.return_value = {
            'hourly_rate': Decimal('0.0104')
        }
        mock_pricing_service.get_data_transfer_pricing.return_value = {
            'price_per_gb': Decimal('0.09')
        }
        
        mock_kb_service = Mock()
        mock_kb_service.query.return_value = []
        
        calculator = PriceCalculator(
            pricing_service=mock_pricing_service,
            knowledge_base_service=mock_kb_service
        )
        
        mapping = AWSServiceMapping(
            aws_service='EC2',
            aws_service_category='compute',
            aws_service_type='t3.micro',
            specifications={'vcpu': 2, 'memory_gb': 1},
            confidence_score=0.9,
            explanation='Test mapping'
        )
        
        all_prices = calculator.get_all_region_prices(
            aws_mapping=mapping,
            pricing_model='on-demand'
        )
        
        # Should have results for all supported regions
        assert len(all_prices) == len(PricingResult.SUPPORTED_REGIONS)
        
        # Each result should be valid
        for region, result in all_prices.items():
            assert region in PricingResult.SUPPORTED_REGIONS
            if result is not None:
                assert isinstance(result, PricingResult)
                assert result.region == region


class TestPriceCalculatorErrorHandling:
    """Test error handling in price calculator."""
    
    def test_pricing_unavailable(self):
        """Test handling when pricing is unavailable."""
        mock_pricing_service = Mock(spec=AWSPricingService)
        mock_pricing_service.get_ec2_pricing.return_value = None
        mock_pricing_service.get_data_transfer_pricing.return_value = None
        
        mock_kb_service = Mock()
        mock_kb_service.query.return_value = []
        
        calculator = PriceCalculator(
            pricing_service=mock_pricing_service,
            knowledge_base_service=mock_kb_service
        )
        
        mapping = AWSServiceMapping(
            aws_service='EC2',
            aws_service_category='compute',
            aws_service_type='t3.micro',
            specifications={'vcpu': 2, 'memory_gb': 1},
            confidence_score=0.9,
            explanation='Test mapping'
        )
        
        result = calculator.calculate_price(
            aws_mapping=mapping,
            region='us-east-1',
            pricing_model='on-demand'
        )
        
        # Should return result with zero cost and unavailable flag
        assert result.monthly_cost == 0
        assert result.region_availability == False
    
    def test_service_not_available_in_region(self):
        """Test handling when service is not available in region."""
        mock_pricing_service = Mock(spec=AWSPricingService)
        mock_kb_service = Mock()
        
        calculator = PriceCalculator(
            pricing_service=mock_pricing_service,
            knowledge_base_service=mock_kb_service
        )
        
        # SageMaker is not available in China regions
        mapping = AWSServiceMapping(
            aws_service='SageMaker',
            aws_service_category='ml',
            aws_service_type='ml.t3.medium',
            specifications={'vcpu': 2, 'memory_gb': 4},
            confidence_score=0.9,
            explanation='Test mapping'
        )
        
        result = calculator.calculate_price(
            aws_mapping=mapping,
            region='cn-north-1',
            pricing_model='on-demand'
        )
        
        # Should indicate service not available
        assert result.region_availability == False
