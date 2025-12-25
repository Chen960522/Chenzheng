"""Quote Generator service for creating AWS pricing quotes."""

from typing import List, Dict, Any, Optional
from datetime import datetime
from decimal import Decimal

from ..models.quote import Quote, AWSServiceMapping
from ..models.service_config import ServiceConfig
from ..models.pricing_result import PricingResult
from ..utils.logger import get_logger

logger = get_logger(__name__)


class QuoteGenerator:
    """
    Service for generating AWS pricing quotes.
    
    Generates structured quote documents with:
    - Original service specifications
    - Mapped AWS services
    - Itemized pricing breakdown
    - Total costs (monthly and annual)
    - Service descriptions and benefits
    - Disclaimers about pricing estimates
    
    Supports both Chinese and English output.
    """
    
    def __init__(self):
        """Initialize the quote generator."""
        logger.info("QuoteGenerator initialized")
        
        # Translations for Chinese and English
        self.translations = {
            'en': {
                'title': 'AWS Pricing Quote',
                'quote_id': 'Quote ID',
                'created_date': 'Created Date',
                'status': 'Status',
                'region': 'Primary Region',
                'original_services': 'Original Service Configuration',
                'aws_mappings': 'AWS Service Mappings',
                'pricing_breakdown': 'Pricing Breakdown',
                'service': 'Service',
                'provider': 'Provider',
                'type': 'Type',
                'specifications': 'Specifications',
                'aws_service': 'AWS Service',
                'confidence': 'Confidence',
                'explanation': 'Explanation',
                'alternatives': 'Alternatives',
                'monthly_cost': 'Monthly Cost',
                'annual_cost': 'Annual Cost',
                'pricing_model': 'Pricing Model',
                'cost_breakdown': 'Cost Breakdown',
                'total_monthly': 'Total Monthly Cost',
                'total_annual': 'Total Annual Cost',
                'currency': 'Currency',
                'notes': 'Notes',
                'disclaimers': 'Disclaimers',
                'disclaimer_text': [
                    'This quote is an estimate based on current AWS pricing and the provided service specifications.',
                    'Actual costs may vary based on usage patterns, data transfer, and other factors.',
                    'AWS pricing is subject to change. Please verify current pricing at https://aws.amazon.com/pricing/',
                    'This quote does not include data transfer costs, support plans, or additional AWS services that may be required.',
                    'For accurate pricing, please consult with an AWS sales representative or use the AWS Pricing Calculator.'
                ],
                'service_descriptions': 'Service Descriptions',
                'benefits': 'AWS Benefits',
                'benefit_text': [
                    'Pay-as-you-go pricing with no upfront costs',
                    'Scalable infrastructure that grows with your needs',
                    'Global infrastructure with multiple regions and availability zones',
                    'Enterprise-grade security and compliance',
                    'Comprehensive monitoring and management tools',
                    '24/7 technical support options available'
                ]
            },
            'zh': {
                'title': 'AWS 定价报价单',
                'quote_id': '报价单编号',
                'created_date': '创建日期',
                'status': '状态',
                'region': '主要区域',
                'original_services': '原始服务配置',
                'aws_mappings': 'AWS 服务映射',
                'pricing_breakdown': '价格明细',
                'service': '服务',
                'provider': '提供商',
                'type': '类型',
                'specifications': '规格',
                'aws_service': 'AWS 服务',
                'confidence': '置信度',
                'explanation': '说明',
                'alternatives': '备选方案',
                'monthly_cost': '月度费用',
                'annual_cost': '年度费用',
                'pricing_model': '定价模式',
                'cost_breakdown': '费用明细',
                'total_monthly': '月度总费用',
                'total_annual': '年度总费用',
                'currency': '货币',
                'notes': '备注',
                'disclaimers': '免责声明',
                'disclaimer_text': [
                    '本报价单是基于当前 AWS 定价和提供的服务规格的估算。',
                    '实际费用可能因使用模式、数据传输和其他因素而有所不同。',
                    'AWS 定价可能会发生变化。请在 https://aws.amazon.com/pricing/ 验证当前定价。',
                    '本报价单不包括数据传输费用、支持计划或可能需要的其他 AWS 服务。',
                    '如需准确定价，请咨询 AWS 销售代表或使用 AWS 定价计算器。'
                ],
                'service_descriptions': '服务说明',
                'benefits': 'AWS 优势',
                'benefit_text': [
                    '按需付费，无需预付费用',
                    '可扩展的基础设施，随业务增长而扩展',
                    '全球基础设施，多个区域和可用区',
                    '企业级安全性和合规性',
                    '全面的监控和管理工具',
                    '提供 24/7 技术支持选项'
                ]
            }
        }
    
    def generate_quote(
        self,
        user_id: str,
        original_input: str,
        parsed_services: List[ServiceConfig],
        aws_mappings: List[AWSServiceMapping],
        pricing_results: List[PricingResult],
        region: str = 'us-east-1',
        language: str = 'en',
        notes: Optional[str] = None
    ) -> Quote:
        """
        Generate a complete quote document.
        
        Args:
            user_id: User ID who requested the quote
            original_input: Original configuration text/file content
            parsed_services: List of parsed service configurations
            aws_mappings: List of AWS service mappings
            pricing_results: List of pricing results
            region: Primary AWS region
            language: Output language ('en' or 'zh')
            notes: Optional notes
        
        Returns:
            Complete Quote object
        """
        logger.info(f"Generating quote for user {user_id} with {len(parsed_services)} services")
        
        # Validate language
        if language not in ['en', 'zh']:
            logger.warning(f"Unsupported language: {language}, defaulting to 'en'")
            language = 'en'
        
        # Convert objects to dictionaries for storage
        parsed_services_dicts = [service.to_dict() for service in parsed_services]
        aws_mappings_dicts = [mapping.to_dict() for mapping in aws_mappings]
        pricing_results_dicts = [pricing.to_dict() for pricing in pricing_results]
        
        # Create the quote
        quote = Quote.create_new(
            user_id=user_id,
            original_input=original_input,
            parsed_services=parsed_services_dicts,
            aws_mappings=aws_mappings_dicts,
            pricing_results=pricing_results_dicts,
            region=region,
            language=language,
            notes=notes
        )
        
        logger.info(f"Generated quote: {quote.quote_id}")
        return quote
    
    def get_quote_content(self, quote: Quote) -> Dict[str, Any]:
        """
        Get structured quote content for display or export.
        
        Args:
            quote: Quote object
        
        Returns:
            Dictionary with structured quote content
        """
        lang = quote.language
        t = self.translations.get(lang, self.translations['en'])
        
        # Build structured content
        content = {
            'header': {
                'title': t['title'],
                'quote_id': quote.quote_id,
                'created_date': quote.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'status': quote.status,
                'region': quote.region,
                'language': lang
            },
            'original_services': {
                'title': t['original_services'],
                'input': quote.original_input,
                'services': self._format_original_services(quote.parsed_services, t)
            },
            'aws_mappings': {
                'title': t['aws_mappings'],
                'mappings': self._format_aws_mappings(quote.aws_mappings, t)
            },
            'pricing': {
                'title': t['pricing_breakdown'],
                'items': self._format_pricing_items(quote.pricing_results, t),
                'total_monthly': {
                    'label': t['total_monthly'],
                    'value': float(quote.total_monthly_cost),
                    'currency': quote.currency
                },
                'total_annual': {
                    'label': t['total_annual'],
                    'value': float(quote.total_annual_cost),
                    'currency': quote.currency
                }
            },
            'descriptions': {
                'title': t['service_descriptions'],
                'services': self._get_service_descriptions(quote.aws_mappings, lang)
            },
            'benefits': {
                'title': t['benefits'],
                'items': t['benefit_text']
            },
            'disclaimers': {
                'title': t['disclaimers'],
                'items': t['disclaimer_text']
            },
            'notes': quote.notes
        }
        
        return content
    
    def _format_original_services(
        self,
        services: List[Dict[str, Any]],
        translations: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """Format original services for display."""
        formatted = []
        for service in services:
            formatted.append({
                'provider': service.get('provider', ''),
                'service_name': service.get('service_name', ''),
                'service_type': service.get('service_type', ''),
                'specifications': service.get('specifications', {}),
                'quantity': service.get('quantity', 1),
                'region': service.get('region', '')
            })
        return formatted
    
    def _format_aws_mappings(
        self,
        mappings: List[Dict[str, Any]],
        translations: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """Format AWS mappings for display."""
        formatted = []
        for mapping in mappings:
            formatted.append({
                'aws_service': mapping.get('aws_service', ''),
                'aws_service_category': mapping.get('aws_service_category', ''),
                'aws_service_type': mapping.get('aws_service_type', ''),
                'specifications': mapping.get('specifications', {}),
                'confidence_score': mapping.get('confidence_score', 0.0),
                'explanation': mapping.get('explanation', ''),
                'alternatives': mapping.get('alternatives', [])
            })
        return formatted
    
    def _format_pricing_items(
        self,
        pricing_results: List[Dict[str, Any]],
        translations: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """Format pricing items for display."""
        formatted = []
        for pricing in pricing_results:
            formatted.append({
                'region': pricing.get('region', ''),
                'pricing_model': pricing.get('pricing_model', ''),
                'monthly_cost': pricing.get('monthly_cost', 0.0),
                'annual_cost': pricing.get('annual_cost', 0.0),
                'breakdown': pricing.get('breakdown', {}),
                'currency': pricing.get('currency', 'USD'),
                'region_availability': pricing.get('region_availability', True)
            })
        return formatted
    
    def _get_service_descriptions(
        self,
        mappings: List[Dict[str, Any]],
        language: str
    ) -> List[Dict[str, str]]:
        """
        Get service descriptions for AWS services.
        
        Args:
            mappings: List of AWS service mappings
            language: Language code ('en' or 'zh')
        
        Returns:
            List of service descriptions
        """
        descriptions = []
        
        # Service descriptions (simplified - in production, these would come from Knowledge Base)
        service_info = {
            'EC2': {
                'en': 'Amazon Elastic Compute Cloud (EC2) provides scalable computing capacity in the AWS cloud.',
                'zh': 'Amazon Elastic Compute Cloud (EC2) 在 AWS 云中提供可扩展的计算容量。'
            },
            'S3': {
                'en': 'Amazon Simple Storage Service (S3) is an object storage service offering industry-leading scalability, data availability, security, and performance.',
                'zh': 'Amazon Simple Storage Service (S3) 是一种对象存储服务，提供行业领先的可扩展性、数据可用性、安全性和性能。'
            },
            'RDS': {
                'en': 'Amazon Relational Database Service (RDS) makes it easy to set up, operate, and scale a relational database in the cloud.',
                'zh': 'Amazon Relational Database Service (RDS) 使在云中设置、操作和扩展关系数据库变得容易。'
            },
            'Lambda': {
                'en': 'AWS Lambda is a serverless compute service that runs your code in response to events and automatically manages the underlying compute resources.',
                'zh': 'AWS Lambda 是一种无服务器计算服务，可响应事件运行代码并自动管理底层计算资源。'
            },
            'DynamoDB': {
                'en': 'Amazon DynamoDB is a fully managed NoSQL database service that provides fast and predictable performance with seamless scalability.',
                'zh': 'Amazon DynamoDB 是一种完全托管的 NoSQL 数据库服务，可提供快速且可预测的性能以及无缝扩展性。'
            },
            'CloudFront': {
                'en': 'Amazon CloudFront is a fast content delivery network (CDN) service that securely delivers data, videos, applications, and APIs to customers globally.',
                'zh': 'Amazon CloudFront 是一种快速内容分发网络 (CDN) 服务，可安全地向全球客户交付数据、视频、应用程序和 API。'
            },
            'VPC': {
                'en': 'Amazon Virtual Private Cloud (VPC) lets you provision a logically isolated section of the AWS Cloud where you can launch AWS resources.',
                'zh': 'Amazon Virtual Private Cloud (VPC) 允许您在 AWS 云中预置一个逻辑隔离的部分，您可以在其中启动 AWS 资源。'
            }
        }
        
        # Get unique AWS services from mappings
        seen_services = set()
        for mapping in mappings:
            service_name = mapping.get('aws_service', '')
            if service_name and service_name not in seen_services:
                seen_services.add(service_name)
                
                # Get description for this service
                service_desc = service_info.get(service_name, {})
                description = service_desc.get(language, service_desc.get('en', ''))
                
                if description:
                    descriptions.append({
                        'service': service_name,
                        'description': description
                    })
        
        return descriptions
    
    def format_quote_text(self, quote: Quote) -> str:
        """
        Format quote as plain text.
        
        Args:
            quote: Quote object
        
        Returns:
            Formatted text string
        """
        content = self.get_quote_content(quote)
        lang = quote.language
        t = self.translations.get(lang, self.translations['en'])
        
        lines = []
        lines.append("=" * 80)
        lines.append(content['header']['title'].center(80))
        lines.append("=" * 80)
        lines.append("")
        
        # Header information
        lines.append(f"{t['quote_id']}: {content['header']['quote_id']}")
        lines.append(f"{t['created_date']}: {content['header']['created_date']}")
        lines.append(f"{t['status']}: {content['header']['status']}")
        lines.append(f"{t['region']}: {content['header']['region']}")
        lines.append("")
        
        # Original services
        lines.append("-" * 80)
        lines.append(content['original_services']['title'])
        lines.append("-" * 80)
        for i, service in enumerate(content['original_services']['services'], 1):
            lines.append(f"\n{i}. {service['provider']} - {service['service_name']}")
            lines.append(f"   {t['type']}: {service['service_type']}")
            lines.append(f"   {t['specifications']}: {service['specifications']}")
        lines.append("")
        
        # AWS mappings
        lines.append("-" * 80)
        lines.append(content['aws_mappings']['title'])
        lines.append("-" * 80)
        for i, mapping in enumerate(content['aws_mappings']['mappings'], 1):
            lines.append(f"\n{i}. {mapping['aws_service']} ({mapping['aws_service_type']})")
            lines.append(f"   {t['confidence']}: {mapping['confidence_score']:.2f}")
            lines.append(f"   {t['explanation']}: {mapping['explanation']}")
            if mapping['alternatives']:
                lines.append(f"   {t['alternatives']}: {', '.join(mapping['alternatives'])}")
        lines.append("")
        
        # Pricing
        lines.append("-" * 80)
        lines.append(content['pricing']['title'])
        lines.append("-" * 80)
        for i, item in enumerate(content['pricing']['items'], 1):
            lines.append(f"\n{i}. {t['region']}: {item['region']}")
            lines.append(f"   {t['pricing_model']}: {item['pricing_model']}")
            lines.append(f"   {t['monthly_cost']}: {item['monthly_cost']:.2f} {item['currency']}")
            lines.append(f"   {t['annual_cost']}: {item['annual_cost']:.2f} {item['currency']}")
        lines.append("")
        lines.append(f"{t['total_monthly']}: {content['pricing']['total_monthly']['value']:.2f} {content['pricing']['total_monthly']['currency']}")
        lines.append(f"{t['total_annual']}: {content['pricing']['total_annual']['value']:.2f} {content['pricing']['total_annual']['currency']}")
        lines.append("")
        
        # Service descriptions
        if content['descriptions']['services']:
            lines.append("-" * 80)
            lines.append(content['descriptions']['title'])
            lines.append("-" * 80)
            for desc in content['descriptions']['services']:
                lines.append(f"\n{desc['service']}:")
                lines.append(f"  {desc['description']}")
            lines.append("")
        
        # Benefits
        lines.append("-" * 80)
        lines.append(content['benefits']['title'])
        lines.append("-" * 80)
        for benefit in content['benefits']['items']:
            lines.append(f"• {benefit}")
        lines.append("")
        
        # Disclaimers
        lines.append("-" * 80)
        lines.append(content['disclaimers']['title'])
        lines.append("-" * 80)
        for disclaimer in content['disclaimers']['items']:
            lines.append(f"• {disclaimer}")
        lines.append("")
        
        # Notes
        if content['notes']:
            lines.append("-" * 80)
            lines.append(t['notes'])
            lines.append("-" * 80)
            lines.append(content['notes'])
            lines.append("")
        
        lines.append("=" * 80)
        
        return "\n".join(lines)
    
    def validate_quote_completeness(self, quote: Quote) -> tuple[bool, List[str]]:
        """
        Validate that a quote contains all required information.
        
        Args:
            quote: Quote object to validate
        
        Returns:
            Tuple of (is_valid, list of missing items)
        """
        missing = []
        
        # Check required fields
        if not quote.quote_id:
            missing.append("quote_id")
        
        if not quote.user_id:
            missing.append("user_id")
        
        if not quote.original_input:
            missing.append("original_input")
        
        if not quote.parsed_services:
            missing.append("parsed_services")
        
        if not quote.aws_mappings:
            missing.append("aws_mappings")
        
        if not quote.pricing_results:
            missing.append("pricing_results")
        
        if quote.total_monthly_cost < 0:
            missing.append("valid total_monthly_cost")
        
        if quote.total_annual_cost < 0:
            missing.append("valid total_annual_cost")
        
        # Check that each parsed service has a corresponding mapping and pricing
        if len(quote.parsed_services) != len(quote.aws_mappings):
            missing.append("matching number of services and mappings")
        
        if len(quote.parsed_services) != len(quote.pricing_results):
            missing.append("matching number of services and pricing results")
        
        is_valid = len(missing) == 0
        
        if not is_valid:
            logger.warning(f"Quote {quote.quote_id} is incomplete. Missing: {missing}")
        
        return is_valid, missing
