"""
Script to set up S3 bucket for Bedrock Knowledge Base and upload initial content.

This script:
1. Creates an S3 bucket for Knowledge Base data source
2. Uploads all JSON files from knowledge_base/ directory
3. Sets appropriate permissions and configurations
"""

import os
import json
import boto3
from botocore.exceptions import ClientError
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class KnowledgeBaseS3Setup:
    """Setup S3 bucket for Bedrock Knowledge Base."""
    
    def __init__(self):
        """Initialize S3 client and configuration."""
        self.s3_client = boto3.client('s3', region_name=settings.AWS_REGION)
        self.bucket_name = settings.KNOWLEDGE_BASE_BUCKET_NAME
        self.knowledge_base_dir = Path(__file__).parent.parent / 'knowledge_base'
        
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
            if settings.AWS_REGION == 'us-east-1':
                # us-east-1 doesn't need LocationConstraint
                self.s3_client.create_bucket(Bucket=self.bucket_name)
            else:
                self.s3_client.create_bucket(
                    Bucket=self.bucket_name,
                    CreateBucketConfiguration={'LocationConstraint': settings.AWS_REGION}
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
    setup = KnowledgeBaseS3Setup()
    
    if setup.setup():
        print("\n✅ Knowledge Base S3 setup completed successfully!")
        print(f"Bucket name: {setup.bucket_name}")
        print(f"Region: {settings.AWS_REGION}")
        print("\nNext steps:")
        print("1. Create Bedrock Knowledge Base in AWS Console")
        print("2. Configure Knowledge Base to use this S3 bucket as data source")
        print("3. Run sync to index the content")
    else:
        print("\n❌ Knowledge Base S3 setup failed. Check logs for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
