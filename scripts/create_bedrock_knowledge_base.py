"""
Script to create and configure Bedrock Knowledge Base.

This script:
1. Creates an OpenSearch Serverless collection for vector storage
2. Creates a Bedrock Knowledge Base
3. Configures S3 as the data source
4. Sets up the embedding model
5. Syncs the Knowledge Base with S3 data
"""

import os
import sys
import time
import json
import boto3
from botocore.exceptions import ClientError

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class BedrockKnowledgeBaseSetup:
    """Setup Bedrock Knowledge Base with OpenSearch Serverless."""
    
    def __init__(self):
        """Initialize AWS clients."""
        self.bedrock_agent_client = boto3.client('bedrock-agent', region_name=settings.aws_region)
        self.iam_client = boto3.client('iam', region_name=settings.aws_region)
        self.aoss_client = boto3.client('opensearchserverless', region_name=settings.aws_region)
        
        self.kb_name = "aws-pricing-assistant-kb"
        self.kb_description = "Knowledge Base for AWS Pricing Assistant containing service mappings, pricing data, and AWS service descriptions"
        self.collection_name = "aws-pricing-kb-collection"
        self.index_name = "aws-pricing-kb-index"
        
    def create_iam_role_for_kb(self) -> str:
        """
        Create IAM role for Bedrock Knowledge Base.
        
        Returns:
            str: ARN of the created role
        """
        role_name = "AWSPricingAssistantKBRole"
        
        try:
            # Check if role already exists
            try:
                response = self.iam_client.get_role(RoleName=role_name)
                logger.info(f"IAM role {role_name} already exists")
                return response['Role']['Arn']
            except ClientError as e:
                if e.response['Error']['Code'] != 'NoSuchEntity':
                    raise
            
            # Create trust policy
            trust_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {
                            "Service": "bedrock.amazonaws.com"
                        },
                        "Action": "sts:AssumeRole"
                    }
                ]
            }
            
            # Create role
            response = self.iam_client.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(trust_policy),
                Description="Role for AWS Pricing Assistant Bedrock Knowledge Base"
            )
            role_arn = response['Role']['Arn']
            logger.info(f"Created IAM role: {role_arn}")
            
            # Attach policies
            policies = [
                {
                    "PolicyName": "KBBedrockPolicy",
                    "PolicyDocument": {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Effect": "Allow",
                                "Action": [
                                    "bedrock:InvokeModel"
                                ],
                                "Resource": f"arn:aws:bedrock:{settings.aws_region}::foundation-model/{settings.bedrock_embedding_model_id}"
                            }
                        ]
                    }
                },
                {
                    "PolicyName": "KBS3Policy",
                    "PolicyDocument": {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Effect": "Allow",
                                "Action": [
                                    "s3:GetObject",
                                    "s3:ListBucket"
                                ],
                                "Resource": [
                                    f"arn:aws:s3:::{settings.s3_knowledge_base_bucket}",
                                    f"arn:aws:s3:::{settings.s3_knowledge_base_bucket}/*"
                                ]
                            }
                        ]
                    }
                },
                {
                    "PolicyName": "KBOpenSearchPolicy",
                    "PolicyDocument": {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Effect": "Allow",
                                "Action": [
                                    "aoss:APIAccessAll"
                                ],
                                "Resource": f"arn:aws:aoss:{settings.aws_region}:*:collection/*"
                            }
                        ]
                    }
                }
            ]
            
            for policy in policies:
                self.iam_client.put_role_policy(
                    RoleName=role_name,
                    PolicyName=policy['PolicyName'],
                    PolicyDocument=json.dumps(policy['PolicyDocument'])
                )
                logger.info(f"Attached policy: {policy['PolicyName']}")
            
            # Wait for role to be available
            time.sleep(10)
            
            return role_arn
            
        except ClientError as e:
            logger.error(f"Error creating IAM role: {e}")
            raise
    
    def create_opensearch_collection(self) -> str:
        """
        Create OpenSearch Serverless collection.
        
        Returns:
            str: ARN of the created collection
        """
        try:
            # Check if collection already exists
            try:
                response = self.aoss_client.batch_get_collection(
                    names=[self.collection_name]
                )
                if response.get('collectionDetails'):
                    collection_arn = response['collectionDetails'][0]['arn']
                    logger.info(f"OpenSearch collection {self.collection_name} already exists")
                    return collection_arn
            except ClientError:
                pass
            
            # Create collection
            response = self.aoss_client.create_collection(
                name=self.collection_name,
                type='VECTORSEARCH',
                description='Vector store for AWS Pricing Assistant Knowledge Base'
            )
            
            collection_id = response['createCollectionDetail']['id']
            logger.info(f"Creating OpenSearch collection: {collection_id}")
            
            # Wait for collection to be active
            max_wait = 300  # 5 minutes
            wait_interval = 10
            elapsed = 0
            
            while elapsed < max_wait:
                response = self.aoss_client.batch_get_collection(ids=[collection_id])
                if response['collectionDetails']:
                    status = response['collectionDetails'][0]['status']
                    if status == 'ACTIVE':
                        collection_arn = response['collectionDetails'][0]['arn']
                        logger.info(f"OpenSearch collection is active: {collection_arn}")
                        return collection_arn
                    elif status == 'FAILED':
                        raise Exception("OpenSearch collection creation failed")
                
                logger.info(f"Waiting for collection to be active... ({elapsed}s)")
                time.sleep(wait_interval)
                elapsed += wait_interval
            
            raise Exception("Timeout waiting for OpenSearch collection to be active")
            
        except ClientError as e:
            logger.error(f"Error creating OpenSearch collection: {e}")
            raise
    
    def create_knowledge_base(self, role_arn: str, collection_arn: str) -> str:
        """
        Create Bedrock Knowledge Base.
        
        Args:
            role_arn: ARN of the IAM role
            collection_arn: ARN of the OpenSearch collection
            
        Returns:
            str: ID of the created Knowledge Base
        """
        try:
            # Extract collection endpoint from ARN
            # ARN format: arn:aws:aoss:region:account:collection/collection-id
            collection_id = collection_arn.split('/')[-1]
            collection_endpoint = f"https://{collection_id}.{settings.aws_region}.aoss.amazonaws.com"
            
            # Create Knowledge Base
            response = self.bedrock_agent_client.create_knowledge_base(
                name=self.kb_name,
                description=self.kb_description,
                roleArn=role_arn,
                knowledgeBaseConfiguration={
                    'type': 'VECTOR',
                    'vectorKnowledgeBaseConfiguration': {
                        'embeddingModelArn': f"arn:aws:bedrock:{settings.aws_region}::foundation-model/{settings.bedrock_embedding_model_id}"
                    }
                },
                storageConfiguration={
                    'type': 'OPENSEARCH_SERVERLESS',
                    'opensearchServerlessConfiguration': {
                        'collectionArn': collection_arn,
                        'vectorIndexName': self.index_name,
                        'fieldMapping': {
                            'vectorField': 'embedding',
                            'textField': 'text',
                            'metadataField': 'metadata'
                        }
                    }
                }
            )
            
            kb_id = response['knowledgeBase']['knowledgeBaseId']
            logger.info(f"Created Knowledge Base: {kb_id}")
            
            return kb_id
            
        except ClientError as e:
            logger.error(f"Error creating Knowledge Base: {e}")
            raise
    
    def create_data_source(self, kb_id: str) -> str:
        """
        Create S3 data source for Knowledge Base.
        
        Args:
            kb_id: ID of the Knowledge Base
            
        Returns:
            str: ID of the created data source
        """
        try:
            response = self.bedrock_agent_client.create_data_source(
                knowledgeBaseId=kb_id,
                name='s3-knowledge-base-data',
                description='S3 bucket containing service mappings, pricing data, and AWS service descriptions',
                dataSourceConfiguration={
                    'type': 'S3',
                    's3Configuration': {
                        'bucketArn': f"arn:aws:s3:::{settings.s3_knowledge_base_bucket}"
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
            logger.info(f"Created data source: {data_source_id}")
            
            return data_source_id
            
        except ClientError as e:
            logger.error(f"Error creating data source: {e}")
            raise
    
    def start_ingestion_job(self, kb_id: str, data_source_id: str) -> str:
        """
        Start ingestion job to sync S3 data with Knowledge Base.
        
        Args:
            kb_id: ID of the Knowledge Base
            data_source_id: ID of the data source
            
        Returns:
            str: ID of the ingestion job
        """
        try:
            response = self.bedrock_agent_client.start_ingestion_job(
                knowledgeBaseId=kb_id,
                dataSourceId=data_source_id
            )
            
            job_id = response['ingestionJob']['ingestionJobId']
            logger.info(f"Started ingestion job: {job_id}")
            
            # Wait for ingestion to complete
            max_wait = 600  # 10 minutes
            wait_interval = 15
            elapsed = 0
            
            while elapsed < max_wait:
                response = self.bedrock_agent_client.get_ingestion_job(
                    knowledgeBaseId=kb_id,
                    dataSourceId=data_source_id,
                    ingestionJobId=job_id
                )
                
                status = response['ingestionJob']['status']
                if status == 'COMPLETE':
                    logger.info("Ingestion job completed successfully")
                    return job_id
                elif status == 'FAILED':
                    raise Exception(f"Ingestion job failed: {response['ingestionJob'].get('failureReasons', [])}")
                
                logger.info(f"Ingestion in progress... ({elapsed}s)")
                time.sleep(wait_interval)
                elapsed += wait_interval
            
            logger.warning("Ingestion job still running after timeout")
            return job_id
            
        except ClientError as e:
            logger.error(f"Error starting ingestion job: {e}")
            raise
    
    def setup(self) -> dict:
        """
        Complete setup: create all resources and sync data.
        
        Returns:
            dict: Dictionary with created resource IDs
        """
        logger.info("Starting Bedrock Knowledge Base setup...")
        
        try:
            # Create IAM role
            role_arn = self.create_iam_role_for_kb()
            
            # Create OpenSearch collection
            collection_arn = self.create_opensearch_collection()
            
            # Create Knowledge Base
            kb_id = self.create_knowledge_base(role_arn, collection_arn)
            
            # Create data source
            data_source_id = self.create_data_source(kb_id)
            
            # Start ingestion
            job_id = self.start_ingestion_job(kb_id, data_source_id)
            
            result = {
                'knowledge_base_id': kb_id,
                'data_source_id': data_source_id,
                'ingestion_job_id': job_id,
                'role_arn': role_arn,
                'collection_arn': collection_arn
            }
            
            logger.info("Bedrock Knowledge Base setup complete!")
            return result
            
        except Exception as e:
            logger.error(f"Setup failed: {e}")
            raise


def main():
    """Main function to run the setup."""
    setup = BedrockKnowledgeBaseSetup()
    
    try:
        result = setup.setup()
        
        print("\n✅ Bedrock Knowledge Base setup completed successfully!")
        print(f"\nKnowledge Base ID: {result['knowledge_base_id']}")
        print(f"Data Source ID: {result['data_source_id']}")
        print(f"Ingestion Job ID: {result['ingestion_job_id']}")
        print(f"\nNext steps:")
        print(f"1. Update .env file with BEDROCK_KNOWLEDGE_BASE_ID={result['knowledge_base_id']}")
        print("2. Test Knowledge Base queries")
        print("3. Integrate with Service Mapper")
        
    except Exception as e:
        print(f"\n❌ Bedrock Knowledge Base setup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
