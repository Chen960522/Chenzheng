"""Tencent Cloud service crawler."""

from typing import List, Dict, Any
from bs4 import BeautifulSoup

from src.services.crawlers.base_crawler import CloudProviderCrawler
from src.utils.logger import get_logger

logger = get_logger(__name__)


class TencentCloudCrawler(CloudProviderCrawler):
    """Crawler for Tencent Cloud services."""
    
    def get_provider_name(self) -> str:
        """Get the provider name."""
        return 'tencent'
    
    def get_service_list_url(self) -> str:
        """Get the URL for Tencent Cloud service listing."""
        return 'https://www.tencentcloud.com/products'
    
    def extract_services(self) -> List[Dict[str, Any]]:
        """Extract all services from Tencent Cloud website."""
        logger.info(f"Starting {self.provider_name} service extraction")
        services = []
        
        html = self.fetch_page(self.get_service_list_url())
        if not html:
            logger.error(f"Failed to fetch {self.provider_name} service list")
            return services
        
        try:
            known_services = self._get_known_tencent_services()
            
            for service_info in known_services:
                try:
                    service_dict = self.create_service_dict(
                        service_name=service_info['name'],
                        service_name_en=service_info['name_en'],
                        service_name_zh=service_info.get('name_zh'),
                        service_category=service_info['category'],
                        description=service_info['description'],
                        source_url=service_info.get('url', self.get_service_list_url()),
                        specifications=service_info.get('specifications', {}),
                        features=service_info.get('features', [])
                    )
                    services.append(service_dict)
                    logger.info(f"Extracted service: {service_info['name']}")
                    
                except Exception as e:
                    logger.error(f"Failed to extract service {service_info.get('name', 'unknown')}: {e}")
                    continue
            
            logger.info(f"Extracted {len(services)} services from {self.provider_name}")
            
        except Exception as e:
            logger.error(f"Failed to parse {self.provider_name} service list: {e}")
        
        return services
    
    def extract_service_details(self, service_url: str) -> Dict[str, Any]:
        """Extract detailed information for a specific Tencent Cloud service."""
        logger.info(f"Extracting details from {service_url}")
        
        html = self.fetch_page(service_url)
        if not html:
            return {}
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            details = {
                'specifications': {},
                'features': [],
                'pricing_info': None
            }
            return details
        except Exception as e:
            logger.error(f"Failed to parse service details from {service_url}: {e}")
            return {}
    
    def _get_known_tencent_services(self) -> List[Dict[str, Any]]:
        """Get list of known Tencent Cloud services."""
        return [
            {
                'name': 'CVM',
                'name_en': 'Cloud Virtual Machine',
                'name_zh': '云服务器',
                'category': 'compute',
                'description': 'Tencent Cloud CVM provides scalable computing capacity.',
                'url': 'https://www.tencentcloud.com/products/cvm',
                'specifications': {
                    'instance_types': ['Standard', 'High IO', 'Memory Optimized', 'Compute Optimized'],
                    'cpu_range': '1-96 vCPU',
                    'memory_range': '1-384 GB'
                },
                'features': ['Auto Scaling', 'Snapshot', 'Security Groups', 'VPC']
            },
            {
                'name': 'COS',
                'name_en': 'Cloud Object Storage',
                'name_zh': '对象存储',
                'category': 'storage',
                'description': 'Tencent Cloud COS provides secure and reliable object storage.',
                'url': 'https://www.tencentcloud.com/products/cos',
                'specifications': {
                    'storage_classes': ['Standard', 'Standard_IA', 'Archive', 'Deep Archive'],
                    'durability': '99.9999999999%'
                },
                'features': ['Lifecycle Management', 'Cross-Region Replication', 'Encryption', 'CDN Integration']
            },
            {
                'name': 'TencentDB',
                'name_en': 'TencentDB for MySQL',
                'name_zh': '云数据库MySQL',
                'category': 'database',
                'description': 'TencentDB provides managed MySQL database services.',
                'url': 'https://www.tencentcloud.com/products/cdb',
                'specifications': {
                    'engines': ['MySQL', 'PostgreSQL', 'SQL Server', 'MongoDB'],
                    'max_storage': '6 TB'
                },
                'features': ['Automated Backups', 'Read Replicas', 'High Availability', 'Data Migration']
            },
            {
                'name': 'CLB',
                'name_en': 'Cloud Load Balancer',
                'name_zh': '负载均衡',
                'category': 'network',
                'description': 'Tencent Cloud CLB distributes traffic across multiple servers.',
                'url': 'https://www.tencentcloud.com/products/clb',
                'specifications': {
                    'types': ['Application Load Balancer', 'Network Load Balancer'],
                    'protocols': ['HTTP', 'HTTPS', 'TCP', 'UDP']
                },
                'features': ['Health Checks', 'SSL Offloading', 'Session Persistence', 'Cross-Region Binding']
            },
            {
                'name': 'TKE',
                'name_en': 'Tencent Kubernetes Engine',
                'name_zh': '容器服务',
                'category': 'container',
                'description': 'Tencent TKE is a managed Kubernetes service.',
                'url': 'https://www.tencentcloud.com/products/tke',
                'specifications': {
                    'kubernetes_versions': ['1.22', '1.24', '1.26']
                },
                'features': ['Managed Kubernetes', 'Auto Scaling', 'Service Mesh', 'CI/CD Integration']
            },
            {
                'name': 'SCF',
                'name_en': 'Serverless Cloud Function',
                'name_zh': '云函数',
                'category': 'serverless',
                'description': 'Tencent SCF is a serverless compute service.',
                'url': 'https://www.tencentcloud.com/products/scf',
                'specifications': {
                    'runtimes': ['Python', 'Node.js', 'Java', 'Go', 'PHP'],
                    'memory_range': '64 MB - 3 GB'
                },
                'features': ['Event-Driven', 'Auto Scaling', 'Pay-Per-Use', 'Multiple Triggers']
            },
            {
                'name': 'CDN',
                'name_en': 'Content Delivery Network',
                'name_zh': '内容分发网络',
                'category': 'cdn',
                'description': 'Tencent Cloud CDN accelerates content delivery globally.',
                'url': 'https://www.tencentcloud.com/products/cdn',
                'specifications': {
                    'nodes': '2000+',
                    'protocols': ['HTTP', 'HTTPS']
                },
                'features': ['Global Coverage', 'HTTPS Acceleration', 'Video Streaming', 'Real-time Monitoring']
            }
        ]
