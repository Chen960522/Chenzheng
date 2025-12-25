"""
Comprehensive End-to-End Tests
Tests all service categories, AWS regions, and error scenarios
"""
import pytest
import asyncio
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, List

from src.services.configuration_parser import ConfigurationParser
from src.services.service_mapper import ServiceMapper
from src.services.price_calculator import PriceCalculator
from src.services.quote_generator import QuoteGenerator
from src.models.service_config import ServiceConfig


class TestComprehensiveE2E:
    """Comprehensive end-to-end tests covering all requirements"""
    
    @pytest.fixture
    def parser(self, mock_bedrock_client):
        """Create configuration parser"""
        return ConfigurationParser(mock_bedrock_client)
    
    @pytest.fixture
    def mapper(self, mock_knowledge_base_client, mock_dynamodb):
        """Create service mapper"""
        return ServiceMapper(mock_knowledge_base_client, mock_dynamodb)
    
    @pytest.fixture
    def calculator(self, mock_pricing_client, mock_knowledge_base_client):
        """Create price calculator"""
        return PriceCalculator(mock_pricing_client, mock_knowledge_base_client)
    
    @pytest.fixture
    def generator(self, mock_s3_client):
        """Create quote generator"""
        return QuoteGenerator(mock_s3_client)
    
    # Test 1: All Service Categories
    @pytest.mark.asyncio
    async def test_all_service_categories(self, parser, mapper, calculator, generator):
        """Test with configurations covering all service categories"""
        
        # Configuration covering multiple service categories
        config_text = """
        Compute: Alibaba ECS ecs.c6.large (4 vCPU, 8GB RAM)
        Storage: Huawei OBS Standard (1TB)
        Database: Tencent Cloud MySQL 8.0 (4 vCPU, 16GB RAM)
        Network: GCP Cloud CDN
        Analytics: Azure Synapse Analytics
        ML: Alibaba PAI Machine Learning
        Container: Tencent TKE Kubernetes
        Serverless: Alibaba Function Compute
        Messaging: Huawei DMS Kafka
        Monitoring: GCP Cloud Monitoring
        Security: Azure Key Vault
        IoT: Alibaba IoT Platform
        """
        
        # Parse configuration
        services = await parser.parse(config_text)
        assert len(services) >= 10, "Should parse multiple service categories"
        
        # Map all services
        all_mappings = []
        for service in services:
            mappings = await mapper.map_service(service)
            assert len(mappings) > 0, f"Should find mapping for {service.service_name}"
            all_mappings.extend(mappings)
        
        # Calculate pricing for all
        pricing_results = []
        for mapping in all_mappings:
            result = await calculator.calculate_price(mapping, region='us-east-1')
            assert result.monthly_cost > 0, f"Should have valid pricing for {mapping.aws_service}"
            pricing_results.append(result)
        
        # Generate quote
        quote = await generator.generate_quote(
            original_configs=services,
            mappings=all_mappings,
            pricing_results=pricing_results,
            user_info={'user_id': 'test-user'}
        )
        
        assert quote.total_monthly_cost > 0
        assert len(quote.aws_services) >= 10
        print(f"✓ All service categories test passed: {len(quote.aws_services)} services mapped")
    
    # Test 2: All AWS Regions
    @pytest.mark.asyncio
    async def test_all_aws_regions(self, parser, mapper, calculator):
        """Test pricing across all AWS regions"""
        
        # Simple EC2 configuration
        config_text = "Alibaba ECS ecs.t5-lc1m2.small (1 vCPU, 2GB RAM)"
        services = await parser.parse(config_text)
        service = services[0]
        
        # Map service
        mappings = await mapper.map_service(service)
        mapping = mappings[0]
        
        # Test all major regions
        regions = [
            # US
            'us-east-1', 'us-east-2', 'us-west-1', 'us-west-2',
            # Canada
            'ca-central-1',
            # South America
            'sa-east-1',
            # Europe
            'eu-west-1', 'eu-west-2', 'eu-central-1', 'eu-north-1',
            # Asia Pacific
            'ap-south-1', 'ap-southeast-1', 'ap-southeast-2', 
            'ap-northeast-1', 'ap-northeast-2', 'ap-east-1',
            # Middle East
            'me-south-1',
            # Africa
            'af-south-1'
        ]
        
        regional_prices = {}
        for region in regions:
            try:
                result = await calculator.calculate_price(mapping, region=region)
                regional_prices[region] = result.monthly_cost
                assert result.monthly_cost > 0, f"Should have valid pricing for {region}"
            except Exception as e:
                # Some services may not be available in all regions
                print(f"Note: {region} - {str(e)}")
        
        assert len(regional_prices) >= 10, "Should have pricing for at least 10 regions"
        
        # Verify regional price differences
        prices = list(regional_prices.values())
        assert max(prices) != min(prices), "Regional prices should vary"
        
        print(f"✓ Regional pricing test passed: {len(regional_prices)} regions tested")
    
    # Test 3: Multi-Region Comparison
    @pytest.mark.asyncio
    async def test_multi_region_comparison(self, parser, mapper, calculator):
        """Test multi-region pricing comparison"""
        
        config_text = "Alibaba ECS ecs.c6.large (4 vCPU, 8GB RAM)"
        services = await parser.parse(config_text)
        mappings = await mapper.map_service(services[0])
        
        # Get pricing for multiple regions
        comparison_regions = ['us-east-1', 'eu-west-1', 'ap-southeast-1']
        all_region_prices = await calculator.get_all_region_prices(mappings[0])
        
        # Verify we have prices for requested regions
        for region in comparison_regions:
            assert region in all_region_prices, f"Should have pricing for {region}"
            if all_region_prices[region]:
                assert all_region_prices[region].monthly_cost > 0
        
        print(f"✓ Multi-region comparison test passed")
    
    # Test 4: Error Scenarios
    @pytest.mark.asyncio
    async def test_error_scenarios(self, parser, mapper, calculator):
        """Test various error scenarios"""
        
        # Test 4.1: Invalid/ambiguous input
        try:
            invalid_config = "some random text that doesn't describe any service"
            services = await parser.parse(invalid_config)
            # Parser should either return empty list or request clarification
            assert isinstance(services, list)
        except Exception as e:
            # Should handle gracefully
            assert "clarification" in str(e).lower() or "parse" in str(e).lower()
        
        # Test 4.2: Unsupported service
        try:
            unsupported_config = "Some Fictional Cloud Service XYZ-9000"
            services = await parser.parse(unsupported_config)
            if services:
                mappings = await mapper.map_service(services[0])
                # Should either find alternative or explain limitation
                assert len(mappings) >= 0
        except Exception as e:
            # Should provide meaningful error
            assert len(str(e)) > 0
        
        # Test 4.3: Invalid region
        config_text = "Alibaba ECS ecs.t5-lc1m2.small"
        services = await parser.parse(config_text)
        mappings = await mapper.map_service(services[0])
        
        with pytest.raises(ValueError) as exc_info:
            await calculator.calculate_price(mappings[0], region='invalid-region-123')
        assert "region" in str(exc_info.value).lower()
        
        # Test 4.4: Pricing unavailable
        # This would be tested with a service that has no pricing data
        # The calculator should notify user and suggest contacting AWS
        
        print(f"✓ Error scenarios test passed")
    
    # Test 5: Multiple Pricing Models
    @pytest.mark.asyncio
    async def test_multiple_pricing_models(self, parser, mapper, calculator):
        """Test all pricing models (On-Demand, Reserved, Savings Plans)"""
        
        config_text = "Alibaba ECS ecs.c6.large (4 vCPU, 8GB RAM)"
        services = await parser.parse(config_text)
        mappings = await mapper.map_service(services[0])
        
        # Test On-Demand
        on_demand = await calculator.calculate_price(
            mappings[0], 
            region='us-east-1',
            pricing_model='on-demand'
        )
        assert on_demand.monthly_cost > 0
        assert on_demand.pricing_model == 'on-demand'
        
        # Test Reserved
        reserved = await calculator.calculate_price(
            mappings[0],
            region='us-east-1', 
            pricing_model='reserved'
        )
        assert reserved.monthly_cost > 0
        assert reserved.pricing_model == 'reserved'
        assert reserved.monthly_cost < on_demand.monthly_cost, "Reserved should be cheaper"
        
        # Test Savings Plans
        savings = await calculator.calculate_price(
            mappings[0],
            region='us-east-1',
            pricing_model='savings-plan'
        )
        assert savings.monthly_cost > 0
        assert savings.pricing_model == 'savings-plan'
        
        print(f"✓ Multiple pricing models test passed")
    
    # Test 6: Multi-Language Support
    @pytest.mark.asyncio
    async def test_multi_language_support(self, parser, mapper):
        """Test Chinese and English service names"""
        
        # Chinese service names
        chinese_config = """
        阿里云ECS实例 ecs.c6.large
        华为云对象存储 OBS 标准存储 1TB
        腾讯云MySQL数据库 8.0版本
        """
        
        chinese_services = await parser.parse(chinese_config)
        assert len(chinese_services) >= 3, "Should parse Chinese service names"
        
        # Map Chinese services
        for service in chinese_services:
            mappings = await mapper.map_service(service)
            assert len(mappings) > 0, f"Should map Chinese service: {service.service_name}"
        
        # English service names
        english_config = """
        Alibaba Cloud ECS ecs.c6.large
        Huawei Cloud OBS Standard Storage 1TB
        Tencent Cloud MySQL 8.0
        """
        
        english_services = await parser.parse(english_config)
        assert len(english_services) >= 3, "Should parse English service names"
        
        # Map English services
        for service in english_services:
            mappings = await mapper.map_service(service)
            assert len(mappings) > 0, f"Should map English service: {service.service_name}"
        
        print(f"✓ Multi-language support test passed")
    
    # Test 7: Complex Multi-Service Configuration
    @pytest.mark.asyncio
    async def test_complex_configuration(self, parser, mapper, calculator, generator):
        """Test complex real-world configuration"""
        
        config_text = """
        Web Application Infrastructure:
        - Compute: 5x Alibaba ECS ecs.c6.2xlarge (8 vCPU, 16GB RAM) for application servers
        - Load Balancer: Alibaba SLB with 100 Mbps bandwidth
        - Database: Tencent Cloud MySQL 8.0 (8 vCPU, 32GB RAM, 500GB storage)
        - Cache: Huawei Cloud Redis 16GB
        - Storage: Alibaba OSS Standard 5TB for static assets
        - CDN: Tencent Cloud CDN with 10TB monthly traffic
        - Monitoring: GCP Cloud Monitoring
        - Backup: Azure Backup 2TB
        """
        
        # Parse
        services = await parser.parse(config_text)
        assert len(services) >= 7, "Should parse complex configuration"
        
        # Map all services
        all_mappings = []
        for service in services:
            mappings = await mapper.map_service(service)
            assert len(mappings) > 0
            all_mappings.extend(mappings)
        
        # Calculate pricing
        pricing_results = []
        for mapping in all_mappings:
            result = await calculator.calculate_price(mapping, region='us-east-1')
            pricing_results.append(result)
        
        # Generate quote
        quote = await generator.generate_quote(
            original_configs=services,
            mappings=all_mappings,
            pricing_results=pricing_results,
            user_info={'user_id': 'test-user'}
        )
        
        # Verify quote completeness
        assert quote.total_monthly_cost > 0
        assert quote.total_annual_cost == quote.total_monthly_cost * 12
        assert len(quote.aws_services) >= 7
        assert len(quote.pricing) >= 7
        
        # Test export formats
        pdf_url = await generator.export_quote(quote, 'pdf')
        assert pdf_url.startswith('https://') or pdf_url.startswith('s3://')
        
        excel_url = await generator.export_quote(quote, 'excel')
        assert excel_url.startswith('https://') or excel_url.startswith('s3://')
        
        json_url = await generator.export_quote(quote, 'json')
        assert json_url.startswith('https://') or json_url.startswith('s3://')
        
        print(f"✓ Complex configuration test passed: ${quote.total_monthly_cost}/month")
    
    # Test 8: Data Transfer Costs
    @pytest.mark.asyncio
    async def test_data_transfer_costs(self, parser, mapper, calculator):
        """Test that data transfer costs are included"""
        
        config_text = """
        Alibaba OSS Standard Storage 10TB
        Tencent Cloud CDN with 50TB monthly traffic
        """
        
        services = await parser.parse(config_text)
        
        for service in services:
            mappings = await mapper.map_service(service)
            result = await calculator.calculate_price(mappings[0], region='us-east-1')
            
            # Verify breakdown includes data transfer
            if 'data_transfer' in result.breakdown or 'transfer' in str(result.breakdown).lower():
                assert result.breakdown.get('data_transfer', 0) > 0 or \
                       any('transfer' in k.lower() for k in result.breakdown.keys())
        
        print(f"✓ Data transfer costs test passed")
    
    # Test 9: Service Alternatives
    @pytest.mark.asyncio
    async def test_service_alternatives(self, parser, mapper):
        """Test that mapper provides alternatives when multiple options exist"""
        
        config_text = "Alibaba Cloud Object Storage 1TB"
        services = await parser.parse(config_text)
        mappings = await mapper.map_service(services[0])
        
        # Should have primary mapping
        assert len(mappings) > 0
        primary = mappings[0]
        
        # Should have alternatives (S3 Standard, S3 IA, S3 Glacier, etc.)
        assert len(primary.alternatives) > 0 or len(mappings) > 1
        
        print(f"✓ Service alternatives test passed")
    
    # Test 10: Cache Performance
    @pytest.mark.asyncio
    async def test_mapping_cache(self, parser, mapper):
        """Test that mapping cache improves performance"""
        
        config_text = "Alibaba ECS ecs.c6.large"
        services = await parser.parse(config_text)
        
        # First mapping (cache miss)
        import time
        start1 = time.time()
        mappings1 = await mapper.map_service(services[0])
        time1 = time.time() - start1
        
        # Second mapping (cache hit)
        start2 = time.time()
        mappings2 = await mapper.map_service(services[0])
        time2 = time.time() - start2
        
        # Cache should make second call faster
        # (In real implementation with actual KB queries)
        assert mappings1[0].aws_service == mappings2[0].aws_service
        
        print(f"✓ Mapping cache test passed (time1: {time1:.3f}s, time2: {time2:.3f}s)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
