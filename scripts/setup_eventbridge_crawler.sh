#!/bin/bash

# AWS Pricing Assistant - EventBridge Crawler Schedule Setup
# This script configures EventBridge to trigger the web crawler daily

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
APP_NAME="aws-pricing-assistant"
RULE_NAME="$APP_NAME-daily-crawler"
SCHEDULE_EXPRESSION="${SCHEDULE_EXPRESSION:-cron(0 2 * * ? *)}"  # Daily at 2 AM UTC

echo -e "${GREEN}=== AWS Pricing Assistant EventBridge Crawler Setup ===${NC}"
echo "AWS Region: $AWS_REGION"
echo "Rule Name: $RULE_NAME"
echo "Schedule: $SCHEDULE_EXPRESSION"
echo ""

# Function to print colored messages
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    print_info "Checking prerequisites..."
    
    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI not found. Please install it first."
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        print_error "AWS credentials not configured. Run 'aws configure' first."
        exit 1
    fi
    
    print_info "Prerequisites check passed!"
}

# Create Lambda function for crawler
create_crawler_lambda() {
    FUNCTION_NAME="$APP_NAME-crawler"
    print_info "Checking Lambda function: $FUNCTION_NAME"
    
    # Check if function exists
    if aws lambda get-function --function-name "$FUNCTION_NAME" --region "$AWS_REGION" &> /dev/null; then
        print_warning "Lambda function already exists: $FUNCTION_NAME"
        return
    fi
    
    print_info "Creating Lambda function..."
    
    # Create deployment package
    print_info "Creating deployment package..."
    mkdir -p /tmp/lambda-package
    
    # Copy crawler code
    cp -r src/services/crawlers /tmp/lambda-package/
    cp -r src/models /tmp/lambda-package/
    cp -r src/config /tmp/lambda-package/
    cp -r src/utils /tmp/lambda-package/
    
    # Create Lambda handler
    cat > /tmp/lambda-package/lambda_handler.py <<'EOF'
import json
import os
import sys
from datetime import datetime

# Add package to path
sys.path.insert(0, '/var/task')

from crawlers.web_crawler import WebCrawler
from config.aws_clients import get_dynamodb_client
from utils.logger import get_logger

logger = get_logger(__name__)

def lambda_handler(event, context):
    """
    Lambda handler for scheduled web crawler execution
    """
    try:
        logger.info("Starting scheduled web crawler execution")
        
        # Initialize crawler
        db_client = get_dynamodb_client()
        crawler = WebCrawler(db_client)
        
        # Run crawler
        report = crawler.crawl_all_providers()
        
        logger.info(f"Crawler completed successfully: {report}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Crawler executed successfully',
                'report': report,
                'timestamp': datetime.utcnow().isoformat()
            })
        }
        
    except Exception as e:
        logger.error(f"Crawler execution failed: {str(e)}", exc_info=True)
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'Crawler execution failed',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            })
        }
EOF
    
    # Install dependencies
    cd /tmp/lambda-package
    pip install -t . boto3 requests beautifulsoup4 lxml -q
    
    # Create ZIP file
    zip -r /tmp/crawler-lambda.zip . -q
    cd -
    
    print_info "Deployment package created"
    
    # Get AWS account ID
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    
    # Create IAM role for Lambda
    ROLE_NAME="$APP_NAME-crawler-lambda-role"
    print_info "Creating IAM role: $ROLE_NAME"
    
    TRUST_POLICY=$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
)
    
    echo "$TRUST_POLICY" > /tmp/trust-policy.json
    
    ROLE_ARN=$(aws iam create-role \
        --role-name "$ROLE_NAME" \
        --assume-role-policy-document file:///tmp/trust-policy.json \
        --query 'Role.Arn' \
        --output text 2>/dev/null || \
        aws iam get-role --role-name "$ROLE_NAME" --query 'Role.Arn' --output text)
    
    rm /tmp/trust-policy.json
    
    # Attach policies
    print_info "Attaching IAM policies..."
    aws iam attach-role-policy \
        --role-name "$ROLE_NAME" \
        --policy-arn "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole" \
        2>/dev/null || true
    
    # Create inline policy for DynamoDB and Bedrock access
    INLINE_POLICY=$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem",
        "dynamodb:GetItem",
        "dynamodb:UpdateItem",
        "dynamodb:Query",
        "dynamodb:Scan"
      ],
      "Resource": [
        "arn:aws:dynamodb:$AWS_REGION:$ACCOUNT_ID:table/$APP_NAME-*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:Retrieve"
      ],
      "Resource": "*"
    }
  ]
}
EOF
)
    
    echo "$INLINE_POLICY" > /tmp/inline-policy.json
    
    aws iam put-role-policy \
        --role-name "$ROLE_NAME" \
        --policy-name "$APP_NAME-crawler-policy" \
        --policy-document file:///tmp/inline-policy.json
    
    rm /tmp/inline-policy.json
    
    # Wait for role to be available
    print_info "Waiting for IAM role to be available..."
    sleep 10
    
    # Create Lambda function
    print_info "Creating Lambda function..."
    aws lambda create-function \
        --function-name "$FUNCTION_NAME" \
        --runtime python3.11 \
        --role "$ROLE_ARN" \
        --handler lambda_handler.lambda_handler \
        --zip-file fileb:///tmp/crawler-lambda.zip \
        --timeout 900 \
        --memory-size 512 \
        --environment "Variables={AWS_REGION=$AWS_REGION,TABLE_PREFIX=$APP_NAME}" \
        --region "$AWS_REGION" \
        --tags Application=aws-pricing-assistant,Component=crawler
    
    print_info "Lambda function created: $FUNCTION_NAME"
    
    # Cleanup
    rm -rf /tmp/lambda-package /tmp/crawler-lambda.zip
}

