#!/bin/bash

# AWS Pricing Assistant - Frontend Deployment Script
# This script deploys the frontend to S3 and CloudFront

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
APP_NAME="aws-pricing-assistant"
S3_BUCKET="${S3_BUCKET:-$APP_NAME-frontend}"
CLOUDFRONT_ENABLED="${CLOUDFRONT_ENABLED:-true}"

echo -e "${GREEN}=== AWS Pricing Assistant Frontend Deployment ===${NC}"
echo "AWS Region: $AWS_REGION"
echo "S3 Bucket: $S3_BUCKET"
echo "CloudFront: $CLOUDFRONT_ENABLED"
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
    
    # Check if frontend directory exists
    if [ ! -d "frontend" ]; then
        print_error "Frontend directory not found. Run this script from the project root."
        exit 1
    fi
    
    print_info "Prerequisites check passed!"
}

# Create S3 bucket
create_s3_bucket() {
    print_info "Checking S3 bucket: $S3_BUCKET"
    
    if aws s3 ls "s3://$S3_BUCKET" 2>&1 | grep -q 'NoSuchBucket'; then
        print_info "Creating S3 bucket..."
        
        if [ "$AWS_REGION" = "us-east-1" ]; then
            aws s3 mb "s3://$S3_BUCKET" --region "$AWS_REGION"
        else
            aws s3 mb "s3://$S3_BUCKET" --region "$AWS_REGION" \
                --create-bucket-configuration LocationConstraint="$AWS_REGION"
        fi
        
        print_info "S3 bucket created: $S3_BUCKET"
    else
        print_info "S3 bucket already exists: $S3_BUCKET"
    fi
}

# Configure S3 bucket for static website hosting
configure_s3_website() {
    print_info "Configuring S3 bucket for static website hosting..."
    
    # Enable static website hosting
    aws s3 website "s3://$S3_BUCKET" \
        --index-document index.html \
        --error-document index.html
    
    # Set bucket policy for public read access
    BUCKET_POLICY=$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadGetObject",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::$S3_BUCKET/*"
    }
  ]
}
EOF
)
    
    echo "$BUCKET_POLICY" > /tmp/bucket-policy.json
    aws s3api put-bucket-policy \
        --bucket "$S3_BUCKET" \
        --policy file:///tmp/bucket-policy.json
    
    rm /tmp/bucket-policy.json
    
    # Enable CORS
    CORS_CONFIG=$(cat <<EOF
{
  "CORSRules": [
    {
      "AllowedOrigins": ["*"],
      "AllowedMethods": ["GET", "HEAD"],
      "AllowedHeaders": ["*"],
      "MaxAgeSeconds": 3000
    }
  ]
}
EOF
)
    
    echo "$CORS_CONFIG" > /tmp/cors-config.json
    aws s3api put-bucket-cors \
        --bucket "$S3_BUCKET" \
        --cors-configuration file:///tmp/cors-config.json
    
    rm /tmp/cors-config.json
    
    print_info "S3 bucket configured for static website hosting"
}

# Update frontend configuration
update_frontend_config() {
    print_info "Updating frontend configuration..."
    
    # Get backend API URL from environment or prompt
    if [ -z "$BACKEND_API_URL" ]; then
        print_warning "BACKEND_API_URL not set. Using default: http://localhost:8000"
        BACKEND_API_URL="http://localhost:8000"
    fi
    
    print_info "Backend API URL: $BACKEND_API_URL"
    
    # Create config.js with API endpoint
    cat > frontend/config.js <<EOF
// Auto-generated configuration
const API_CONFIG = {
    baseURL: '${BACKEND_API_URL}',
    wsURL: '${BACKEND_API_URL}'.replace('http', 'ws') + '/api/ws',
    timeout: 30000
};

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = API_CONFIG;
}
EOF
    
    print_info "Frontend configuration updated"
}

# Upload frontend files to S3
upload_to_s3() {
    print_info "Uploading frontend files to S3..."
    
    # Sync frontend directory to S3
    aws s3 sync frontend/ "s3://$S3_BUCKET/" \
        --delete \
        --cache-control "public, max-age=3600" \
        --exclude "*.md" \
        --exclude ".DS_Store"
    
    # Set specific cache control for HTML files (no cache)
    aws s3 cp frontend/ "s3://$S3_BUCKET/" \
        --recursive \
        --exclude "*" \
        --include "*.html" \
        --cache-control "no-cache, no-store, must-revalidate" \
        --metadata-directive REPLACE
    
    # Set longer cache for static assets
    aws s3 cp frontend/ "s3://$S3_BUCKET/" \
        --recursive \
        --exclude "*" \
        --include "*.css" \
        --include "*.js" \
        --include "*.png" \
        --include "*.jpg" \
        --include "*.svg" \
        --cache-control "public, max-age=31536000" \
        --metadata-directive REPLACE
    
    print_info "Frontend files uploaded to S3"
}

