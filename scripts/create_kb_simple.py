"""
简化的 Bedrock Knowledge Base 创建脚本

根据 AWS Bedrock 官方文档最佳实践：
- 让 Bedrock 自动创建和管理 OpenSearch Serverless 集合
- 让 Bedrock 自动创建服务角色
- 简化配置，减少手动步骤

Compatible with Python 3.12+
"""

import os
import sys
import time
import logging
from pathlib import Path
from typing import Dict, Optional

import boto3
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def load_config() -> dict:
    """Load configuration from environment variables or .env file."""
    config = {
        'aws_region': os.getenv('AWS_REGION', 'us-east-1'),
        'bucket_name': os.getenv('S3_KNOWLEDGE_BASE_BUCKET', 'aws-pricing-assistant-kb-data'),
        'embedding_model_id': os.getenv('BEDROCK_EMBEDDING_MODEL_ID', 'amazon.titan-embed-text-v2:0'),
    }
    
    # Try to load from .env file
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
                        elif key == 'bedrock_embedding_model_id':
                            config['embedding_model_id'] = value
            logger.info(f"Loaded configuration from {env_file}")
        except Exception as e:
            logger.warning(f"Could not load .env file: {e}")
    
    return config


def create_knowledge_base(config: dict) -> Dict[str, str]:
    """
    Create Bedrock Knowledge Base with auto-managed OpenSearch Serverless.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        dict: Created resource information
    """
    bedrock_agent = boto3.client('bedrock-agent', region_name=config['aws_region'])
    
    kb_name = "aws-pricing-assistant-kb"
    kb_description = "Knowledge Base for AWS Pricing Assistant"
    
    try:
        logger.info("Creating Knowledge Base (Bedrock will auto-create OpenSearch collection)...")
        
        # Create Knowledge Base - let Bedrock handle everything
        response = bedrock_agent.create_knowledge_base(
            name=kb_name,
            description=kb_description,
            # Let Bedrock create and manage the service role
            roleArn='',  # Empty string tells Bedrock to create role automatically
            knowledgeBaseConfiguration={
                'type': 'VECTOR',
                'vectorKnowledgeBaseConfiguration': {
                    'embeddingModelArn': f"arn:aws:bedrock:{config['aws_region']}::foundation-model/{config['embedding_model_id']}"
                }
            },
            storageConfiguration={
                'type': 'OPENSEARCH_SERVERLESS',
                'opensearchServerlessConfiguration': {
                    # Let Bedrock create the collection automatically
                    'collectionArn': '',  # Empty means auto-create
                    'vectorIndexName': 'bedrock-knowledge-base-default-index',
                    'fieldMapping': {
                        'vectorField': 'bedrock-knowledge-base-default-vector',
                        'textField': 'AMAZON_BEDROCK_TEXT_CHUNK',
                        'metadataField': 'AMAZON_BEDROCK_METADATA'
                    }
                }
            }
        )
        
        kb_id = response['knowledgeBase']['knowledgeBaseId']
        kb_arn = response['knowledgeBase']['knowledgeBaseArn']
        role_arn = response['knowledgeBase']['roleArn']
        
        logger.info(f"✅ Knowledge Base created: {kb_id}")
        logger.info(f"   ARN: {kb_arn}")
        logger.info(f"   Service Role: {role_arn}")
        
        # Wait for Knowledge Base to be ready
        logger.info("Waiting for Knowledge Base to be ready...")
        max_wait = 300
        wait_interval = 10
        elapsed = 0
        
        while elapsed < max_wait:
            kb_response = bedrock_agent.get_knowledge_base(knowledgeBaseId=kb_id)
            status = kb_response['knowledgeBase']['status']
            
            if status == 'ACTIVE':
                logger.info("✅ Knowledge Base is ACTIVE")
                break
            elif status == 'FAILED':
                raise Exception("Knowledge Base creation failed")
            
            logger.info(f"   Status: {status}, waiting... ({elapsed}s)")
            time.sleep(wait_interval)
            elapsed += wait_interval
        
        return {
            'knowledge_base_id': kb_id,
            'knowledge_base_arn': kb_arn,
            'role_arn': role_arn
        }
        
    except ClientError as e:
        logger.error(f"Error creating Knowledge Base: {e}")
        raise


def create_data_source(kb_id: str, config: dict) -> str:
    """
    Create S3 data source for Knowledge Base.
    
    Args:
        kb_id: Knowledge Base ID
        config: Configuration dictionary
        
    Returns:
        str: Data source ID
    """
    bedrock_agent = boto3.client('bedrock-agent', region_name=config['aws_region'])
    
    try:
        logger.info("Creating S3 data source...")
        
        response = bedrock_agent.create_data_source(
            knowledgeBaseId=kb_id,
            name='s3-pricing-data',
            description='S3 bucket containing AWS pricing and service mapping data',
            dataSourceConfiguration={
                'type': 'S3',
                's3Configuration': {
                    'bucketArn': f"arn:aws:s3:::{config['bucket_name']}"
                }
            },
            vectorIngestionConfiguration={
                'chunkingConfiguration': {
                    'chunkingStrategy': 'FIXED_SIZE',
                    'fixedSizeChunkingConfiguration': {
                        'maxTokens': 512,
                        'overlapPercentage': 20
                    }
                }
            }
        )
        
        data_source_id = response['dataSource']['dataSourceId']
        logger.info(f"✅ Data source created: {data_source_id}")
        
        return data_source_id
        
    except ClientError as e:
        logger.error(f"Error creating data source: {e}")
        raise


