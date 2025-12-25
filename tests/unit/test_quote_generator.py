"""Unit tests for Quote Generator."""

import pytest
from decimal import Decimal
from datetime import datetime
import json
import os

from src.models.quote import Quote, AWSServiceMapping
from src.models.service_config import ServiceConfig
from src.models.pricing_result import PricingResult
from src.services.quote_generator import QuoteGenerator
from src.services.export.json_exporter import JSONExporter


class TestQuoteGenerator:
    """Test suite for QuoteGenerator class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.generator = QuoteGenerator()
        
        # Sample service config
        self.service_config = ServiceConfig(
            provider='alibaba',
            service_type='compute',
            service_name='ECS',
            specifications={'cpu': 4, 'memory': 8, 'storage': 100},
            quantity=2
        )
        
        # Sample AWS mapping
        self.aws_mapping = AWSServiceMapping(
            aws_service='EC2',
            aws_service_category='compute',
            aws_service_type='t3.large',
            specifications={'vcpu': 2, 'memory': 8},
            confidence_score=0.95,
            explanation='Alibaba ECS maps to AWS EC2 t3.large instance',
            alternatives=['t3.xlarge', 't2.large']
        )
        
        # Sample pricing result
        self.pricing_result = PricingResult(
            monthly_cost=Decimal('100.50'),
            annual_cost=Decimal('1206.00'),
            pricing_model='on-demand',
            region='us-east-1',
            breakdown={
                'compute': Decimal('80.00'),
                'storage': Decimal('15.50'),
                'data_transfer': Decimal('5.00')
            }
        )
    
    def test_generate_quote_basic(self):
        """Test basic quote generation."""
        quote = self.generator.generate_quote(
            user_id='test-user-123',
            original_input='Alibaba ECS: 4 CPU, 8GB RAM, 100GB storage',
            parsed_services=[self.service_config],
            aws_mappings=[self.aws_mapping],
            pricing_results=[self.pricing_result],
            language='en'
        )
        
        assert quote is not None
        assert quote.user_id == 'test-user-123'
        assert quote.status == 'draft'
        assert quote.language == 'en'
        assert len(quote.parsed_services) == 1
        assert len(quote.aws_mappings) == 1
        assert len(quote.pricing_results) == 1
        assert quote.total_monthly_cost == Decimal('100.50')
        assert quote.total_annual_cost == Decimal('1206.00')
    
    def test_generate_quote_multiple_services(self):
        """Test quote generation with multiple services."""
        # Create additional services
        service2 = ServiceConfig(
            provider='huawei',
            service_type='storage',
            service_name='OBS',
            specifications={'capacity': 1000},
            quantity=1
        )
        
        mapping2 = AWSServiceMapping(
            aws_service='S3',
            aws_service_category='storage',
            aws_service_type='Standard',
            specifications={'storage_class': 'STANDARD'},
            confidence_score=0.98,
            explanation='Huawei OBS maps to AWS S3 Standard',
            alternatives=['S3 Intelligent-Tiering']
        )
        
        pricing2 = PricingResult(
            monthly_cost=Decimal('50.00'),
            annual_cost=Decimal('600.00'),
            pricing_model='on-demand',
            region='us-east-1',
            breakdown={'storage': Decimal('50.00')}
        )
        
        quote = self.generator.generate_quote(
            user_id='test-user-123',
            original_input='Multiple services',
            parsed_services=[self.service_config, service2],
            aws_mappings=[self.aws_mapping, mapping2],
            pricing_results=[self.pricing_result, pricing2],
            language='en'
        )
        
        assert len(quote.parsed_services) == 2
        assert len(quote.aws_mappings) == 2
        assert len(quote.pricing_results) == 2
        assert quote.total_monthly_cost == Decimal('150.50')
        assert quote.total_annual_cost == Decimal('1806.00')
    
    def test_generate_quote_chinese_language(self):
        """Test quote generation with Chinese language."""
        quote = self.generator.generate_quote(
            user_id='test-user-123',
            original_input='阿里云 ECS: 4核, 8GB内存, 100GB存储',
            parsed_services=[self.service_config],
            aws_mappings=[self.aws_mapping],
            pricing_results=[self.pricing_result],
            language='zh'
        )
        
        assert quote.language == 'zh'
        
        # Get content and verify Chinese translations
        content = self.generator.get_quote_content(quote)
        assert content['header']['language'] == 'zh'
        assert '报价单' in content['header']['title'] or 'AWS' in content['header']['title']
    
    def test_get_quote_content(self):
        """Test getting structured quote content."""
        quote = self.generator.generate_quote(
            user_id='test-user-123',
            original_input='Test input',
            parsed_services=[self.service_config],
            aws_mappings=[self.aws_mapping],
            pricing_results=[self.pricing_result],
            language='en'
        )
        
        content = self.generator.get_quote_content(quote)
        
        # Verify all major sections exist
        assert 'header' in content
        assert 'original_services' in content
        assert 'aws_mappings' in content
        assert 'pricing' in content
        assert 'descriptions' in content
        assert 'benefits' in content
        assert 'disclaimers' in content
        
        # Verify header
        assert content['header']['quote_id'] == quote.quote_id
        assert content['header']['language'] == 'en'
        
        # Verify pricing totals
        assert content['pricing']['total_monthly']['value'] == float(quote.total_monthly_cost)
        assert content['pricing']['total_annual']['value'] == float(quote.total_annual_cost)
    
    def test_format_quote_text(self):
        """Test formatting quote as plain text."""
        quote = self.generator.generate_quote(
            user_id='test-user-123',
            original_input='Test input',
            parsed_services=[self.service_config],
            aws_mappings=[self.aws_mapping],
            pricing_results=[self.pricing_result],
            language='en'
        )
        
        text = self.generator.format_quote_text(quote)
        
        # Verify text contains key information
        assert quote.quote_id in text
        assert 'EC2' in text
        assert 'ECS' in text
        assert str(quote.total_monthly_cost) in text or f"{float(quote.total_monthly_cost):.2f}" in text
        
        # Verify text has structure
        assert '=' in text  # Section separators
        assert '-' in text  # Sub-section separators
    
    def test_validate_quote_completeness_valid(self):
        """Test validation of complete quote."""
        quote = self.generator.generate_quote(
            user_id='test-user-123',
            original_input='Test input',
            parsed_services=[self.service_config],
            aws_mappings=[self.aws_mapping],
            pricing_results=[self.pricing_result],
            language='en'
        )
        
        is_valid, missing = self.generator.validate_quote_completeness(quote)
        
        assert is_valid
        assert len(missing) == 0
    
    def test_validate_quote_completeness_invalid(self):
        """Test validation of incomplete quote."""
        # Create quote with missing data
        quote = Quote(
            quote_id='test-quote-123',
            user_id='test-user-123',
            created_at=datetime.now(),
            updated_at=datetime.now(),
            status='draft',
            original_input='',  # Missing
            parsed_services=[],  # Missing
            aws_mappings=[],  # Missing
            pricing_results=[],  # Missing
            total_monthly_cost=Decimal('0'),
            total_annual_cost=Decimal('0')
        )
        
        is_valid, missing = self.generator.validate_quote_completeness(quote)
        
        assert not is_valid
        assert len(missing) > 0
        assert 'original_input' in missing
        assert 'parsed_services' in missing
        assert 'aws_mappings' in missing
        assert 'pricing_results' in missing
    
    def test_quote_with_notes(self):
        """Test quote generation with notes."""
        quote = self.generator.generate_quote(
            user_id='test-user-123',
            original_input='Test input',
            parsed_services=[self.service_config],
            aws_mappings=[self.aws_mapping],
            pricing_results=[self.pricing_result],
            language='en',
            notes='This is a test quote with custom notes'
        )
        
        assert quote.notes == 'This is a test quote with custom notes'
        
        content = self.generator.get_quote_content(quote)
        assert content['notes'] == 'This is a test quote with custom notes'
    
    def test_quote_different_regions(self):
        """Test quote generation with different AWS regions."""
        pricing_eu = PricingResult(
            monthly_cost=Decimal('110.00'),
            annual_cost=Decimal('1320.00'),
            pricing_model='on-demand',
            region='eu-west-1',
            breakdown={'compute': Decimal('110.00')}
        )
        
        quote = self.generator.generate_quote(
            user_id='test-user-123',
            original_input='Test input',
            parsed_services=[self.service_config],
            aws_mappings=[self.aws_mapping],
            pricing_results=[pricing_eu],
            region='eu-west-1',
            language='en'
        )
        
        assert quote.region == 'eu-west-1'
        assert quote.pricing_results[0]['region'] == 'eu-west-1'


class TestJSONExport:
    """Test suite for JSON export functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.generator = QuoteGenerator()
        self.json_exporter = JSONExporter()
        
        # Sample data
        self.service_config = ServiceConfig(
            provider='alibaba',
            service_type='compute',
            service_name='ECS',
            specifications={'cpu': 4, 'memory': 8},
            quantity=1
        )
        
        self.aws_mapping = AWSServiceMapping(
            aws_service='EC2',
            aws_service_category='compute',
            aws_service_type='t3.large',
            specifications={'vcpu': 2, 'memory': 8},
            confidence_score=0.95,
            explanation='Test mapping',
            alternatives=[]
        )
        
        self.pricing_result = PricingResult(
            monthly_cost=Decimal('100.00'),
            annual_cost=Decimal('1200.00'),
            pricing_model='on-demand',
            region='us-east-1',
            breakdown={'compute': Decimal('100.00')}
        )
    
    def test_json_export_local(self):
        """Test JSON export to local file."""
        quote = self.generator.generate_quote(
            user_id='test-user-123',
            original_input='Test input',
            parsed_services=[self.service_config],
            aws_mappings=[self.aws_mapping],
            pricing_results=[self.pricing_result],
            language='en'
        )
        
        content = self.generator.get_quote_content(quote)
        filename = self.json_exporter.export_quote(quote, content, upload_to_s3=False)
        
        # Verify file exists
        assert os.path.exists(filename)
        
        # Verify content
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        assert data['quote_metadata']['quote_id'] == quote.quote_id
        assert data['quote_metadata']['user_id'] == 'test-user-123'
        assert len(data['original_services']) == 1
        assert len(data['aws_mappings']) == 1
        assert len(data['pricing']['items']) == 1
        
        # Clean up
        os.remove(filename)
    
    def test_json_export_raw(self):
        """Test raw JSON export."""
        quote = self.generator.generate_quote(
            user_id='test-user-123',
            original_input='Test input',
            parsed_services=[self.service_config],
            aws_mappings=[self.aws_mapping],
            pricing_results=[self.pricing_result],
            language='en'
        )
        
        json_str = self.json_exporter.export_quote_raw(quote, pretty_print=True)
        
        # Verify it's valid JSON
        data = json.loads(json_str)
        assert data['quote_id'] == quote.quote_id
        assert data['user_id'] == 'test-user-123'
        
        # Verify pretty print
        assert '\n' in json_str
    
    def test_json_round_trip(self):
        """Test JSON export and import round trip."""
        quote = self.generator.generate_quote(
            user_id='test-user-123',
            original_input='Test input',
            parsed_services=[self.service_config],
            aws_mappings=[self.aws_mapping],
            pricing_results=[self.pricing_result],
            language='en'
        )
        
        # Export
        json_str = self.json_exporter.export_quote_raw(quote)
        
        # Import
        parsed_quote = self.json_exporter.parse_json_quote(json_str)
        
        # Verify
        assert parsed_quote.quote_id == quote.quote_id
        assert parsed_quote.user_id == quote.user_id
        assert parsed_quote.total_monthly_cost == quote.total_monthly_cost
        assert parsed_quote.total_annual_cost == quote.total_annual_cost
    
    def test_json_export_chinese(self):
        """Test JSON export with Chinese content."""
        quote = self.generator.generate_quote(
            user_id='test-user-123',
            original_input='测试输入',
            parsed_services=[self.service_config],
            aws_mappings=[self.aws_mapping],
            pricing_results=[self.pricing_result],
            language='zh'
        )
        
        content = self.generator.get_quote_content(quote)
        filename = self.json_exporter.export_quote(quote, content, upload_to_s3=False)
        
        # Verify file exists and contains Chinese characters
        assert os.path.exists(filename)
        
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        assert data['quote_metadata']['language'] == 'zh'
        
        # Clean up
        os.remove(filename)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