# Create CloudFront distribution
create_cloudfront_distribution() {
    if [ "$CLOUDFRONT_ENABLED" != "true" ]; then
        print_info "CloudFront disabled, skipping..."
        return
    fi
    
    print_info "Checking CloudFront distribution..."
    
    # Check if distribution already exists
    DISTRIBUTION_ID=$(aws cloudfront list-distributions \
        --query "DistributionList.Items[?Origins.Items[0].DomainName=='$S3_BUCKET.s3-website-$AWS_REGION.amazonaws.com'].Id" \
        --output text 2>/dev/null || echo "")
    
    if [ -n "$DISTRIBUTION_ID" ]; then
        print_info "CloudFront distribution already exists: $DISTRIBUTION_ID"
        
        # Create invalidation
        print_info "Creating CloudFront invalidation..."
        aws cloudfront create-invalidation \
            --distribution-id "$DISTRIBUTION_ID" \
            --paths "/*" > /dev/null
        
        print_info "CloudFront cache invalidated"
    else
        print_info "Creating CloudFront distribution..."
        
        # Create distribution configuration
        DISTRIBUTION_CONFIG=$(cat <<EOF
{
  "CallerReference": "$(date +%s)",
  "Comment": "AWS Pricing Assistant Frontend",
  "Enabled": true,
  "Origins": {
    "Quantity": 1,
    "Items": [
      {
        "Id": "S3-$S3_BUCKET",
        "DomainName": "$S3_BUCKET.s3-website-$AWS_REGION.amazonaws.com",
        "CustomOriginConfig": {
          "HTTPPort": 80,
          "HTTPSPort": 443,
          "OriginProtocolPolicy": "http-only"
        }
      }
    ]
  },
  "DefaultRootObject": "index.html",
  "DefaultCacheBehavior": {
    "TargetOriginId": "S3-$S3_BUCKET",
    "ViewerProtocolPolicy": "redirect-to-https",
    "AllowedMethods": {
      "Quantity": 2,
      "Items": ["GET", "HEAD"],
      "CachedMethods": {
        "Quantity": 2,
        "Items": ["GET", "HEAD"]
      }
    },
    "ForwardedValues": {
      "QueryString": false,
      "Cookies": {
        "Forward": "none"
      }
    },
    "MinTTL": 0,
    "DefaultTTL": 3600,
    "MaxTTL": 86400,
    "Compress": true
  },
  "CustomErrorResponses": {
    "Quantity": 1,
    "Items": [
      {
        "ErrorCode": 404,
        "ResponsePagePath": "/index.html",
        "ResponseCode": "200",
        "ErrorCachingMinTTL": 300
      }
    ]
  },
  "PriceClass": "PriceClass_100"
}
EOF
)
        
        echo "$DISTRIBUTION_CONFIG" > /tmp/distribution-config.json
        
        DISTRIBUTION_ID=$(aws cloudfront create-distribution \
            --distribution-config file:///tmp/distribution-config.json \
            --query 'Distribution.Id' \
            --output text)
        
        rm /tmp/distribution-config.json
        
        print_info "CloudFront distribution created: $DISTRIBUTION_ID"
        print_warning "Distribution deployment may take 15-20 minutes..."
    fi
    
    # Get CloudFront domain name
    CLOUDFRONT_DOMAIN=$(aws cloudfront get-distribution \
        --id "$DISTRIBUTION_ID" \
        --query 'Distribution.DomainName' \
        --output text)
    
    print_info "CloudFront Domain: https://$CLOUDFRONT_DOMAIN"
}

# Main deployment flow
main() {
    check_prerequisites
    create_s3_bucket
    configure_s3_website
    update_frontend_config
    upload_to_s3
    create_cloudfront_distribution
    
    # Print deployment summary
    echo ""
    print_info "=== Deployment Summary ==="
    print_info "S3 Bucket: $S3_BUCKET"
    print_info "S3 Website URL: http://$S3_BUCKET.s3-website-$AWS_REGION.amazonaws.com"
    
    if [ "$CLOUDFRONT_ENABLED" = "true" ] && [ -n "$CLOUDFRONT_DOMAIN" ]; then
        print_info "CloudFront URL: https://$CLOUDFRONT_DOMAIN"
    fi
    
    echo ""
    print_info "Frontend deployed successfully!"
}

# Run main function
main
