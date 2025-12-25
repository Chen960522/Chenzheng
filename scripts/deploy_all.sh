#!/bin/bash

# AWS Pricing Assistant - Master Deployment Script
# This script orchestrates the complete deployment process

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
DEPLOYMENT_TYPE="${DEPLOYMENT_TYPE:-ec2}"  # ec2 or ecs
APP_NAME="aws-pricing-assistant"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   AWS Pricing Assistant - Complete Deployment Script      ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Deployment Configuration:"
echo "  AWS Region: $AWS_REGION"
echo "  Deployment Type: $DEPLOYMENT_TYPE"
echo "  Application: $APP_NAME"
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

print_step() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo ""
}

# Check prerequisites
check_prerequisites() {
    print_step "Step 1: Checking Prerequisites"
    
    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI not found. Please install it first."
        exit 1
    fi
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 not found. Please install it first."
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        print_error "AWS credentials not configured. Run 'aws configure' first."
        exit 1
    fi
    
    # Check if .env file exists
    if [ ! -f ".env" ]; then
        print_warning ".env file not found. Creating from .env.example..."
        cp .env.example .env
        print_warning "Please edit .env file with your configuration before continuing."
        read -p "Press Enter to continue after editing .env file..."
    fi
    
    print_info "Prerequisites check passed!"
}

# Setup DynamoDB tables
setup_dynamodb() {
    print_step "Step 2: Setting Up DynamoDB Tables"
    
    if [ -f "scripts/setup_dynamodb.sh" ]; then
        chmod +x scripts/setup_dynamodb.sh
        ./scripts/setup_dynamodb.sh
    else
        print_warning "DynamoDB setup script not found, using Python script..."
        python3 scripts/init_dynamodb.py
    fi
    
    print_info "DynamoDB setup completed!"
}

# Setup Knowledge Base
setup_knowledge_base() {
    print_step "Step 3: Setting Up Bedrock Knowledge Base"
    
    print_info "Setting up S3 bucket for Knowledge Base..."
    if [ -f "scripts/setup_knowledge_base_s3.py" ]; then
        python3 scripts/setup_knowledge_base_s3.py
    else
        print_warning "Knowledge Base S3 setup script not found, skipping..."
    fi
    
    print_info "Creating Bedrock Knowledge Base..."
    if [ -f "scripts/create_bedrock_knowledge_base.py" ]; then
        python3 scripts/create_bedrock_knowledge_base.py
    else
        print_warning "Bedrock Knowledge Base creation script not found, skipping..."
    fi
    
    print_info "Knowledge Base setup completed!"
}

# Setup EventBridge crawler
setup_crawler() {
    print_step "Step 4: Setting Up EventBridge Crawler Schedule"
    
    if [ -f "scripts/setup_eventbridge_crawler.sh" ]; then
        chmod +x scripts/setup_eventbridge_crawler.sh
        ./scripts/setup_eventbridge_crawler.sh
    else
        print_warning "EventBridge crawler setup script not found, skipping..."
    fi
    
    print_info "Crawler setup completed!"
}

# Deploy backend
deploy_backend() {
    print_step "Step 5: Deploying Backend"
    
    if [ -f "scripts/deploy_backend.sh" ]; then
        chmod +x scripts/deploy_backend.sh
        export DEPLOYMENT_TYPE
        ./scripts/deploy_backend.sh
    else
        print_error "Backend deployment script not found!"
        exit 1
    fi
    
    print_info "Backend deployment completed!"
}

# Deploy frontend
deploy_frontend() {
    print_step "Step 6: Deploying Frontend"
    
    # Get backend URL
    if [ -z "$BACKEND_API_URL" ]; then
        print_warning "BACKEND_API_URL not set. Please enter the backend API URL:"
        read -p "Backend API URL: " BACKEND_API_URL
        export BACKEND_API_URL
    fi
    
    if [ -f "scripts/deploy_frontend.sh" ]; then
        chmod +x scripts/deploy_frontend.sh
        ./scripts/deploy_frontend.sh
    else
        print_error "Frontend deployment script not found!"
        exit 1
    fi
    
    print_info "Frontend deployment completed!"
}

