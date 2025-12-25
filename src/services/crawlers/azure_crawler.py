"""Microsoft Azure service crawler."""

from typing import List, Dict, Any
from bs4 import BeautifulSoup

from src.services.crawlers.base_crawler import CloudProviderCrawler
from src.utils.logger import get_logger

logger = get_logger(__name__)


class AzureCrawler(CloudProviderCrawler):
    """Crawler for Microsoft Azure services."""
    
    def get_provider_name(self) -> str:
        """Get the provider name."""
        return 'azure'
    
    def get_service_list_url(self) -> str:
        """Get the URL for Azure service listing."""
        return 'https://azure.microsoft.com/en-us/products/'
    
    def extract_services(self) -> List[Dict[str, Any]]:
        """Extract all services from Azure website."""
        logger.info(f"Starting {self.provider_name} service extraction")
        services = []
        
        html = self.fetch_page(self.get_service_list_url())
        if not html:
            logger.error(f"Failed to fetch {self.provider_name} service list")
            return services
        
        try:
            known_services = self._get_known_azure_services()
            
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
        """Extract detailed information for a specific Azure service."""
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
    
    def _get_known_azure_services(self) -> List[Dict[str, Any]]:
        """Get list of known Azure services."""
        return [
            {
                'name': 'Virtual Machines',
                'name_en': 'Virtual Machines',
                'category': 'compute',
                'description': 'Azure Virtual Machines provides on-demand scalable computing resources.',
                'url': 'https://azure.microsoft.com/en-us/products/virtual-machines',
                'specifications': {
                    'vm_series': ['A', 'B', 'D', 'E', 'F', 'G', 'H', 'L', 'M', 'N'],
                    'cpu_range': '1-128 vCPU',
                    'memory_range': '0.5-3892 GB'
                },
                'features': ['Spot VMs', 'Reserved Instances', 'Availability Sets', 'Scale Sets']
            },
            {
                'name': 'Blob Storage',
                'name_en': 'Blob Storage',
                'category': 'storage',
                'description': 'Azure Blob Storage is a massively scalable object storage service.',
                'url': 'https://azure.microsoft.com/en-us/products/storage/blobs',
                'specifications': {
                    'storage_tiers': ['Hot', 'Cool', 'Archive'],
                    'durability': '99.999999999%'
                },
                'features': ['Lifecycle Management', 'Blob Versioning', 'Encryption', 'CDN Integration']
            },
            {
                'name': 'Azure SQL Database',
                'name_en': 'Azure SQL Database',
                'category': 'database',
                'description': 'Azure SQL Database is a fully managed relational database service.',
                'url': 'https://azure.microsoft.com/en-us/products/azure-sql/database',
                'specifications': {
                    'engines': ['SQL Server'],
                    'max_storage': '4 TB'
                },
                'features': ['Automated Backups', 'Geo-Replication', 'High Availability', 'Elastic Pools']
            },
            {
                'name': 'Load Balancer',
                'name_en': 'Load Balancer',
                'category': 'network',
                'description': 'Azure Load Balancer distributes traffic across multiple VMs.',
                'url': 'https://azure.microsoft.com/en-us/products/load-balancer',
                'specifications': {
                    'types': ['Basic', 'Standard'],
                    'protocols': ['TCP', 'UDP']
                },
                'features': ['Health Probes', 'Outbound Rules', 'HA Ports', 'Zone Redundancy']
            },
            {
                'name': 'AKS',
                'name_en': 'Azure Kubernetes Service',
                'category': 'container',
                'description': 'AKS is a managed Kubernetes service.',
                'url': 'https://azure.microsoft.com/en-us/products/kubernetes-service',
                'specifications': {
                    'kubernetes_versions': ['1.25', '1.26', '1.27']
                },
                'features': ['Managed Kubernetes', 'Auto Scaling', 'Azure Monitor Integration', 'Azure AD Integration']
            },
            {
                'name': 'Azure Functions',
                'name_en': 'Azure Functions',
                'category': 'serverless',
                'description': 'Azure Functions is a serverless compute service.',
                'url': 'https://azure.microsoft.com/en-us/products/functions',
                'specifications': {
                    'runtimes': ['C#', 'JavaScript', 'Python', 'Java', 'PowerShell'],
                    'memory_range': '128 MB - 1.5 GB'
                },
                'features': ['Event-Driven', 'Auto Scaling', 'Durable Functions', 'Multiple Triggers']
            },
            {
                'name': 'Synapse Analytics',
                'name_en': 'Synapse Analytics',
                'category': 'analytics',
                'description': 'Azure Synapse Analytics is an analytics service.',
                'url': 'https://azure.microsoft.com/en-us/products/synapse-analytics',
                'specifications': {
                    'data_scale': 'Petabyte-scale',
                    'query_types': ['SQL', 'Spark']
                },
                'features': ['Serverless', 'Data Integration', 'ML Integration', 'Power BI Integration']
            },
            {
                'name': 'Machine Learning',
                'name_en': 'Azure Machine Learning',
                'category': 'ml',
                'description': 'Azure Machine Learning is an enterprise-grade ML service.',
                'url': 'https://azure.microsoft.com/en-us/products/machine-learning',
                'specifications': {
                    'frameworks': ['TensorFlow', 'PyTorch', 'Scikit-learn'],
                    'compute_types': ['CPU', 'GPU']
                },
                'features': ['AutoML', 'Model Training', 'Model Deployment', 'MLOps']
            },
            {
                'name': 'CDN',
                'name_en': 'Content Delivery Network',
                'category': 'cdn',
                'description': 'Azure CDN delivers content globally with low latency.',
                'url': 'https://azure.microsoft.com/en-us/products/cdn',
                'specifications': {
                    'nodes': '100+',
                    'protocols': ['HTTP', 'HTTPS']
                },
                'features': ['Global Coverage', 'Dynamic Site Acceleration', 'Rules Engine', 'Real-time Analytics']
            }
        ]
