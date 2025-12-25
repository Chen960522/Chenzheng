#!/bin/bash

# AWS Pricing Assistant - DynamoDB Setup Script
# This script creates all required DynamoDB tables

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
TABLE_PREFIX="${TABLE_PREFIX:-aws-pricing-assistant}"

echo -e "${GREEN}=== AWS Pricing Assistant DynamoDB Setup ===${NC}"
echo "AWS Region: $AWS_REGION"
echo "Table Prefix: $TABLE_PREFIX"
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

# Create users table
create_users_table() {
    TABLE_NAME="$TABLE_PREFIX-users"
    print_info "Creating table: $TABLE_NAME"
    
    if aws dynamodb describe-table --table-name "$TABLE_NAME" --region "$AWS_REGION" &> /dev/null; then
        print_warning "Table already exists: $TABLE_NAME"
        return
    fi
    
    aws dynamodb create-table \
        --table-name "$TABLE_NAME" \
        --attribute-definitions \
            AttributeName=user_id,AttributeType=S \
            AttributeName=username,AttributeType=S \
        --key-schema \
            AttributeName=user_id,KeyType=HASH \
        --global-secondary-indexes \
            "IndexName=username-index,KeySchema=[{AttributeName=username,KeyType=HASH}],Projection={ProjectionType=ALL},ProvisionedThroughput={ReadCapacityUnits=5,WriteCapacityUnits=5}" \
        --provisioned-throughput \
            ReadCapacityUnits=5,WriteCapacityUnits=5 \
        --region "$AWS_REGION" \
        --tags Key=Application,Value=aws-pricing-assistant Key=Environment,Value=production
    
    print_info "Table created: $TABLE_NAME"
}

# Create sessions table
create_sessions_table() {
    TABLE_NAME="$TABLE_PREFIX-sessions"
    print_info "Creating table: $TABLE_NAME"
    
    if aws dynamodb describe-table --table-name "$TABLE_NAME" --region "$AWS_REGION" &> /dev/null; then
        print_warning "Table already exists: $TABLE_NAME"
        return
    fi
    
    aws dynamodb create-table \
        --table-name "$TABLE_NAME" \
        --attribute-definitions \
            AttributeName=session_id,AttributeType=S \
            AttributeName=user_id,AttributeType=S \
        --key-schema \
            AttributeName=session_id,KeyType=HASH \
        --global-secondary-indexes \
            "IndexName=user-sessions-index,KeySchema=[{AttributeName=user_id,KeyType=HASH}],Projection={ProjectionType=ALL},ProvisionedThroughput={ReadCapacityUnits=5,WriteCapacityUnits=5}" \
        --provisioned-throughput \
            ReadCapacityUnits=5,WriteCapacityUnits=5 \
        --region "$AWS_REGION" \
        --tags Key=Application,Value=aws-pricing-assistant Key=Environment,Value=production
    
    # Enable TTL for automatic session expiration
    print_info "Enabling TTL for sessions table..."
    aws dynamodb update-time-to-live \
        --table-name "$TABLE_NAME" \
        --time-to-live-specification "Enabled=true,AttributeName=expires_at" \
        --region "$AWS_REGION"
    
    print_info "Table created with TTL: $TABLE_NAME"
}

# Create quotes table
create_quotes_table() {
    TABLE_NAME="$TABLE_PREFIX-quotes"
    print_info "Creating table: $TABLE_NAME"
    
    if aws dynamodb describe-table --table-name "$TABLE_NAME" --region "$AWS_REGION" &> /dev/null; then
        print_warning "Table already exists: $TABLE_NAME"
        return
    fi
    
    aws dynamodb create-table \
        --table-name "$TABLE_NAME" \
        --attribute-definitions \
            AttributeName=quote_id,AttributeType=S \
            AttributeName=user_id,AttributeType=S \
            AttributeName=created_at,AttributeType=S \
        --key-schema \
            AttributeName=quote_id,KeyType=HASH \
        --global-secondary-indexes \
            "IndexName=user-quotes-index,KeySchema=[{AttributeName=user_id,KeyType=HASH},{AttributeName=created_at,KeyType=RANGE}],Projection={ProjectionType=ALL},ProvisionedThroughput={ReadCapacityUnits=5,WriteCapacityUnits=5}" \
        --provisioned-throughput \
            ReadCapacityUnits=5,WriteCapacityUnits=5 \
        --region "$AWS_REGION" \
        --tags Key=Application,Value=aws-pricing-assistant Key=Environment,Value=production
    
    print_info "Table created: $TABLE_NAME"
}