# Setup CloudWatch logging
setup_cloudwatch() {
    print_step "Step 7: Setting Up CloudWatch Logging"
    
    if [ -f "scripts/setup_cloudwatch_logs.py" ]; then
        python3 scripts/setup_cloudwatch_logs.py
    else
        print_warning "CloudWatch setup script not found, skipping..."
    fi
    
    print_info "CloudWatch setup completed!"
}

# Verify deployment
verify_deployment() {
    print_step "Step 8: Verifying Deployment"
    
    print_info "Running verification checks..."
    
    # Check DynamoDB tables
    print_info "Checking DynamoDB tables..."
    TABLES=(
        "$APP_NAME-users"
        "$APP_NAME-sessions"
        "$APP_NAME-quotes"
        "$APP_NAME-cloud-services"
        "$APP_NAME-mapping-cache"
    )
    
    for TABLE in "${TABLES[@]}"; do
        if aws dynamodb describe-table --table-name "$TABLE" --region "$AWS_REGION" &> /dev/null; then
            print_info "  ✓ Table exists: $TABLE"
        else
            print_warning "  ✗ Table not found: $TABLE"
        fi
    done
    
    # Check S3 bucket
    S3_BUCKET="${S3_BUCKET:-$APP_NAME-frontend}"
    if aws s3 ls "s3://$S3_BUCKET" &> /dev/null; then
        print_info "  ✓ S3 bucket exists: $S3_BUCKET"
    else
        print_warning "  ✗ S3 bucket not found: $S3_BUCKET"
    fi
    
    # Check Lambda function
    LAMBDA_FUNCTION="$APP_NAME-crawler"
    if aws lambda get-function --function-name "$LAMBDA_FUNCTION" --region "$AWS_REGION" &> /dev/null; then
        print_info "  ✓ Lambda function exists: $LAMBDA_FUNCTION"
    else
        print_warning "  ✗ Lambda function not found: $LAMBDA_FUNCTION"
    fi
    
    print_info "Verification completed!"
}

# Print deployment summary
print_summary() {
    print_step "Deployment Summary"
    
    echo -e "${GREEN}Deployment completed successfully!${NC}"
    echo ""
    echo "Resources created:"
    echo "  • DynamoDB Tables: 5 tables"
    echo "  • S3 Bucket: $APP_NAME-frontend"
    echo "  • Lambda Function: $APP_NAME-crawler"
    echo "  • EventBridge Rule: $APP_NAME-daily-crawler"
    echo "  • Backend: Deployed to $DEPLOYMENT_TYPE"
    echo "  • Frontend: Deployed to S3/CloudFront"
    echo ""
    echo "Next steps:"
    echo "  1. Update .env file with Knowledge Base ID"
    echo "  2. Configure SSL/TLS certificates for production"
    echo "  3. Set up custom domain names"
    echo "  4. Configure AWS WAF rules"
    echo "  5. Set up monitoring and alerts"
    echo ""
    echo "Access your application:"
    if [ -n "$BACKEND_API_URL" ]; then
        echo "  • Backend API: $BACKEND_API_URL"
        echo "  • API Docs: $BACKEND_API_URL/docs"
    fi
    if [ -n "$S3_BUCKET" ]; then
        echo "  • Frontend: http://$S3_BUCKET.s3-website-$AWS_REGION.amazonaws.com"
    fi
    echo ""
    echo -e "${GREEN}Thank you for using AWS Pricing Assistant!${NC}"
}

# Main deployment flow
main() {
    # Confirm deployment
    echo -e "${YELLOW}This script will deploy the complete AWS Pricing Assistant application.${NC}"
    echo -e "${YELLOW}This may incur AWS charges.${NC}"
    echo ""
    read -p "Do you want to continue? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Deployment cancelled."
        exit 0
    fi
    
    # Run deployment steps
    check_prerequisites
    setup_dynamodb
    setup_knowledge_base
    setup_crawler
    deploy_backend
    deploy_frontend
    setup_cloudwatch
    verify_deployment
    print_summary
}

# Handle errors
trap 'print_error "Deployment failed at step: $BASH_COMMAND"' ERR

# Run main function
main
