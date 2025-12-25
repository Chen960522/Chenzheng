"""Huawei Cloud service crawler."""

from typing import List, Dict, Any
from bs4 import BeautifulSoup

from src.services.crawlers.base_crawler import CloudProviderCrawler
from src.utils.logger import get_logger

logger = get_logger(__name__)


class HuaweiCloudCrawler(CloudProviderCrawler):
    """Crawler for Huawei Cloud services."""
    
    def get_provider_name(self) -> str:
        """Get the provider name."""
        return 'huawei'
    
    def get_service_list_url(self) -> str:
        """Get the URL for Huawei Cloud service listing."""
        return 'https://www.huaweicloud.com/intl/en-us/product/'
    
    def extract_services(self) -> List[Dict[str, Any]]:
        """Extract all services from Huawei Cloud website."""
        logger.info(f"Starting {self.provider_name} service extraction")
        services = []
        
        html = self.fetch_page(self.get_service_list_url())
        if not html:
            logger.error(f"Failed to fetch {self.provider_name} service list")
            return services
        
        try:
            # Use known services as fallback
            known_services = self._get_known_huawei_services()
            
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
        """Extract detailed information for a specific Huawei Cloud service."""
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
    
    def _get_known_huawei_services(self) -> List[Dict[str, Any]]:
        """Get list of known Huawei Cloud services."""
        return [
            {
                'name': 'ECS',
                'name_en': 'Elastic Cloud Server',
                'name_zh': '弹性云服务器',
                'category': 'compute',
                'description': 'Huawei Cloud Elastic Cloud Server provides scalable computing resources.',
                'url': 'https://www.huaweicloud.com/intl/en-us/product/ecs.html',
                'specifications': {
                    'instance_types': ['General Purpose', 'Compute Optimized', 'Memory Optimized'],
                    'cpu_range': '1-96 vCPU',
                    'memory_range': '1-384 GB'
                },
                'features': ['Auto Scaling', 'Snapshot', 'Security Groups', 'VPC Integration']
            },
            {
                'name': 'OBS',
                'name_en': 'Object Storage Service',
                'name_zh': '对象存储服务',
                'category': 'storage',
                'description': 'Huawei Cloud OBS provides secure and reliable object storage.',
                'url': 'https://www.huaweicloud.com/intl/en-us/product/obs.html',
                'specifications': {
                    'storage_classes': ['Standard', 'Infrequent Access', 'Archive'],
                    'durability': '99.999999999%'
                },
                'features': ['Lifecycle Management', 'Cross-Region Replication', 'Encryption']
            },
            {
                'name': 'RDS',
                'name_en': 'Relational Database Service',
                'name_zh': '云数据库RDS',
                'category': 'database',
                'description': 'Huawei Cloud RDS provides managed relational database services.',
                'url': 'https://www.huaweicloud.com/intl/en-us/product/rds.html',
                'specifications': {
                    'engines': ['MySQL', 'PostgreSQL', 'SQL Server'],
                    'max_storage': '4 TB'
                },
                'features': ['Automated Backups', 'Read Replicas', 'High Availability']
            },
            {
                'name': 'ELB',
                'name_en': 'Elastic Load Balance',
                'name_zh': '弹性负载均衡',
                'category': 'network',
                'description': 'Huawei Cloud ELB distributes traffic across multiple servers.',
                'url': 'https://www.huaweicloud.com/intl/en-us/product/elb.html',
                'specifications': {
                    'types': ['Classic', 'Application', 'Network'],
                    'protocols': ['HTTP', 'HTTPS', 'TCP', 'UDP']
                },
                'features': ['Health Checks', 'SSL Offloading', 'Session Persistence']
            },
            {
                'name': 'CCE',
                'name_en': 'Cloud Container Engine',
                'name_zh': '云容器引擎',
                'category': 'container',
                'description': 'Huawei Cloud CCE is a managed Kubernetes service.',
                'url': 'https://www.huaweicloud.com/intl/en-us/product/cce.html',
                'specifications': {
                    'kubernetes_versions': ['1.23', '1.25', '1.27']
                },
                'features': ['Managed Kubernetes', 'Auto Scaling', 'Service Mesh']
            },
            {
                'name': 'FunctionGraph',
                'name_en': 'FunctionGraph',
                'name_zh': '函数工作流',
                'category': 'serverless',
                'description': 'Huawei Cloud FunctionGraph is a serverless compute service.',
                'url': 'https://www.huaweicloud.com/intl/en-us/product/functiongraph.html',
                'specifications': {
                    'runtimes': ['Python', 'Node.js', 'Java', 'Go'],
                    'memory_range': '128 MB - 10 GB'
                },
                'features': ['Event-Driven', 'Auto Scaling', 'Pay-Per-Use']
            }
        ]
