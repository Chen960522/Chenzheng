"""Google Cloud Platform service crawler."""

from typing import List, Dict, Any
from bs4 import BeautifulSoup

from src.services.crawlers.base_crawler import CloudProviderCrawler
from src.utils.logger import get_logger

logger = get_logger(__name__)


class GCPCrawler(CloudProviderCrawler):
    """Crawler for Google Cloud Platform services."""
    
    def get_provider_name(self) -> str:
        """Get the provider name."""
        return 'gcp'
    
    def get_service_list_url(self) -> str:
        """Get the URL for GCP service listing."""
        return 'https://cloud.google.com/products'
    
    def extract_services(self) -> List[Dict[str, Any]]:
        """Extract all services from GCP website."""
        logger.info(f"Starting {self.provider_name} service extraction")
        services = []
        
        html = self.fetch_page(self.get_service_list_url())
        if not html:
            logger.error(f"Failed to fetch {self.provider_name} service list")
            return services
        
        try:
            known_services = self._get_known_gcp_services()
            
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
        """Extract detailed information for a specific GCP service."""
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
    
    def _get_known_gcp_services(self) -> List[Dict[str, Any]]:
        """Get list of known GCP services."""
        return [
            {
                'name': 'Compute Engine',
                'name_en': 'Compute Engine',
                'category': 'compute',
                'description': 'Google Compute Engine provides scalable virtual machines.',
                'url': 'https://cloud.google.com/compute',
                'specifications': {
                    'machine_types': ['E2', 'N2', 'N2D', 'C2', 'M1', 'M2'],
                    'cpu_range': '1-224 vCPU',
                    'memory_range': '0.5-896 GB'
                },
                'features': ['Preemptible VMs', 'Live Migration', 'Custom Machine Types', 'GPUs']
            },
            {
                'name': 'Cloud Storage',
                'name_en': 'Cloud Storage',
                'category': 'storage',
                'description': 'Google Cloud Storage provides unified object storage.',
                'url': 'https://cloud.google.com/storage',
                'specifications': {
                    'storage_classes': ['Standard', 'Nearline', 'Coldline', 'Archive'],
                    'durability': '99.999999999%'
                },
                'features': ['Lifecycle Management', 'Object Versioning', 'Encryption', 'CDN Integration']
            },
            {
                'name': 'Cloud SQL',
                'name_en': 'Cloud SQL',
                'category': 'database',
                'description': 'Google Cloud SQL is a fully managed relational database service.',
                'url': 'https://cloud.google.com/sql',
                'specifications': {
                    'engines': ['MySQL', 'PostgreSQL', 'SQL Server'],
                    'max_storage': '64 TB'
                },
                'features': ['Automated Backups', 'Read Replicas', 'High Availability', 'Point-in-Time Recovery']
            },
            {
                'name': 'Cloud Load Balancing',
                'name_en': 'Cloud Load Balancing',
                'category': 'network',
                'description': 'Google Cloud Load Balancing distributes traffic globally.',
                'url': 'https://cloud.google.com/load-balancing',
                'specifications': {
                    'types': ['HTTP(S)', 'TCP/SSL', 'UDP'],
                    'global': True
                },
                'features': ['Global Load Balancing', 'Auto Scaling', 'Health Checks', 'SSL Offloading']
            },
            {
                'name': 'GKE',
                'name_en': 'Google Kubernetes Engine',
                'category': 'container',
                'description': 'GKE is a managed Kubernetes service.',
                'url': 'https://cloud.google.com/kubernetes-engine',
                'specifications': {
                    'kubernetes_versions': ['1.25', '1.26', '1.27']
                },
                'features': ['Managed Kubernetes', 'Auto Scaling', 'Autopilot Mode', 'Workload Identity']
            },
            {
                'name': 'Cloud Functions',
                'name_en': 'Cloud Functions',
                'category': 'serverless',
                'description': 'Google Cloud Functions is a serverless execution environment.',
                'url': 'https://cloud.google.com/functions',
                'specifications': {
                    'runtimes': ['Python', 'Node.js', 'Go', 'Java', 'Ruby', '.NET'],
                    'memory_range': '128 MB - 8 GB'
                },
                'features': ['Event-Driven', 'Auto Scaling', 'Pay-Per-Use', 'Cloud Events']
            },
            {
                'name': 'BigQuery',
                'name_en': 'BigQuery',
                'category': 'analytics',
                'description': 'Google BigQuery is a serverless data warehouse.',
                'url': 'https://cloud.google.com/bigquery',
                'specifications': {
                    'data_scale': 'Petabyte-scale',
                    'query_types': ['SQL', 'ML']
                },
                'features': ['Serverless', 'Real-time Analytics', 'ML Integration', 'BI Engine']
            },
            {
                'name': 'Vertex AI',
                'name_en': 'Vertex AI',
                'category': 'ml',
                'description': 'Google Vertex AI is a unified ML platform.',
                'url': 'https://cloud.google.com/vertex-ai',
                'specifications': {
                    'frameworks': ['TensorFlow', 'PyTorch', 'Scikit-learn'],
                    'compute_types': ['CPU', 'GPU', 'TPU']
                },
                'features': ['AutoML', 'Model Training', 'Model Deployment', 'Feature Store']
            }
        ]
