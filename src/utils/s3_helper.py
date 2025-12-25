"""S3 helper utilities with encryption support."""

from typing import Optional, BinaryIO
import os
from pathlib import Path

from src.config.aws_clients import aws_clients
from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class S3Helper:
    """
    Helper class for S3 operations with server-side encryption.
    
    All uploads automatically use server-side encryption (SSE-S3 or SSE-KMS).
    """
    
    def __init__(self, bucket_name: Optional[str] = None):
        """
        Initialize S3 helper.
        
        Args:
            bucket_name: S3 bucket name (defaults to settings.s3_bucket_name)
        """
        self.bucket_name = bucket_name or settings.s3_bucket_name
        self.s3_client = aws_clients.s3
        self.encryption_type = os.getenv("S3_ENCRYPTION_TYPE", "AES256")  # AES256 or aws:kms
        self.kms_key_id = os.getenv("S3_KMS_KEY_ID")  # Optional KMS key ID
    
    def upload_file(
        self,
        file_path: Path,
        s3_key: str,
        content_type: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> str:
        """
        Upload a file to S3 with server-side encryption.
        
        Args:
            file_path: Path to local file
            s3_key: S3 object key
            content_type: Optional content type
            metadata: Optional metadata dict
        
        Returns:
            S3 object URL
        """
        try:
            extra_args = {
                'ServerSideEncryption': self.encryption_type
            }
            
            # Add KMS key if using KMS encryption
            if self.encryption_type == 'aws:kms' and self.kms_key_id:
                extra_args['SSEKMSKeyId'] = self.kms_key_id
            
            # Add content type if provided
            if content_type:
                extra_args['ContentType'] = content_type
            
            # Add metadata if provided
            if metadata:
                extra_args['Metadata'] = metadata
            
            # Upload file
            self.s3_client.upload_file(
                str(file_path),
                self.bucket_name,
                s3_key,
                ExtraArgs=extra_args
            )
            
            logger.info(f"Uploaded file to S3: s3://{self.bucket_name}/{s3_key}")
            
            return f"s3://{self.bucket_name}/{s3_key}"
        
        except Exception as e:
            logger.error(f"Failed to upload file to S3: {e}")
            raise
    
    def upload_fileobj(
        self,
        file_obj: BinaryIO,
        s3_key: str,
        content_type: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> str:
        """
        Upload a file object to S3 with server-side encryption.
        
        Args:
            file_obj: File-like object
            s3_key: S3 object key
            content_type: Optional content type
            metadata: Optional metadata dict
        
        Returns:
            S3 object URL
        """
        try:
            extra_args = {
                'ServerSideEncryption': self.encryption_type
            }
            
            # Add KMS key if using KMS encryption
            if self.encryption_type == 'aws:kms' and self.kms_key_id:
                extra_args['SSEKMSKeyId'] = self.kms_key_id
            
            # Add content type if provided
            if content_type:
                extra_args['ContentType'] = content_type
            
            # Add metadata if provided
            if metadata:
                extra_args['Metadata'] = metadata
            
            # Upload file object
            self.s3_client.upload_fileobj(
                file_obj,
                self.bucket_name,
                s3_key,
                ExtraArgs=extra_args
            )
            
            logger.info(f"Uploaded file object to S3: s3://{self.bucket_name}/{s3_key}")
            
            return f"s3://{self.bucket_name}/{s3_key}"
        
        except Exception as e:
            logger.error(f"Failed to upload file object to S3: {e}")
            raise
    
    def generate_presigned_url(
        self,
        s3_key: str,
        expiration: int = 3600
    ) -> str:
        """
        Generate a presigned URL for downloading an S3 object.
        
        Args:
            s3_key: S3 object key
            expiration: URL expiration time in seconds (default: 1 hour)
        
        Returns:
            Presigned URL
        """
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': s3_key
                },
                ExpiresIn=expiration
            )
            
            logger.debug(f"Generated presigned URL for s3://{self.bucket_name}/{s3_key}")
            
            return url
        
        except Exception as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            raise
    
    def delete_object(self, s3_key: str):
        """
        Delete an object from S3.
        
        Args:
            s3_key: S3 object key
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            
            logger.info(f"Deleted S3 object: s3://{self.bucket_name}/{s3_key}")
        
        except Exception as e:
            logger.error(f"Failed to delete S3 object: {e}")
            raise
    
    def ensure_bucket_encryption(self):
        """
        Ensure the S3 bucket has default encryption enabled.
        
        This sets up default encryption for all objects in the bucket.
        """
        try:
            encryption_config = {
                'Rules': [
                    {
                        'ApplyServerSideEncryptionByDefault': {
                            'SSEAlgorithm': self.encryption_type
                        },
                        'BucketKeyEnabled': True
                    }
                ]
            }
            
            # Add KMS key if using KMS encryption
            if self.encryption_type == 'aws:kms' and self.kms_key_id:
                encryption_config['Rules'][0]['ApplyServerSideEncryptionByDefault']['KMSMasterKeyID'] = self.kms_key_id
            
            self.s3_client.put_bucket_encryption(
                Bucket=self.bucket_name,
                ServerSideEncryptionConfiguration=encryption_config
            )
            
            logger.info(f"Enabled default encryption for bucket: {self.bucket_name}")
        
        except Exception as e:
            logger.error(f"Failed to enable bucket encryption: {e}")
            raise


def get_s3_helper(bucket_name: Optional[str] = None) -> S3Helper:
    """
    Get S3 helper instance.
    
    Args:
        bucket_name: Optional bucket name (defaults to settings.s3_bucket_name)
    
    Returns:
        S3Helper instance
    """
    return S3Helper(bucket_name)