# Create EventBridge rule
create_eventbridge_rule() {
    print_info "Creating EventBridge rule: $RULE_NAME"
    
    # Check if rule exists
    if aws events describe-rule --name "$RULE_NAME" --region "$AWS_REGION" &> /dev/null; then
        print_warning "EventBridge rule already exists: $RULE_NAME"
    else
        # Create rule
        aws events put-rule \
            --name "$RULE_NAME" \
            --description "Daily trigger for AWS Pricing Assistant web crawler" \
            --schedule-expression "$SCHEDULE_EXPRESSION" \
            --state ENABLED \
            --region "$AWS_REGION" \
            --tags key=Application,value=aws-pricing-assistant
        
        print_info "EventBridge rule created: $RULE_NAME"
    fi
}

# Add Lambda permission for EventBridge
add_lambda_permission() {
    FUNCTION_NAME="$APP_NAME-crawler"
    print_info "Adding Lambda permission for EventBridge..."
    
    # Get AWS account ID
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    
    # Add permission
    aws lambda add-permission \
        --function-name "$FUNCTION_NAME" \
        --statement-id "AllowEventBridgeInvoke" \
        --action "lambda:InvokeFunction" \
        --principal events.amazonaws.com \
        --source-arn "arn:aws:events:$AWS_REGION:$ACCOUNT_ID:rule/$RULE_NAME" \
        --region "$AWS_REGION" \
        2>/dev/null || print_warning "Permission already exists"
    
    print_info "Lambda permission added"
}

# Add Lambda target to EventBridge rule
add_rule_target() {
    FUNCTION_NAME="$APP_NAME-crawler"
    print_info "Adding Lambda target to EventBridge rule..."
    
    # Get Lambda ARN
    LAMBDA_ARN=$(aws lambda get-function \
        --function-name "$FUNCTION_NAME" \
        --region "$AWS_REGION" \
        --query 'Configuration.FunctionArn' \
        --output text)
    
    # Add target
    aws events put-targets \
        --rule "$RULE_NAME" \
        --targets "Id=1,Arn=$LAMBDA_ARN" \
        --region "$AWS_REGION"
    
    print_info "Lambda target added to EventBridge rule"
}

# Test the setup
test_crawler() {
    FUNCTION_NAME="$APP_NAME-crawler"
    print_info "Testing crawler Lambda function..."
    
    # Invoke Lambda function
    aws lambda invoke \
        --function-name "$FUNCTION_NAME" \
        --invocation-type RequestResponse \
        --region "$AWS_REGION" \
        /tmp/lambda-response.json
    
    # Display response
    if [ -f /tmp/lambda-response.json ]; then
        print_info "Lambda response:"
        cat /tmp/lambda-response.json | python3 -m json.tool
        rm /tmp/lambda-response.json
    fi
}

# Main setup flow
main() {
    check_prerequisites
    create_crawler_lambda
    create_eventbridge_rule
    add_lambda_permission
    add_rule_target
    
    # Ask if user wants to test
    echo ""
    read -p "Do you want to test the crawler now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        test_crawler
    fi
    
    # Print summary
    echo ""
    print_info "=== EventBridge Crawler Setup Summary ==="
    print_info "Lambda Function: $APP_NAME-crawler"
    print_info "EventBridge Rule: $RULE_NAME"
    print_info "Schedule: $SCHEDULE_EXPRESSION"
    print_info "Region: $AWS_REGION"
    echo ""
    print_info "EventBridge crawler setup completed successfully!"
    print_info "The crawler will run automatically according to the schedule."
}

# Run main function
main
