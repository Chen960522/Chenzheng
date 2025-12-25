"""Unit tests for web crawler error handling and functionality."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests
from datetime import datetime

from src.services.crawlers.base_crawler import CloudProviderCrawler
from src.services.crawlers.alibaba_crawler import AlibabaCloudCrawler
from src.services.crawlers.web_crawler import WebCrawler
from src.models.cloud_service import CloudService


class TestCrawlerRetryLogic:
    """Test retry logic with exponential backoff."""
    
    def test_fetch_page_success_first_attempt(self):
        """Test successful page fetch on first attempt."""
        crawler = AlibabaCloudCrawler()
        
        with patch.object(crawler.session, 'get') as mock_get:
            mock_response = Mock()
            mock_response.text = '<html>Test content</html>'
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response
            
            result = crawler.fetch_page('https://example.com')
            
            assert result == '<html>Test content</html>'
            assert mock_get.call_count == 1
    
    def test_fetch_page_retry_on_failure(self):
        """Test retry logic when request fails."""
        crawler = AlibabaCloudCrawler()
        
        with patch.object(crawler.session, 'get') as mock_get:
            # First two attempts fail, third succeeds
            mock_get.side_effect = [
                requests.exceptions.RequestException("Connection error"),
                requests.exceptions.RequestException("Timeout"),
                Mock(text='<html>Success</html>', raise_for_status=Mock())
            ]
            
            with patch('time.sleep'):  # Mock sleep to speed up test
                result = crawler.fetch_page('https://example.com')
            
            assert result == '<html>Success</html>'
            assert mock_get.call_count == 3
    
    def test_fetch_page_all_retries_fail(self):
        """Test behavior when all retry attempts fail."""
        crawler = AlibabaCloudCrawler()
        
        with patch.object(crawler.session, 'get') as mock_get:
            mock_get.side_effect = requests.exceptions.RequestException("Connection error")
            
            with patch('time.sleep'):  # Mock sleep to speed up test
                result = crawler.fetch_page('https://example.com')
            
            assert result is None
            assert mock_get.call_count == crawler.retry_attempts
    
    def test_fetch_page_exponential_backoff(self):
        """Test that retry delays follow exponential backoff."""
        crawler = AlibabaCloudCrawler()
        
        with patch.object(crawler.session, 'get') as mock_get:
            mock_get.side_effect = requests.exceptions.RequestException("Error")
            
            with patch('time.sleep') as mock_sleep:
                crawler.fetch_page('https://example.com')
                
                # Verify exponential backoff delays
                expected_delays = [
                    crawler.retry_delay * (2 ** 0),  # First retry: delay * 1
                    crawler.retry_delay * (2 ** 1),  # Second retry: delay * 2
                ]
                
                actual_delays = [call[0][0] for call in mock_sleep.call_args_list]
                assert actual_delays == expected_delays


class TestCrawlerErrorLogging:
    """Test error logging functionality."""
    
    def test_extract_services_logs_error_on_failure(self):
        """Test that extraction errors are logged."""
        crawler = AlibabaCloudCrawler()
        
        with patch.object(crawler, 'fetch_page', return_value=None):
            with patch('src.services.crawlers.alibaba_crawler.logger') as mock_logger:
                services = crawler.extract_services()
                
                assert services == []
                assert mock_logger.error.called
    
    def test_web_crawler_logs_provider_failures(self):
        """Test that WebCrawler logs individual provider failures."""
        mock_db = Mock()
        crawler = WebCrawler(db_service=mock_db)
        
        with patch.object(crawler, 'crawl_provider', side_effect=Exception("Test error")):
            with patch('src.services.crawlers.web_crawler.logger') as mock_logger:
                result = crawler.crawl_all_providers()
                
                # Verify error was logged for each provider
                assert mock_logger.error.call_count >= len(crawler.providers)
                
                # Verify all providers have failed status
                for provider in crawler.providers:
                    assert result['results'][provider]['status'] == 'failed'


class TestDataQualityScoring:
    """Test data quality scoring functionality."""
    
    def test_quality_score_complete_data(self):
        """Test quality score for complete service data."""
        crawler = AlibabaCloudCrawler()
        
        service_data = {
            'description': 'Complete service description with details',
            'specifications': {'cpu': '4', 'memory': '8GB'},
            'features': ['Feature 1', 'Feature 2'],
            'pricing_info': {'monthly': '100'},
            'service_name_en': 'Test Service',
            'service_name_zh': '测试服务'
        }
        
        score = crawler.calculate_data_quality_score(service_data)
        
        # All criteria met = 1.0
        assert score == 1.0
    
    def test_quality_score_minimal_data(self):
        """Test quality score for minimal service data."""
        crawler = AlibabaCloudCrawler()
        
        service_data = {
            'description': '',
            'specifications': {},
            'features': [],
            'pricing_info': None,
            'service_name_en': 'Test Service',
            'service_name_zh': None
        }
        
        score = crawler.calculate_data_quality_score(service_data)
        
        # No criteria met = 0.0
        assert score == 0.0
    
    def test_quality_score_partial_data(self):
        """Test quality score for partial service data."""
        crawler = AlibabaCloudCrawler()
        
        service_data = {
            'description': 'Good description',
            'specifications': {'cpu': '4'},
            'features': [],
            'pricing_info': None,
            'service_name_en': 'Test Service',
            'service_name_zh': None
        }
        
        score = crawler.calculate_data_quality_score(service_data)
        
        # Description + specs = 0.4
        assert score == 0.4
    
    def test_should_flag_for_review_low_quality(self):
        """Test that low quality data is flagged for review."""
        crawler = AlibabaCloudCrawler()
        
        # Quality score below threshold (0.5)
        assert crawler.should_flag_for_review(0.3) is True
        assert crawler.should_flag_for_review(0.4) is True
    
    def test_should_not_flag_high_quality(self):
        """Test that high quality data is not flagged."""
        crawler = AlibabaCloudCrawler()
        
        # Quality score at or above threshold (0.5)
        assert crawler.should_flag_for_review(0.5) is False
        assert crawler.should_flag_for_review(0.8) is False
        assert crawler.should_flag_for_review(1.0) is False


class TestWebCrawlerOrchestration:
    """Test WebCrawler orchestration functionality."""
    
    def test_crawl_all_providers_success(self):
        """Test successful crawling of all providers."""
        mock_db = Mock()
        mock_db.get_cloud_service.return_value = None
        mock_db.create_cloud_service.return_value = None
        
        crawler = WebCrawler(db_service=mock_db)
        
        # Mock each provider crawler to return test services
        for provider_name, provider_crawler in crawler.crawlers.items():
            with patch.object(provider_crawler, 'extract_services', return_value=[
                {
                    'service_name': f'{provider_name}_service',
                    'service_name_en': f'{provider_name} Service',
                    'service_name_zh': None,
                    'service_category': 'compute',
                    'description': 'Test service',
                    'specifications': {},
                    'features': [],
                    'pricing_info': None,
                    'source_url': 'https://example.com',
                    'crawled_at': datetime.utcnow().isoformat(),
                    'data_quality_score': 0.6,
                    'manual_review_required': False
                }
            ]):
                pass
        
        result = crawler.crawl_all_providers()
        
        assert 'results' in result
        assert 'report' in result
        assert len(result['results']) == len(crawler.providers)
    
    def test_crawl_provider_creates_new_services(self):
        """Test that new services are created in database."""
        mock_db = Mock()
        mock_db.get_cloud_service.return_value = None  # No existing service
        mock_db.create_cloud_service.return_value = None
        
        crawler = WebCrawler(db_service=mock_db)
        
        # Mock Alibaba crawler to return one service
        with patch.object(crawler.crawlers['alibaba'], 'extract_services', return_value=[
            {
                'service_name': 'ECS',
                'service_name_en': 'Elastic Compute Service',
                'service_name_zh': '云服务器',
                'service_category': 'compute',
                'description': 'Test service',
                'specifications': {},
                'features': [],
                'pricing_info': None,
                'source_url': 'https://example.com',
                'crawled_at': datetime.utcnow().isoformat(),
                'data_quality_score': 0.8,
                'manual_review_required': False
            }
        ]):
            result = crawler.crawl_provider('alibaba')
        
        assert result['status'] == 'success'
        assert result['new_services'] == 1
        assert result['updated_services'] == 0
        assert mock_db.create_cloud_service.called
    
    def test_crawl_provider_updates_existing_services(self):
        """Test that existing services are updated when changes detected."""
        mock_db = Mock()
        
        # Mock existing service
        existing_service = CloudService(
            service_id='test-id',
            provider='alibaba',
            service_name='ECS',
            service_name_en='Elastic Compute Service',
            service_name_zh='云服务器',
            service_category='compute',
            description='Old description',
            specifications={},
            features=[],
            pricing_info=None,
            source_url='https://example.com',
            crawled_at=datetime.utcnow(),
            last_updated=datetime.utcnow(),
            data_quality_score=0.6,
            manual_review_required=False
        )
        
        mock_db.get_cloud_service.return_value = existing_service
        mock_db.update_cloud_service.return_value = None
        
        crawler = WebCrawler(db_service=mock_db)
        
        # Mock crawler to return updated service
        with patch.object(crawler.crawlers['alibaba'], 'extract_services', return_value=[
            {
                'service_name': 'ECS',
                'service_name_en': 'Elastic Compute Service',
                'service_name_zh': '云服务器',
                'service_category': 'compute',
                'description': 'New description',  # Changed
                'specifications': {},
                'features': [],
                'pricing_info': None,
                'source_url': 'https://example.com',
                'crawled_at': datetime.utcnow().isoformat(),
                'data_quality_score': 0.8,
                'manual_review_required': False
            }
        ]):
            result = crawler.crawl_provider('alibaba')
        
        assert result['status'] == 'success'
        assert result['new_services'] == 0
        assert result['updated_services'] == 1
        assert mock_db.update_cloud_service.called
    
    def test_generate_report_includes_summary(self):
        """Test that crawling report includes summary statistics."""
        mock_db = Mock()
        crawler = WebCrawler(db_service=mock_db)
        
        results = {
            'alibaba': {'status': 'success', 'new_services': 5, 'updated_services': 2, 'total_services': 10, 'low_quality_services': 1},
            'huawei': {'status': 'success', 'new_services': 3, 'updated_services': 1, 'total_services': 8, 'low_quality_services': 0},
            'tencent': {'status': 'failed', 'error': 'Connection error', 'new_services': 0, 'updated_services': 0, 'total_services': 0, 'low_quality_services': 0}
        }
        
        start_time = datetime.utcnow()
        end_time = datetime.utcnow()
        duration = 120.5
        
        report = crawler._generate_report(results, start_time, end_time, duration)
        
        assert 'summary' in report
        assert report['summary']['total_providers'] == 5
        assert report['summary']['successful_providers'] == 2
        assert report['summary']['failed_providers'] == 1
        assert report['summary']['total_new_services'] == 8
        assert report['summary']['total_updated_services'] == 3
        assert report['summary']['total_services_crawled'] == 18
        assert report['summary']['total_low_quality_services'] == 1
        
        assert 'tencent' in report['failed_providers']
        assert 'alibaba' in report['successful_providers']
        assert 'huawei' in report['successful_providers']


class TestServiceCategoryNormalization:
    """Test service category normalization."""
    
    def test_normalize_standard_categories(self):
        """Test normalization of standard category names."""
        crawler = AlibabaCloudCrawler()
        
        assert crawler.normalize_service_category('compute') == 'compute'
        assert crawler.normalize_service_category('storage') == 'storage'
        assert crawler.normalize_service_category('database') == 'database'
    
    def test_normalize_variations(self):
        """Test normalization of category variations."""
        crawler = AlibabaCloudCrawler()
        
        assert crawler.normalize_service_category('computing') == 'compute'
        assert crawler.normalize_service_category('virtual machine') == 'compute'
        assert crawler.normalize_service_category('object storage') == 'storage'
        assert crawler.normalize_service_category('nosql') == 'database'
    
    def test_normalize_unknown_category(self):
        """Test normalization of unknown categories."""
        crawler = AlibabaCloudCrawler()
        
        assert crawler.normalize_service_category('unknown_category') == 'other'
        assert crawler.normalize_service_category('random_text') == 'other'
