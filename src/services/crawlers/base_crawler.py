"""Base crawler class for cloud provider service information extraction."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import requests
import time
from datetime import datetime

from src.utils.logger import get_logger
from src.config.settings import settings

logger = get_logger(__name__)


class CloudProviderCrawler(ABC):
    """Abstract base class for cloud provider crawlers."""
    
    def __init__(self):
        """Initialize crawler with HTTP session and retry configuration."""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': settings.crawler_user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,zh-CN,zh;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive'
        })
        
        self.retry_attempts = settings.crawler_retry_attempts
        self.retry_delay = settings.crawler_retry_delay
        self.provider_name = self.get_provider_name()
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Get the provider name (e.g., 'alibaba', 'huawei', 'tencent', 'gcp', 'azure')."""
        pass
    
    @abstractmethod
    def get_service_list_url(self) -> str:
        """Get the URL for the service listing page."""
        pass
    
    @abstractmethod
    def extract_services(self) -> List[Dict[str, Any]]:
        """
        Extract all services from the provider website.
        
        Returns:
            List of service dictionaries with keys:
            - service_name: str
            - service_name_en: str
            - service_name_zh: Optional[str]
            - service_category: str
            - description: str
            - specifications: Dict[str, Any]
            - features: List[str]
            - pricing_info: Optional[Dict]
            - source_url: str
        """
        pass
    
    @abstractmethod
    def extract_service_details(self, service_url: str) -> Dict[str, Any]:
        """
        Extract detailed information for a specific service.
        
        Args:
            service_url: URL of the service detail page
            
        Returns:
            Dictionary with service details
        """
        pass
    
    def fetch_page(self, url: str, timeout: int = 30) -> Optional[str]:
        """
        Fetch a web page with retry logic and exponential backoff.
        
        Args:
            url: URL to fetch
            timeout: Request timeout in seconds
            
        Returns:
            Page HTML content or None if all retries failed
        """
        for attempt in range(self.retry_attempts):
            try:
                logger.info(f"Fetching {url} (attempt {attempt + 1}/{self.retry_attempts})")
                
                response = self.session.get(url, timeout=timeout)
                response.raise_for_status()
                
                logger.info(f"Successfully fetched {url}")
                return response.text
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"Failed to fetch {url} (attempt {attempt + 1}/{self.retry_attempts}): {e}")
                
                if attempt < self.retry_attempts - 1:
                    # Exponential backoff: delay * 2^attempt
                    delay = self.retry_delay * (2 ** attempt)
                    logger.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    logger.error(f"All retry attempts failed for {url}")
                    return None
        
        return None
    
    def calculate_data_quality_score(self, service_data: Dict[str, Any]) -> float:
        """
        Calculate data quality score for a service (0.0 to 1.0).
        
        Scoring criteria:
        - Has description: +0.2
        - Has specifications: +0.2
        - Has features: +0.2
        - Has pricing info: +0.2
        - Has both English and Chinese names: +0.2
        
        Args:
            service_data: Service data dictionary
            
        Returns:
            Quality score between 0.0 and 1.0
        """
        score = 0.0
        
        # Check description
        if service_data.get('description') and len(service_data['description']) > 10:
            score += 0.2
        
        # Check specifications
        if service_data.get('specifications') and len(service_data['specifications']) > 0:
            score += 0.2
        
        # Check features
        if service_data.get('features') and len(service_data['features']) > 0:
            score += 0.2
        
        # Check pricing info
        if service_data.get('pricing_info'):
            score += 0.2
        
        # Check bilingual names
        if service_data.get('service_name_en') and service_data.get('service_name_zh'):
            score += 0.2
        
        return round(score, 2)
    
    def should_flag_for_review(self, quality_score: float, threshold: float = 0.5) -> bool:
        """
        Determine if service data should be flagged for manual review.
        
        Args:
            quality_score: Data quality score (0.0 to 1.0)
            threshold: Minimum acceptable quality score
            
        Returns:
            True if data should be flagged for review
        """
        return quality_score < threshold
    
    def normalize_service_category(self, category: str) -> str:
        """
        Normalize service category to standard categories.
        
        Standard categories:
        - compute, storage, database, network, analytics, ml, container,
          serverless, messaging, monitoring, security, cdn, iot, blockchain,
          developer-tools, management, integration, business, media, gaming
        
        Args:
            category: Raw category string
            
        Returns:
            Normalized category string
        """
        category_lower = category.lower().strip()
        
        # Mapping of common variations to standard categories
        category_map = {
            # Compute
            'compute': 'compute',
            'computing': 'compute',
            'virtual machine': 'compute',
            'vm': 'compute',
            'instance': 'compute',
            'ecs': 'compute',
            'ec2': 'compute',
            
            # Storage
            'storage': 'storage',
            'object storage': 'storage',
            'block storage': 'storage',
            'file storage': 'storage',
            's3': 'storage',
            'oss': 'storage',
            
            # Database
            'database': 'database',
            'db': 'database',
            'rds': 'database',
            'nosql': 'database',
            'sql': 'database',
            
            # Network
            'network': 'network',
            'networking': 'network',
            'cdn': 'cdn',
            'content delivery': 'cdn',
            'load balancer': 'network',
            'vpn': 'network',
            
            # Analytics
            'analytics': 'analytics',
            'data analytics': 'analytics',
            'big data': 'analytics',
            'data warehouse': 'analytics',
            
            # Machine Learning
            'machine learning': 'ml',
            'ml': 'ml',
            'ai': 'ml',
            'artificial intelligence': 'ml',
            
            # Container
            'container': 'container',
            'kubernetes': 'container',
            'docker': 'container',
            'k8s': 'container',
            
            # Serverless
            'serverless': 'serverless',
            'function': 'serverless',
            'lambda': 'serverless',
            
            # Messaging
            'messaging': 'messaging',
            'message queue': 'messaging',
            'mq': 'messaging',
            'queue': 'messaging',
            
            # Monitoring
            'monitoring': 'monitoring',
            'observability': 'monitoring',
            'logging': 'monitoring',
            
            # Security
            'security': 'security',
            'identity': 'security',
            'access management': 'security',
            'iam': 'security',
            
            # IoT
            'iot': 'iot',
            'internet of things': 'iot',
            
            # Blockchain
            'blockchain': 'blockchain',
            
            # Developer Tools
            'developer tools': 'developer-tools',
            'devops': 'developer-tools',
            'ci/cd': 'developer-tools',
            
            # Management
            'management': 'management',
            'governance': 'management',
            
            # Integration
            'integration': 'integration',
            'application integration': 'integration',
            
            # Business Applications
            'business': 'business',
            'enterprise': 'business',
            
            # Media
            'media': 'media',
            'video': 'media',
            'streaming': 'media',
            
            # Gaming
            'gaming': 'gaming',
            'game': 'gaming'
        }
        
        # Try exact match first
        if category_lower in category_map:
            return category_map[category_lower]
        
        # Try partial match
        for key, value in category_map.items():
            if key in category_lower:
                return value
        
        # Default to 'other' if no match found
        logger.warning(f"Unknown service category: {category}, defaulting to 'other'")
        return 'other'
    
    def create_service_dict(
        self,
        service_name: str,
        service_name_en: str,
        service_category: str,
        description: str,
        source_url: str,
        service_name_zh: Optional[str] = None,
        specifications: Optional[Dict[str, Any]] = None,
        features: Optional[List[str]] = None,
        pricing_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a standardized service dictionary.
        
        Args:
            service_name: Service name (primary identifier)
            service_name_en: English service name
            service_category: Service category
            description: Service description
            source_url: URL where data was extracted from
            service_name_zh: Optional Chinese service name
            specifications: Optional service specifications
            features: Optional list of features
            pricing_info: Optional pricing information
            
        Returns:
            Standardized service dictionary
        """
        service_data = {
            'service_name': service_name,
            'service_name_en': service_name_en,
            'service_name_zh': service_name_zh,
            'service_category': self.normalize_service_category(service_category),
            'description': description,
            'specifications': specifications or {},
            'features': features or [],
            'pricing_info': pricing_info,
            'source_url': source_url,
            'crawled_at': datetime.utcnow().isoformat()
        }
        
        # Calculate quality score
        quality_score = self.calculate_data_quality_score(service_data)
        service_data['data_quality_score'] = quality_score
        service_data['manual_review_required'] = self.should_flag_for_review(quality_score)
        
        return service_data