# Create cloud_services table
create_cloud_services_table() {
    TABLE_NAME="$TABLE_PREFIX-cloud-services"
    print_info "Creating table: $TABLE_NAME"
    
    if aws dynamodb describe-table --table-name "$TABLE_NAME" --region "$AWS_REGION" &> /dev/null; then
        print_warning "Table already exists: $TABLE_NAME"
        return
    fi
    
    aws dynamodb create-table \
        --table-name "$TABLE_NAME" \
        --attribute-definitions \
            AttributeName=provider,AttributeType=S \
            AttributeName=service_name,AttributeType=S \
            AttributeName=service_category,AttributeType=S \
            AttributeName=crawled_at,AttributeType=S \
        --key-schema \
            AttributeName=provider,KeyType=HASH \
            AttributeName=service_name,KeyType=RANGE \
        --global-secondary-indexes \
            "IndexName=category-index,KeySchema=[{AttributeName=service_category,KeyType=HASH}],Projection={ProjectionType=ALL},ProvisionedThroughput={ReadCapacityUnits=5,WriteCapacityUnits=5}" \
            "IndexName=crawled-date-index,KeySchema=[{AttributeName=crawled_at,KeyType=HASH}],Projection={ProjectionType=ALL},ProvisionedThroughput={ReadCapacityUnits=5,WriteCapacityUnits=5}" \
        --provisioned-throughput \
            ReadCapacityUnits=5,WriteCapacityUnits=5 \
        --region "$AWS_REGION" \
        --tags Key=Application,Value=aws-pricing-assistant Key=Environment,Value=production
    
    print_info "Table created: $TABLE_NAME"
}

# Create service_mapping_cache table
create_mapping_cache_table() {
    TABLE_NAME="$TABLE_PREFIX-mapping-cache"
    print_info "Creating table: $TABLE_NAME"
    
    if aws dynamodb describe-table --table-name "$TABLE_NAME" --region "$AWS_REGION" &> /dev/null; then
        print_warning "Table already exists: $TABLE_NAME"
        return
    fi
    
    aws dynamodb create-table \
        --table-name "$TABLE_NAME" \
        --attribute-definitions \
            AttributeName=source_provider,AttributeType=S \
            AttributeName=source_service,AttributeType=S \
        --key-schema \
            AttributeName=source_provider,KeyType=HASH \
            AttributeName=source_service,KeyType=RANGE \
        --provisioned-throughput \
            ReadCapacityUnits=5,WriteCapacityUnits=5 \
        --region "$AWS_REGION" \
        --tags Key=Application,Value=aws-pricing-assistant Key=Environment,Value=production
    
    # Enable TTL for cache expiration (30 days)
    print_info "Enabling TTL for mapping cache table..."
    aws dynamodb update-time-to-live \
        --table-name "$TABLE_NAME" \
        --time-to-live-specification "Enabled=true,AttributeName=ttl" \
        --region "$AWS_REGION"
    
    print_info "Table created with TTL: $TABLE_NAME"
}

# Wait for tables to be active
wait_for_tables() {
    print_info "Waiting for tables to become active..."
    
    TABLES=(
        "$TABLE_PREFIX-users"
        "$TABLE_PREFIX-sessions"
        "$TABLE_PREFIX-quotes"
        "$TABLE_PREFIX-cloud-services"
        "$TABLE_PREFIX-mapping-cache"
    )
    
    for TABLE in "${TABLES[@]}"; do
        print_info "Waiting for $TABLE..."
        aws dynamodb wait table-exists --table-name "$TABLE" --region "$AWS_REGION"
    done
    
    print_info "All tables are active!"
}

# Enable encryption at rest
enable_encryption() {
    print_info "Enabling encryption at rest for all tables..."
    
    TABLES=(
        "$TABLE_PREFIX-users"
        "$TABLE_PREFIX-sessions"
        "$TABLE_PREFIX-quotes"
        "$TABLE_PREFIX-cloud-services"
        "$TABLE_PREFIX-mapping-cache"
    )
    
    for TABLE in "${TABLES[@]}"; do
        print_info "Enabling encryption for $TABLE..."
        aws dynamodb update-table \
            --table-name "$TABLE" \
            --sse-specification Enabled=true,SSEType=KMS \
            --region "$AWS_REGION" &> /dev/null || print_warning "Encryption already enabled for $TABLE"
    done
    
    print_info "Encryption enabled for all tables"
}

# Main setup flow
main() {
    check_prerequisites
    
    print_info "Creating DynamoDB tables..."
    create_users_table
    create_sessions_table
    create_quotes_table
    create_cloud_services_table
    create_mapping_cache_table
    
    wait_for_tables
    enable_encryption
    
    # Print summary
    echo ""
    print_info "=== DynamoDB Setup Summary ==="
    print_info "Region: $AWS_REGION"
    print_info "Tables created:"
    print_info "  - $TABLE_PREFIX-users (with username-index)"
    print_info "  - $TABLE_PREFIX-sessions (with user-sessions-index, TTL enabled)"
    print_info "  - $TABLE_PREFIX-quotes (with user-quotes-index)"
    print_info "  - $TABLE_PREFIX-cloud-services (with category-index, crawled-date-index)"
    print_info "  - $TABLE_PREFIX-mapping-cache (with TTL enabled)"
    echo ""
    print_info "DynamoDB setup completed successfully!"
}

# Run main function
main
