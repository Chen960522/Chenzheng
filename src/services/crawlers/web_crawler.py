"""Web crawler orchestrator for coordinating multi-provider crawling."""

from typing import Dict, List, Any
from datetime import datetime
import uuid

from src.services.crawlers.alibaba_crawler import AlibabaCloudCrawler
from src.services.crawlers.huawei_crawler import HuaweiCloudCrawler
from src.services.crawlers.tencent_crawler import TencentCloudCrawler
from src.services.crawlers.gcp_crawler import GCPCrawler
from src.services.crawlers.azure_crawler import AzureCrawler
from src.services.cloud_service_service import CloudServiceService
from src.models.cloud_service import CloudService
from src.utils.logger import get_logger

logger = get_logger(__name__)


class WebCrawler:
    """Orchestrator for crawling cloud provider services."""
    
    def __init__(self, db_service: CloudServiceService = None):
        """
        Initialize WebCrawler with database service.
        
        Args:
            db_service: CloudServiceService instance for database operations
        """
        self.db = db_service or CloudServiceService()
        self.providers = ['alibaba', 'huawei', 'tencent', 'gcp', 'azure']
        self.crawlers = {
            'alibaba': AlibabaCloudCrawler(),
            'huawei': HuaweiCloudCrawler(),
            'tencent': TencentCloudCrawler(),
            'gcp': GCPCrawler(),
            'azure': AzureCrawler()
        }
    
    def crawl_all_providers(self) -> Dict[str, Any]:
        """
        Crawl all cloud providers and store results in database.
        
        Returns:
            Dictionary with crawling results and report
        """
        logger.info("Starting multi-provider crawling")
        start_time = datetime.utcnow()
        
        results = {}
        for provider in self.providers:
            try:
                logger.info(f"Crawling {provider}...")
                results[provider] = self.crawl_provider(provider)
            except Exception as e:
                logger.error(f"Failed to crawl {provider}: {e}")
                results[provider] = {
                    'status': 'failed',
                    'error': str(e),
                    'new_services': 0,
                    'updated_services': 0,
                    'total_services': 0
                }
        
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        # Generate crawling report
        report = self._generate_report(results, start_time, end_time, duration)
        
        logger.info(f"Multi-provider crawling completed in {duration:.2f} seconds")
        
        return {
            'results': results,
            'report': report
        }
    
    def crawl_provider(self, provider: str) -> Dict[str, Any]:
        """
        Crawl a specific cloud provider.
        
        Args:
            provider: Provider name ('alibaba', 'huawei', 'tencent', 'gcp', 'azure')
            
        Returns:
            Dictionary with crawling statistics
        """
        if provider not in self.crawlers:
            raise ValueError(f"Unknown provider: {provider}")
        
        crawler = self.crawlers[provider]
        
        # Extract services from provider website
        logger.info(f"Extracting services from {provider}")
        services = crawler.extract_services()
        
        if not services:
            logger.warning(f"No services extracted from {provider}")
            return {
                'status': 'success',
                'new_services': 0,
                'updated_services': 0,
                'total_services': 0,
                'low_quality_services': 0
            }
        
        new_count = 0
        updated_count = 0
        low_quality_count = 0
        
        # Process each service
        for service_data in services:
            try:
                # Check if service already exists
                existing = self.db.get_cloud_service(
                    provider,
                    service_data['service_name']
                )
                
                # Create CloudService object
                cloud_service = CloudService(
                    service_id=existing.service_id if existing else CloudService.generate_id(),
                    provider=provider,
                    service_name=service_data['service_name'],
                    service_name_en=service_data['service_name_en'],
                    service_name_zh=service_data.get('service_name_zh'),
                    service_category=service_data['service_category'],
                    description=service_data['description'],
                    specifications=service_data['specifications'],
                    features=service_data['features'],
                    pricing_info=service_data.get('pricing_info'),
                    source_url=service_data['source_url'],
                    crawled_at=datetime.fromisoformat(service_data['crawled_at']),
                    last_updated=datetime.utcnow(),
                    data_quality_score=service_data['data_quality_score'],
                    manual_review_required=service_data['manual_review_required']
                )
                
                if existing is None:
                    # New service
                    self.db.create_cloud_service(cloud_service)
                    new_count += 1
                    logger.info(f"Created new service: {provider}/{service_data['service_name']}")
                elif self._has_changes(existing, cloud_service):
                    # Updated service
                    self.db.update_cloud_service(cloud_service)
                    updated_count += 1
                    logger.info(f"Updated service: {provider}/{service_data['service_name']}")
                
                # Count low quality services
                if cloud_service.manual_review_required:
                    low_quality_count += 1
                    
            except Exception as e:
                logger.error(f"Failed to process service {service_data.get('service_name', 'unknown')}: {e}")
                continue
        
        return {
            'status': 'success',
            'new_services': new_count,
            'updated_services': updated_count,
            'total_services': len(services),
            'low_quality_services': low_quality_count
        }
    
    def _has_changes(self, existing: CloudService, new: CloudService) -> bool:
        """
        Check if a service has changes that warrant an update.
        
        Args:
            existing: Existing CloudService from database
            new: New CloudService from crawling
            
        Returns:
            True if service has meaningful changes
        """
        # Compare key fields
        if existing.description != new.description:
            return True
        
        if existing.specifications != new.specifications:
            return True
        
        if existing.features != new.features:
            return True
        
        if existing.pricing_info != new.pricing_info:
            return True
        
        if existing.data_quality_score != new.data_quality_score:
            return True
        
        return False
    
    def _generate_report(
        self,
        results: Dict[str, Dict[str, Any]],
        start_time: datetime,
        end_time: datetime,
        duration: float
    ) -> Dict[str, Any]:
        """
        Generate a crawling report.
        
        Args:
            results: Crawling results for all providers
            start_time: Crawling start time
            end_time: Crawling end time
            duration: Total duration in seconds
            
        Returns:
            Report dictionary
        """
        total_new = sum(r.get('new_services', 0) for r in results.values())
        total_updated = sum(r.get('updated_services', 0) for r in results.values())
        total_services = sum(r.get('total_services', 0) for r in results.values())
        total_low_quality = sum(r.get('low_quality_services', 0) for r in results.values())
        
        successful_providers = [p for p, r in results.items() if r.get('status') == 'success']
        failed_providers = [p for p, r in results.items() if r.get('status') == 'failed']
        
        report = {
            'report_id': str(uuid.uuid4()),
            'timestamp': end_time.isoformat(),
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'duration_seconds': duration,
            'summary': {
                'total_providers': len(self.providers),
                'successful_providers': len(successful_providers),
                'failed_providers': len(failed_providers),
                'total_new_services': total_new,
                'total_updated_services': total_updated,
                'total_services_crawled': total_services,
                'total_low_quality_services': total_low_quality
            },
            'provider_results': results,
            'successful_providers': successful_providers,
            'failed_providers': failed_providers
        }
        
        # Log summary
        logger.info(f"Crawling Report Summary:")
        logger.info(f"  - Successful providers: {len(successful_providers)}/{len(self.providers)}")
        logger.info(f"  - New services: {total_new}")
        logger.info(f"  - Updated services: {total_updated}")
        logger.info(f"  - Total services crawled: {total_services}")
        logger.info(f"  - Low quality services: {total_low_quality}")
        
        if failed_providers:
            logger.warning(f"  - Failed providers: {', '.join(failed_providers)}")
        
        return report
    
    def get_services_requiring_review(self) -> List[CloudService]:
        """
        Get all services flagged for manual review.
        
        Returns:
            List of CloudService objects requiring review
        """
        return self.db.list_services_requiring_review()
    
    def update_knowledge_base(self, provider: str = None):
        """
        Update Bedrock Knowledge Base with crawled data.
        
        This method would upload formatted service data to S3 for Knowledge Base ingestion.
        Implementation depends on Knowledge Base setup.
        
        Args:
            provider: Optional provider name to update only specific provider data
        """
        logger.info(f"Updating Knowledge Base for provider: {provider or 'all'}")
        
        # TODO: Implement Knowledge Base update logic
        # 1. Fetch services from database
        # 2. Format as markdown/JSON documents
        # 3. Upload to S3 Knowledge Base data source
        # 4. Trigger Knowledge Base sync if needed
        
        logger.warning("Knowledge Base update not yet implemented")
