#!/bin/bash

# AWS Pricing Assistant - Infrastructure Deployment Script
# This script deploys the CloudFormation stack for the complete infrastructure

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
STACK_NAME="${STACK_NAME:-aws-pricing-assistant}"
ENVIRONMENT="${ENVIRONMENT:-production}"
INSTANCE_TYPE="${INSTANCE_TYPE:-t3.medium}"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   AWS Pricing Assistant - Infrastructure Deployment       ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
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
    
    # Check if CloudFormation template exists
    if [ ! -f "infrastructure/cloudformation-template.yaml" ]; then
        print_error "CloudFormation template not found!"
        exit 1
    fi
    
    print_info "Prerequisites check passed!"
}

# Get parameters
get_parameters() {
    print_info "Gathering deployment parameters..."
    
    # Get EC2 Key Pair
    if [ -z "$KEY_PAIR_NAME" ]; then
        print_info "Available EC2 Key Pairs:"
        aws ec2 describe-key-pairs --region "$AWS_REGION" --query 'KeyPairs[*].KeyName' --output table
        echo ""
        read -p "Enter EC2 Key Pair name: " KEY_PAIR_NAME
    fi
    
    # Optional: Domain name
    if [ -z "$DOMAIN_NAME" ]; then
        read -p "Enter custom domain name (optional, press Enter to skip): " DOMAIN_NAME
    fi
    
    # Optional: Certificate ARN
    if [ -n "$DOMAIN_NAME" ] && [ -z "$CERTIFICATE_ARN" ]; then
        print_info "For HTTPS, you need an ACM certificate."
        read -p "Enter ACM Certificate ARN (optional, press Enter to skip): " CERTIFICATE_ARN
    fi
    
    print_info "Deployment parameters:"
    print_info "  Stack Name: $STACK_NAME"
    print_info "  Region: $AWS_REGION"
    print_info "  Environment: $ENVIRONMENT"
    print_info "  Instance Type: $INSTANCE_TYPE"
    print_info "  Key Pair: $KEY_PAIR_NAME"
    [ -n "$DOMAIN_NAME" ] && print_info "  Domain: $DOMAIN_NAME"
    [ -n "$CERTIFICATE_ARN" ] && print_info "  Certificate: $CERTIFICATE_ARN"
}

# Validate CloudFormation template
validate_template() {
    print_info "Validating CloudFormation template..."
    
    aws cloudformation validate-template \
        --template-body file://infrastructure/cloudformation-template.yaml \
        --region "$AWS_REGION" > /dev/null
    
    print_info "Template validation passed!"
}

# Deploy CloudFormation stack
deploy_stack() {
    print_info "Deploying CloudFormation stack..."
    
    # Build parameters
    PARAMETERS="ParameterKey=Environment,ParameterValue=$ENVIRONMENT"
    PARAMETERS="$PARAMETERS ParameterKey=InstanceType,ParameterValue=$INSTANCE_TYPE"
    PARAMETERS="$PARAMETERS ParameterKey=KeyPairName,ParameterValue=$KEY_PAIR_NAME"
    
    if [ -n "$DOMAIN_NAME" ]; then
        PARAMETERS="$PARAMETERS ParameterKey=DomainName,ParameterValue=$DOMAIN_NAME"
    fi
    
    if [ -n "$CERTIFICATE_ARN" ]; then
        PARAMETERS="$PARAMETERS ParameterKey=CertificateArn,ParameterValue=$CERTIFICATE_ARN"
    fi
    
    # Check if stack exists
    if aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$AWS_REGION" &> /dev/null; then
        print_info "Stack exists, updating..."
        
        aws cloudformation update-stack \
            --stack-name "$STACK_NAME" \
            --template-body file://infrastructure/cloudformation-template.yaml \
            --parameters $PARAMETERS \
            --capabilities CAPABILITY_IAM \
            --region "$AWS_REGION" || {
                if [ $? -eq 254 ]; then
                    print_warning "No updates to be performed"
                    return
                else
                    print_error "Stack update failed"
                    exit 1
                fi
            }
        
        print_info "Waiting for stack update to complete..."
        aws cloudformation wait stack-update-complete \
            --stack-name "$STACK_NAME" \
            --region "$AWS_REGION"
    else
        print_info "Creating new stack..."
        
        aws cloudformation create-stack \
            --stack-name "$STACK_NAME" \
            --template-body file://infrastructure/cloudformation-template.yaml \
            --parameters $PARAMETERS \
            --capabilities CAPABILITY_IAM \
            --region "$AWS_REGION" \
            --tags Key=Application,Value=aws-pricing-assistant Key=Environment,Value=$ENVIRONMENT
        
        print_info "Waiting for stack creation to complete (this may take 10-15 minutes)..."
        aws cloudformation wait stack-create-complete \
            --stack-name "$STACK_NAME" \
            --region "$AWS_REGION"
    fi
    
    print_info "Stack deployment completed!"
}

