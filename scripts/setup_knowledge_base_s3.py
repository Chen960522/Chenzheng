"""
Script to set up S3 bucket for Bedrock Knowledge Base and upload initial content.

This script:
1. Creates an S3 bucket for Knowledge Base data source
2. Uploads all JSON files from knowledge_base/ directory
3. Sets appropriate permissions and configurations

Compatible with Python 3.14+
"""

import os
import json
import sys
import logging
from pathlib import Path
from typing import List, Optional

import boto3
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def load_config() -> dict:
    """
    Load configuration from environment variables or .env file.
    
    Returns:
        dict: Configuration dictionary
    """
    config = {
        'aws_region': os.getenv('AWS_REGION', 'us-east-1'),
        'bucket_name': os.getenv('S3_KNOWLEDGE_BASE_BUCKET', 'aws-pricing-assistant-kb-data'),
    }
    
    # Try to load from .env file if exists
    env_file = Path(__file__).parent.parent / '.env'
    if env_file.exists():
        try:
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip().lower()
                        value = value.strip().strip('"').strip("'")
                        
                        if key == 'aws_region':
                            config['aws_region'] = value
                        elif key == 's3_knowledge_base_bucket':
                            config['bucket_name'] = value
            logger.info(f"Loaded configuration from {env_file}")
        except Exception as e:
            logger.warning(f"Could not load .env file: {e}")
    
    return config


class KnowledgeBaseS3Setup:
    """Setup S3 bucket for Bedrock Knowledge Base."""
    
    def __init__(self, config: Optional[dict] = None):
        """
        Initialize S3 client and configuration.
        
        Args:
            config: Configuration dictionary (optional)
        """
        if config is None:
            config = load_config()
        
        self.config = config
        self.aws_region = config['aws_region']
        self.bucket_name = config['bucket_name']
        self.s3_client = boto3.client('s3', region_name=self.aws_region)
        self.knowledge_base_dir = Path(__file__).parent.parent / 'knowledge_base'
        
        logger.info(f"Initialized with bucket: {self.bucket_name}, region: {self.aws_region}")
        
    def create_bucket(self) -> bool:
        """
        Create S3 bucket for Knowledge Base.
        
        Returns:
            bool: True if bucket created or already exists, False otherwise
        """
        try:
            # Check if bucket already exists
            try:
                self.s3_client.head_bucket(Bucket=self.bucket_name)
                logger.info(f"Bucket {self.bucket_name} already exists")
                return True
            except ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code != '404':
                    raise
            
            # Create bucket
            if self.aws_region == 'us-east-1':
                # us-east-1 doesn't need LocationConstraint
                self.s3_client.create_bucket(Bucket=self.bucket_name)
            else:
                self.s3_client.create_bucket(
                    Bucket=self.bucket_name,
                    CreateBucketConfiguration={'LocationConstraint': self.aws_region}
                )
            
            logger.info(f"Created bucket: {self.bucket_name}")
            
            # Enable versioning
            self.s3_client.put_bucket_versioning(
                Bucket=self.bucket_name,
                VersioningConfiguration={'Status': 'Enabled'}
            )
            logger.info(f"Enabled versioning for bucket: {self.bucket_name}")
            
            # Enable server-side encryption
            self.s3_client.put_bucket_encryption(
                Bucket=self.bucket_name,
                ServerSideEncryptionConfiguration={
                    'Rules': [
                        {
                            'ApplyServerSideEncryptionByDefault': {
                                'SSEAlgorithm': 'AES256'
                            },
                            'BucketKeyEnabled': True
                        }
                    ]
                }
            )
            logger.info(f"Enabled encryption for bucket: {self.bucket_name}")
            
            # Block public access
            self.s3_client.put_public_access_block(
                Bucket=self.bucket_name,
                PublicAccessBlockConfiguration={
                    'BlockPublicAcls': True,
                    'IgnorePublicAcls': True,
                    'BlockPublicPolicy': True,
                    'RestrictPublicBuckets': True
                }
            )
            logger.info(f"Blocked public access for bucket: {self.bucket_name}")
            
            return True
            
        except ClientError as e:
            logger.error(f"Error creating bucket: {e}")
            return False
    
    def upload_knowledge_base_content(self) -> bool:
        """
        Upload all Knowledge Base content to S3.
        
        Returns:
            bool: True if all files uploaded successfully, False otherwise
        """
        try:
            if not self.knowledge_base_dir.exists():
                logger.error(f"Knowledge base directory not found: {self.knowledge_base_dir}")
                return False
            
            uploaded_count = 0
            failed_count = 0
            
            # Walk through all subdirectories and upload JSON files
            for root, dirs, files in os.walk(self.knowledge_base_dir):
                for file in files:
                    if file.endswith('.json') or file.endswith('.md'):
                        local_path = Path(root) / file
                        
                        # Create S3 key (relative path from knowledge_base directory)
                        relative_path = local_path.relative_to(self.knowledge_base_dir)
                        s3_key = str(relative_path).replace('\\', '/')
                        
                        try:
                            # Upload file
                            self.s3_client.upload_file(
                                str(local_path),
                                self.bucket_name,
                                s3_key,
                                ExtraArgs={
                                    'ContentType': 'application/json' if file.endswith('.json') else 'text/markdown'
                                }
                            )
                            logger.info(f"Uploaded: {s3_key}")
                            uploaded_count += 1
                            
                        except ClientError as e:
                            logger.error(f"Error uploading {s3_key}: {e}")
                            failed_count += 1
            
            logger.info(f"Upload complete: {uploaded_count} files uploaded, {failed_count} failed")
            return failed_count == 0
            
        except Exception as e:
            logger.error(f"Error uploading knowledge base content: {e}")
            return False
    
    def list_uploaded_files(self) -> list:
        """
        List all files in the Knowledge Base S3 bucket.
        
        Returns:
            list: List of S3 object keys
        """
        try:
            response = self.s3_client.list_objects_v2(Bucket=self.bucket_name)
            
            if 'Contents' not in response:
                logger.info("No files found in bucket")
                return []
            
            files = [obj['Key'] for obj in response['Contents']]
            logger.info(f"Found {len(files)} files in bucket:")
            for file in files:
                logger.info(f"  - {file}")
            
            return files
            
        except ClientError as e:
            logger.error(f"Error listing files: {e}")
            return []
    
    def setup(self) -> bool:
        """
        Complete setup: create bucket and upload content.
        
        Returns:
            bool: True if setup successful, False otherwise
        """
        logger.info("Starting Knowledge Base S3 setup...")
        
        # Create bucket
        if not self.create_bucket():
            logger.error("Failed to create bucket")
            return False
        
        # Upload content
        if not self.upload_knowledge_base_content():
            logger.error("Failed to upload content")
            return False
        
        # List uploaded files
        self.list_uploaded_files()
        
        logger.info("Knowledge Base S3 setup complete!")
        return True


