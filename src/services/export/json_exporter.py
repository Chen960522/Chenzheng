"""JSON export service for quotes."""

import json
import io
from typing import Dict, Any
from datetime import datetime
import boto3
from botocore.exceptions import ClientError

from ...models.quote import Quote
from ...utils.logger import get_logger

logger = get_logger(__name__)


class JSONExporter:
    """
    Service for exporting quotes to JSON format.
    
    Serializes quote data to JSON format.
    Uploads to S3 and generates presigned URLs for download.
    """
    
    def __init__(self, s3_client=None, bucket_name: str = 'aws-pricing-quotes'):
        """
        Initialize the JSON exporter.
        
        Args:
            s3_client: Boto3 S3 client (optional, will create if not provided)
            bucket_name: S3 bucket name for storing JSON files
        """
        self.s3_client = s3_client or boto3.client('s3')
        self.bucket_name = bucket_name
        logger.info(f"JSONExporter initialized with bucket: {bucket_name}")
    
    def export_quote(
        self,
        quote: Quote,
        quote_content: Dict[str, Any],
        upload_to_s3: bool = True,
        pretty_print: bool = True
    ) -> str:
        """
        Export quote to JSON format.
        
        Args:
            quote: Quote object
            quote_content: Structured quote content from QuoteGenerator
            upload_to_s3: Whether to upload to S3 (default: True)
            pretty_print: Whether to format JSON with indentation (default: True)
        
        Returns:
            S3 presigned URL if uploaded, or local file path
        """
        logger.info(f"Exporting quote {quote.quote_id} to JSON")
        
        # Generate JSON
        json_data = self._generate_json(quote, quote_content, pretty_print)
        json_buffer = io.BytesIO(json_data.encode('utf-8'))
        
        if upload_to_s3:
            # Upload to S3 and get presigned URL
            s3_key = f"quotes/{quote.user_id}/{quote.quote_id}.json"
            url = self._upload_to_s3(json_buffer, s3_key)
            logger.info(f"JSON uploaded to S3: {s3_key}")
            return url
        else:
            # Save to local file
            filename = f"quote_{quote.quote_id}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(json_data)
            logger.info(f"JSON saved locally: {filename}")
            return filename
    
    def _generate_json(
        self,
        quote: Quote,
        content: Dict[str, Any],
        pretty_print: bool
    ) -> str:
        """
        Generate JSON string from quote data.
        
        Args:
            quote: Quote object
            content: Structured quote content
            pretty_print: Whether to format with indentation
        
        Returns:
            JSON string
        """
        # Build complete JSON structure
        json_data = {
            'quote_metadata': {
                'quote_id': quote.quote_id,
                'user_id': quote.user_id,
                'created_at': quote.created_at.isoformat(),
                'updated_at': quote.updated_at.isoformat(),
                'status': quote.status,
                'language': quote.language,
                'region': quote.region,
                'currency': quote.currency
            },
            'original_input': quote.original_input,
            'original_services': content['original_services']['services'],
            'aws_mappings': content['aws_mappings']['mappings'],
            'pricing': {
                'items': content['pricing']['items'],
                'total_monthly_cost': content['pricing']['total_monthly']['value'],
                'total_annual_cost': content['pricing']['total_annual']['value'],
                'currency': content['pricing']['total_monthly']['currency']
            },
            'service_descriptions': content['descriptions']['services'],
            'benefits': content['benefits']['items'],
            'disclaimers': content['disclaimers']['items'],
            'notes': content['notes'],
            'export_urls': quote.export_urls
        }
        
        # Serialize to JSON
        if pretty_print:
            return json.dumps(json_data, indent=2, ensure_ascii=False)
        else:
            return json.dumps(json_data, ensure_ascii=False)
    
    def _upload_to_s3(self, buffer: io.BytesIO, s3_key: str) -> str:
        """
        Upload JSON to S3 and generate presigned URL.
        
        Args:
            buffer: JSON buffer
            s3_key: S3 object key
        
        Returns:
            Presigned URL for download
        """
        try:
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=buffer.getvalue(),
                ContentType='application/json',
                ServerSideEncryption='AES256'
            )
            
            # Generate presigned URL (valid for 7 days)
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': s3_key
                },
                ExpiresIn=604800  # 7 days
            )
            
            return url
        except ClientError as e:
            logger.error(f"Failed to upload JSON to S3: {e}")
            raise
    
    def export_quote_raw(self, quote: Quote, pretty_print: bool = True) -> str:
        """
        Export quote as raw JSON (just the Quote object data).
        
        Args:
            quote: Quote object
            pretty_print: Whether to format with indentation
        
        Returns:
            JSON string
        """
        json_data = quote.to_dict()
        
        if pretty_print:
            return json.dumps(json_data, indent=2, ensure_ascii=False, default=str)
        else:
            return json.dumps(json_data, ensure_ascii=False, default=str)
    
    def parse_json_quote(self, json_str: str) -> Quote:
        """
        Parse JSON string back to Quote object.
        
        Args:
            json_str: JSON string
        
        Returns:
            Quote object
        """
        try:
            data = json.loads(json_str)
            return Quote.from_dict(data)
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Failed to parse JSON quote: {e}")
            raise ValueError(f"Invalid quote JSON: {e}")