# Get stack outputs
get_outputs() {
    print_info "Retrieving stack outputs..."
    
    OUTPUTS=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$AWS_REGION" \
        --query 'Stacks[0].Outputs' \
        --output json)
    
    echo "$OUTPUTS" > /tmp/stack-outputs.json
    
    # Extract key outputs
    ALB_DNS=$(echo "$OUTPUTS" | jq -r '.[] | select(.OutputKey=="LoadBalancerDNS") | .OutputValue')
    ALB_URL=$(echo "$OUTPUTS" | jq -r '.[] | select(.OutputKey=="LoadBalancerURL") | .OutputValue')
    CLOUDFRONT_URL=$(echo "$OUTPUTS" | jq -r '.[] | select(.OutputKey=="CloudFrontURL") | .OutputValue')
    FRONTEND_BUCKET=$(echo "$OUTPUTS" | jq -r '.[] | select(.OutputKey=="FrontendBucketName") | .OutputValue')
    QUOTE_BUCKET=$(echo "$OUTPUTS" | jq -r '.[] | select(.OutputKey=="QuoteBucketName") | .OutputValue')
    KB_BUCKET=$(echo "$OUTPUTS" | jq -r '.[] | select(.OutputKey=="KnowledgeBaseBucketName") | .OutputValue')
    
    # Export for use by other scripts
    export BACKEND_API_URL="$ALB_URL"
    export S3_BUCKET="$FRONTEND_BUCKET"
    export QUOTE_BUCKET
    export KB_BUCKET
}

# Update .env file
update_env_file() {
    print_info "Updating .env file with infrastructure details..."
    
    if [ ! -f ".env" ]; then
        cp .env.example .env
    fi
    
    # Update .env with stack outputs
    sed -i.bak "s|^AWS_REGION=.*|AWS_REGION=$AWS_REGION|" .env
    sed -i.bak "s|^FRONTEND_BUCKET=.*|FRONTEND_BUCKET=$FRONTEND_BUCKET|" .env
    sed -i.bak "s|^QUOTE_BUCKET=.*|QUOTE_BUCKET=$QUOTE_BUCKET|" .env
    sed -i.bak "s|^KNOWLEDGE_BASE_BUCKET=.*|KNOWLEDGE_BASE_BUCKET=$KB_BUCKET|" .env
    
    rm .env.bak 2>/dev/null || true
    
    print_info ".env file updated"
}

# Print deployment summary
print_summary() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  Deployment Summary${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${GREEN}Infrastructure deployed successfully!${NC}"
    echo ""
    echo "Stack Details:"
    echo "  • Stack Name: $STACK_NAME"
    echo "  • Region: $AWS_REGION"
    echo "  • Environment: $ENVIRONMENT"
    echo ""
    echo "Resources Created:"
    echo "  • VPC with 2 public subnets"
    echo "  • Application Load Balancer"
    echo "  • Auto Scaling Group (1-4 instances)"
    echo "  • 3 S3 Buckets (frontend, quotes, knowledge base)"
    echo "  • CloudFront Distribution"
    echo "  • CloudWatch Log Groups"
    echo "  • IAM Roles and Security Groups"
    echo ""
    echo "Access URLs:"
    echo "  • Backend API: $ALB_URL"
    echo "  • Frontend: $CLOUDFRONT_URL"
    echo ""
    echo "S3 Buckets:"
    echo "  • Frontend: $FRONTEND_BUCKET"
    echo "  • Quotes: $QUOTE_BUCKET"
    echo "  • Knowledge Base: $KB_BUCKET"
    echo ""
    echo "Next Steps:"
    echo "  1. Deploy backend application to EC2 instances"
    echo "  2. Deploy frontend to S3 bucket"
    echo "  3. Set up DynamoDB tables"
    echo "  4. Configure Bedrock Knowledge Base"
    echo "  5. Set up EventBridge crawler schedule"
    echo ""
    echo "Run the following commands:"
    echo "  export BACKEND_API_URL=$ALB_URL"
    echo "  export S3_BUCKET=$FRONTEND_BUCKET"
    echo "  ./scripts/deploy_backend.sh"
    echo "  ./scripts/deploy_frontend.sh"
    echo ""
}

# Main deployment flow
main() {
    check_prerequisites
    get_parameters
    
    # Confirm deployment
    echo ""
    echo -e "${YELLOW}This will create AWS resources that may incur charges.${NC}"
    read -p "Do you want to continue? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Deployment cancelled."
        exit 0
    fi
    
    validate_template
    deploy_stack
    get_outputs
    update_env_file
    print_summary
}

# Handle errors
trap 'print_error "Deployment failed at: $BASH_COMMAND"' ERR

# Run main function
main