def main():
    """Main function to run the setup."""
    print("=" * 60)
    print("AWS Pricing Assistant - Knowledge Base S3 Setup")
    print("=" * 60)
    print()
    
    # Load configuration
    config = load_config()
    print(f"Configuration:")
    print(f"  AWS Region: {config['aws_region']}")
    print(f"  S3 Bucket: {config['bucket_name']}")
    print()
    
    # Check AWS credentials
    try:
        sts = boto3.client('sts', region_name=config['aws_region'])
        identity = sts.get_caller_identity()
        print(f"AWS Identity:")
        print(f"  Account: {identity['Account']}")
        print(f"  User/Role: {identity['Arn'].split('/')[-1]}")
        print()
    except Exception as e:
        print(f"⚠️  Warning: Could not verify AWS credentials: {e}")
        print("Please ensure AWS credentials are configured.")
        print()
    
    # Run setup
    setup = KnowledgeBaseS3Setup(config)
    
    if setup.setup():
        print()
        print("=" * 60)
        print("✅ Knowledge Base S3 setup completed successfully!")
        print("=" * 60)
        print()
        print(f"Bucket name: {setup.bucket_name}")
        print(f"Region: {setup.aws_region}")
        print()
        print("Next steps:")
        print("1. Create Bedrock Knowledge Base in AWS Console")
        print("2. Configure Knowledge Base to use this S3 bucket as data source")
        print("3. Run sync to index the content")
        print()
    else:
        print()
        print("=" * 60)
        print("❌ Knowledge Base S3 setup failed")
        print("=" * 60)
        print()
        print("Check the logs above for details.")
        print()
        sys.exit(1)


if __name__ == "__main__":
    main()
