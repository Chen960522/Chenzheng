"""Set up EventBridge scheduled task for web crawler."""

import sys
import os
import json

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import boto3
from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


def create_crawler_lambda():
    """
    Create Lambda function for running the crawler.
    
    Note: This is a placeholder. In production, you would:
    1. Package the crawler code and dependencies
    2. Upload to S3 or deploy directly
    3. Create Lambda function with proper IAM role
    """
    lambda_client = boto3.client('lambda', region_name=settings.aws_region)
    
    function_name = 'aws-pricing-assistant-crawler'
    
    # Lambda function code (simplified)
    lambda_code = """
import json
from src.services.crawlers.web_crawler import WebCrawler

def lambda_handler(event, context):
    '''Lambda handler for scheduled crawler execution.'''
    
    crawler = WebCrawler()
    
    try:
        result = crawler.crawl_all_providers()
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Crawling completed successfully',
                'report': result['report']
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'Crawling failed',
                'error': str(e)
            })
        }
"""
    
    logger.info(f"Lambda function code prepared: {function_name}")
    logger.info("Note: Actual Lambda deployment requires packaging and IAM role setup")
    
    return function_name


def create_eventbridge_rule():
    """Create EventBridge rule for daily crawler execution."""
    events_client = boto3.client('events', region_name=settings.aws_region)
    
    rule_name = 'aws-pricing-assistant-crawler-schedule'
    
    try:
        # Create EventBridge rule with cron schedule
        response = events_client.put_rule(
            Name=rule_name,
            ScheduleExpression=settings.crawler_schedule,  # Default: cron(0 2 * * ? *)
            State='ENABLED',
            Description='Daily scheduled crawling of cloud provider services'
        )
        
        logger.info(f"Created EventBridge rule: {rule_name}")
        logger.info(f"Schedule: {settings.crawler_schedule}")
        logger.info(f"Rule ARN: {response['RuleArn']}")
        
        return response['RuleArn']
        
    except events_client.exceptions.ResourceAlreadyExistsException:
        logger.info(f"EventBridge rule already exists: {rule_name}")
        
        # Get existing rule
        response = events_client.describe_rule(Name=rule_name)
        return response['Arn']
    
    except Exception as e:
        logger.error(f"Failed to create EventBridge rule: {e}")
        raise


def add_lambda_target(rule_arn: str, lambda_function_name: str):
    """
    Add Lambda function as target for EventBridge rule.
    
    Args:
        rule_arn: ARN of the EventBridge rule
        lambda_function_name: Name of the Lambda function
    """
    events_client = boto3.client('events', region_name=settings.aws_region)
    lambda_client = boto3.client('lambda', region_name=settings.aws_region)
    
    rule_name = 'aws-pricing-assistant-crawler-schedule'
    
    # Get Lambda function ARN
    try:
        lambda_response = lambda_client.get_function(FunctionName=lambda_function_name)
        lambda_arn = lambda_response['Configuration']['FunctionArn']
    except lambda_client.exceptions.ResourceNotFoundException:
        logger.error(f"Lambda function not found: {lambda_function_name}")
        logger.info("Please create the Lambda function first")
        return
    
    try:
        # Add Lambda as target
        events_client.put_targets(
            Rule=rule_name,
            Targets=[
                {
                    'Id': '1',
                    'Arn': lambda_arn,
                    'Input': json.dumps({
                        'source': 'eventbridge-schedule',
                        'action': 'crawl_all_providers'
                    })
                }
            ]
        )
        
        logger.info(f"Added Lambda target to EventBridge rule: {lambda_function_name}")
        
        # Add permission for EventBridge to invoke Lambda
        try:
            lambda_client.add_permission(
                FunctionName=lambda_function_name,
                StatementId='AllowEventBridgeInvoke',
                Action='lambda:InvokeFunction',
                Principal='events.amazonaws.com',
                SourceArn=rule_arn
            )
            logger.info("Added EventBridge invoke permission to Lambda")
        except lambda_client.exceptions.ResourceConflictException:
            logger.info("Lambda permission already exists")
        
    except Exception as e:
        logger.error(f"Failed to add Lambda target: {e}")
        raise


def setup_crawler_schedule():
    """Set up complete EventBridge scheduled task for crawler."""
    logger.info("Setting up crawler schedule...")
    
    # Step 1: Create/verify Lambda function
    lambda_function_name = create_crawler_lambda()
    
    # Step 2: Create EventBridge rule
    rule_arn = create_eventbridge_rule()
    
    # Step 3: Add Lambda as target (commented out until Lambda is deployed)
    logger.info("\nNext steps:")
    logger.info("1. Package and deploy the Lambda function")
    logger.info("2. Run add_lambda_target() to connect EventBridge to Lambda")
    logger.info(f"3. Lambda function name: {lambda_function_name}")
    logger.info(f"4. EventBridge rule ARN: {rule_arn}")
    
    # Uncomment when Lambda is deployed:
    # add_lambda_target(rule_arn, lambda_function_name)
    
    logger.info("\nCrawler schedule setup complete!")


def main():
    """Main entry point."""
    setup_crawler_schedule()


if __name__ == "__main__":
    main()
