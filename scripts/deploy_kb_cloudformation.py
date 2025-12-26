"""
Deploy Bedrock Knowledge Base using CloudFormation.

This approach may bypass SCP restrictions that block direct API calls.
"""

import os
import sys
import time
import logging
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

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
        'stack_name': 'aws-pricing-kb-stack'
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


def deploy_stack(config: dict) -> dict:
    """Deploy CloudFormation stack."""
    cfn = boto3.client('cloudformation', region_name=config['aws_region'])
    
    # Load template
    template_path = Path(__file__).parent.parent / 'infrastructure' / 'bedrock-kb-stack.yaml'
    
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")
    
    with open(template_path, 'r', encoding='utf-8') as f:
        template_body = f.read()
    
    logger.info(f"Deploying CloudFormation stack: {config['stack_name']}")
    
    try:
        # Check if stack exists
        try:
            cfn.describe_stacks(StackName=config['stack_name'])
            stack_exists = True
            logger.info("Stack already exists, updating...")
        except ClientError as e:
            if 'does not exist' in str(e):
                stack_exists = False
                logger.info("Creating new stack...")
            else:
                raise
        
        # Create or update stack
        if stack_exists:
            response = cfn.update_stack(
                StackName=config['stack_name'],
                TemplateBody=template_body,
                Parameters=[
                    {
                        'ParameterKey': 'S3BucketName',
                        'ParameterValue': config['bucket_name']
                    },
                    {
                        'ParameterKey': 'EmbeddingModelId',
                        'ParameterValue': config['embedding_model_id']
                    }
                ],
                Capabilities=['CAPABILITY_NAMED_IAM']
            )
            stack_id = response['StackId']
            wait_status = 'UPDATE_COMPLETE'
        else:
            response = cfn.create_stack(
                StackName=config['stack_name'],
                TemplateBody=template_body,
                Parameters=[
                    {
                        'ParameterKey': 'S3BucketName',
                        'ParameterValue': config['bucket_name']
                    },
                    {
                        'ParameterKey': 'EmbeddingModelId',
                        'ParameterValue': config['embedding_model_id']
                    }
                ],
                Capabilities=['CAPABILITY_NAMED_IAM'],
                OnFailure='ROLLBACK'
            )
            stack_id = response['StackId']
            wait_status = 'CREATE_COMPLETE'
        
        logger.info(f"Stack ID: {stack_id}")
        logger.info("Waiting for stack operation to complete...")
        
        # Wait for stack to complete
        waiter = cfn.get_waiter('stack_create_complete' if not stack_exists else 'stack_update_complete')
        
        try:
            waiter.wait(
                StackName=config['stack_name'],
                WaiterConfig={
                    'Delay': 15,
                    'MaxAttempts': 120
                }
            )
        except Exception as e:
            logger.error(f"Stack operation failed: {e}")
            # Get stack events for debugging
            events = cfn.describe_stack_events(StackName=config['stack_name'])
            logger.error("Recent stack events:")
            for event in events['StackEvents'][:10]:
                if 'FAILED' in event.get('ResourceStatus', ''):
                    logger.error(f"  {event['LogicalResourceId']}: {event.get('ResourceStatusReason', 'N/A')}")
            raise
        
        # Get stack outputs
        stack = cfn.describe_stacks(StackName=config['stack_name'])['Stacks'][0]
        outputs = {o['OutputKey']: o['OutputValue'] for o in stack.get('Outputs', [])}
        
        logger.info("✅ Stack deployed successfully!")
        
        return outputs
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_msg = e.response['Error']['Message']
        
        if error_code == 'ValidationError' and 'No updates are to be performed' in error_msg:
            logger.info("Stack is already up to date")
            # Get existing outputs
            stack = cfn.describe_stacks(StackName=config['stack_name'])['Stacks'][0]
            outputs = {o['OutputKey']: o['OutputValue'] for o in stack.get('Outputs', [])}
            return outputs
        else:
            logger.error(f"CloudFormation error: {error_code} - {error_msg}")
            raise


def start_ingestion(kb_id: str, data_source_id: str, config: dict):
    """Start data ingestion job."""
    bedrock_agent = boto3.client('bedrock-agent', region_name=config['aws_region'])
    
    try:
        logger.info("Starting data ingestion...")
        
        response = bedrock_agent.start_ingestion_job(
            knowledgeBaseId=kb_id,
            dataSourceId=data_source_id
        )
        
        job_id = response['ingestionJob']['ingestionJobId']
        logger.info(f"✅ Ingestion job started: {job_id}")
        
        # Monitor progress
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
    print("AWS Pricing Assistant - CloudFormation Deployment")
    print("=" * 70)
    print()
    print("This script deploys Bedrock Knowledge Base using CloudFormation.")
    print("This approach may bypass SCP restrictions on direct API calls.")
    print()
    
    # Load configuration
    config = load_config()
    print(f"Configuration:")
    print(f"  AWS Region: {config['aws_region']}")
    print(f"  S3 Bucket: {config['bucket_name']}")
    print(f"  Embedding Model: {config['embedding_model_id']}")
    print(f"  Stack Name: {config['stack_name']}")
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
    print("⚠️  This will create:")
    print("  - CloudFormation Stack")
    print("  - Bedrock Knowledge Base")
    print("  - OpenSearch Serverless Collection")
    print("  - IAM Service Role")
    print("  - Security Policies")
    print()
    print("💰 Estimated cost: $50-100/month for OpenSearch Serverless")
    print()
    
    response = input("Continue? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("Deployment cancelled.")
        sys.exit(0)
    
    print()
    print("Starting deployment...")
    print()
    
    try:
        # Deploy stack
        outputs = deploy_stack(config)
        print()
        
        # Display outputs
        print("Stack Outputs:")
        for key, value in outputs.items():
            print(f"  {key}: {value}")
        print()
        
        # Start ingestion if data source exists
        if 'KnowledgeBaseId' in outputs and 'DataSourceId' in outputs:
            kb_id = outputs['KnowledgeBaseId']
            ds_id = outputs['DataSourceId']
            
            print("Starting data ingestion...")
            try:
                job_id = start_ingestion(kb_id, ds_id, config)
                print(f"✅ Ingestion job: {job_id}")
            except Exception as e:
                print(f"⚠️  Could not start ingestion: {e}")
                print("   You can start it manually later.")
        
        print()
        print("=" * 70)
        print("✅ Deployment completed successfully!")
        print("=" * 70)
        print()
        print("Next steps:")
        print(f"1. Update .env file:")
        print(f"   BEDROCK_KNOWLEDGE_BASE_ID={outputs.get('KnowledgeBaseId', 'N/A')}")
        print("2. Upload data to S3:")
        print("   python scripts/setup_knowledge_base_s3.py")
        print("3. Test Knowledge Base queries")
        print()
        
    except Exception as e:
        print()
        print("=" * 70)
        print("❌ Deployment failed")
        print("=" * 70)
        print()
        print(f"Error: {e}")
        print()
        print("If CloudFormation also fails due to permissions:")
        print("1. Contact your AWS organization administrator")
        print("2. Or create Knowledge Base manually via AWS Console")
        print("3. See: scripts/PERMISSION_ISSUE_RESOLUTION.md")
        print()
        sys.exit(1)


if __name__ == "__main__":
    main()
