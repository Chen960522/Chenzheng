"""Cloud provider crawlers package."""

from src.services.crawlers.base_crawler import CloudProviderCrawler
from src.services.crawlers.alibaba_crawler import AlibabaCloudCrawler
from src.services.crawlers.huawei_crawler import HuaweiCloudCrawler
from src.services.crawlers.tencent_crawler import TencentCloudCrawler
from src.services.crawlers.gcp_crawler import GCPCrawler
from src.services.crawlers.azure_crawler import AzureCrawler
from src.services.crawlers.web_crawler import WebCrawler

__all__ = [
    'CloudProviderCrawler',
    'AlibabaCloudCrawler',
    'HuaweiCloudCrawler',
    'TencentCloudCrawler',
    'GCPCrawler',
    'AzureCrawler',
    'WebCrawler'
]