def start_ingestion(kb_id: str, data_source_id: str, config: dict) -> str:
    """
    Start data ingestion job.
    
    Args:
        kb_id: Knowledge Base ID
        data_source_id: Data source ID
        config: Configuration dictionary
        
    Returns:
        str: Ingestion job ID
    """
    bedrock_agent = boto3.client('bedrock-agent', region_name=config['aws_region'])
    
    try:
        logger.info("Starting data ingestion...")
        
        response = bedrock_agent.start_ingestion_job(
            knowledgeBaseId=kb_id,
            dataSourceId=data_source_id
        )
        
        job_id = response['ingestionJob']['ingestionJobId']
        logger.info(f"✅ Ingestion job started: {job_id}")
        
        # Monitor ingestion progress
        logger.info("Monitoring ingestion progress...")
        max_wait = 600
        wait_interval = 15
        elapsed = 0
        
        while elapsed < max_wait:
            job_response = bedrock_agent.get_ingestion_job(
                knowledgeBaseId=kb_id,
                dataSourceId=data_source_id,
                ingestionJobId=job_id
            )
            
            status = job_response['ingestionJob']['status']
            stats = job_response['ingestionJob'].get('statistics', {})
            
            if status == 'COMPLETE':
                logger.info("✅ Ingestion completed successfully")
                logger.info(f"   Documents processed: {stats.get('numberOfDocumentsScanned', 0)}")
                logger.info(f"   Documents indexed: {stats.get('numberOfNewDocumentsIndexed', 0)}")
                return job_id
            elif status == 'FAILED':
                failures = job_response['ingestionJob'].get('failureReasons', [])
                raise Exception(f"Ingestion failed: {failures}")
            
            logger.info(f"   Status: {status}, waiting... ({elapsed}s)")
            time.sleep(wait_interval)
            elapsed += wait_interval
        
        logger.warning("Ingestion still running after timeout")
        return job_id
        
    except ClientError as e:
        logger.error(f"Error during ingestion: {e}")
        raise


def main():
    """Main function."""
    print("=" * 70)
    print("AWS Pricing Assistant - Bedrock Knowledge Base Setup (Simplified)")
    print("=" * 70)
    print()
    
    # Load configuration
    config = load_config()
    print(f"Configuration:")
    print(f"  AWS Region: {config['aws_region']}")
    print(f"  S3 Bucket: {config['bucket_name']}")
    print(f"  Embedding Model: {config['embedding_model_id']}")
    print()
    
    # Verify AWS credentials
    try:
        sts = boto3.client('sts', region_name=config['aws_region'])
        identity = sts.get_caller_identity()
        print(f"AWS Identity:")
        print(f"  Account: {identity['Account']}")
        print(f"  User/Role: {identity['Arn'].split('/')[-1]}")
        print()
    except Exception as e:
        print(f"⚠️  Warning: Could not verify AWS credentials: {e}")
        print()
    
    # Confirm
    print("⚠️  This script will:")
    print("  - Create a Bedrock Knowledge Base")
    print("  - Auto-create OpenSearch Serverless collection (managed by Bedrock)")
    print("  - Auto-create IAM service role (managed by Bedrock)")
    print("  - Create S3 data source")
    print("  - Start data ingestion")
    print()
    print("💰 Estimated cost: $50-100/month for OpenSearch Serverless")
    print()
    
    response = input("Continue? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("Setup cancelled.")
        sys.exit(0)
    
    print()
    print("Starting setup...")
    print()
    
    try:
        # Create Knowledge Base
        kb_info = create_knowledge_base(config)
        print()
        
        # Create Data Source
        data_source_id = create_data_source(kb_info['knowledge_base_id'], config)
        print()
        
        # Start Ingestion
        job_id = start_ingestion(kb_info['knowledge_base_id'], data_source_id, config)
        print()
        
        # Success
        print("=" * 70)
        print("✅ Setup completed successfully!")
        print("=" * 70)
        print()
        print(f"Knowledge Base ID: {kb_info['knowledge_base_id']}")
        print(f"Data Source ID: {data_source_id}")
        print(f"Ingestion Job ID: {job_id}")
        print()
        print("Next steps:")
        print(f"1. Update .env file:")
        print(f"   BEDROCK_KNOWLEDGE_BASE_ID={kb_info['knowledge_base_id']}")
        print("2. Test Knowledge Base queries")
        print("3. Integrate with your application")
        print()
        
    except Exception as e:
        print()
        print("=" * 70)
        print("❌ Setup failed")
        print("=" * 70)
        print()
        print(f"Error: {e}")
        print()
        sys.exit(1)


if __name__ == "__main__":
    main()
