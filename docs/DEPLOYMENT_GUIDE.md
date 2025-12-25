# AWS Pricing Assistant - Complete Deployment Guide

This guide provides step-by-step instructions for deploying the AWS Pricing Assistant to production.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Detailed Deployment Steps](#detailed-deployment-steps)
4. [Configuration](#configuration)
5. [Troubleshooting](#troubleshooting)
6. [Maintenance](#maintenance)
7. [Security Best Practices](#security-best-practices)

## Prerequisites

### Required Tools

- **AWS CLI** (v2.x or higher)
  ```bash
  aws --version
  ```
  Install: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html

- **Python 3.11+**
  ```bash
  python3 --version
  ```

- **Git**
  ```bash
  git --version
  ```

- **Docker** (for ECS deployment)
  ```bash
  docker --version
  ```

### AWS Account Requirements

- Active AWS account with appropriate permissions
- IAM user or role with the following permissions:
  - EC2 (full access)
  - S3 (full access)
  - DynamoDB (full access)
  - CloudFormation (full access)
  - IAM (create roles and policies)
  - Bedrock (invoke models and manage Knowledge Base)
  - CloudWatch (logs and metrics)
  - Secrets Manager (create and read secrets)
  - EventBridge (create rules)
  - Lambda (create and invoke functions)

- **Bedrock Access**: Ensure your AWS account has access to Amazon Bedrock
  - Go to AWS Console → Bedrock → Model access
  - Request access to Claude 3.5 Sonnet model
  - Wait for approval (usually instant)

### EC2 Key Pair

Create an EC2 key pair for SSH access:

```bash
aws ec2 create-key-pair \
  --key-name aws-pricing-assistant-key \
  --query 'KeyMaterial' \
  --output text > ~/.ssh/aws-pricing-assistant-key.pem

chmod 400 ~/.ssh/aws-pricing-assistant-key.pem
```

## Quick Start

For a complete automated deployment:

```bash
# 1. Clone the repository
git clone <repository-url>
cd aws-pricing-assistant

# 2. Configure environment
cp .env.example .env
# Edit .env with your settings

# 3. Configure AWS credentials
aws configure

# 4. Run complete deployment
export AWS_REGION=us-east-1
export KEY_PAIR_NAME=aws-pricing-assistant-key
./scripts/deploy_all.sh
```

This will deploy:
- Complete AWS infrastructure (VPC, ALB, EC2, S3, etc.)
- DynamoDB tables
- Bedrock Knowledge Base
- EventBridge crawler schedule
- Backend application
- Frontend application

## Detailed Deployment Steps

### Step 1: Infrastructure Deployment

Deploy the complete AWS infrastructure using CloudFormation:

```bash
# Set environment variables
export AWS_REGION=us-east-1
export STACK_NAME=aws-pricing-assistant
export ENVIRONMENT=production
export INSTANCE_TYPE=t3.medium
export KEY_PAIR_NAME=aws-pricing-assistant-key

# Optional: For custom domain
export DOMAIN_NAME=pricing.example.com
export CERTIFICATE_ARN=arn:aws:acm:us-east-1:123456789012:certificate/xxx

# Deploy infrastructure
./scripts/deploy_infrastructure.sh
```

This creates:
- VPC with 2 public subnets across 2 AZs
- Application Load Balancer with target group
- Auto Scaling Group (1-4 EC2 instances)
- 3 S3 buckets (frontend, quotes, knowledge base)
- CloudFront distribution
- IAM roles and security groups
- CloudWatch log groups
- Secrets Manager secret

**Expected Duration**: 10-15 minutes

### Step 2: DynamoDB Tables Setup

Create all required DynamoDB tables:

```bash
./scripts/setup_dynamodb.sh
```

This creates:
- `aws-pricing-assistant-users` (with username index)
- `aws-pricing-assistant-sessions` (with TTL)
- `aws-pricing-assistant-quotes` (with user-quotes index)
- `aws-pricing-assistant-cloud-services` (with category and date indexes)
- `aws-pricing-assistant-mapping-cache` (with TTL)

**Expected Duration**: 2-3 minutes

### Step 3: Bedrock Knowledge Base Setup

Set up the Knowledge Base for service mappings and pricing data:

```bash
# Upload knowledge base data to S3
python3 scripts/setup_knowledge_base_s3.py

# Create Bedrock Knowledge Base
python3 scripts/create_bedrock_knowledge_base.py
```

**Note**: After creation, update `.env` with the Knowledge Base ID:
```bash
BEDROCK_KNOWLEDGE_BASE_ID=<your-kb-id>
```

**Expected Duration**: 5-10 minutes

### Step 4: EventBridge Crawler Setup

Configure the daily web crawler schedule:

```bash
# Default: Daily at 2 AM UTC
./scripts/setup_eventbridge_crawler.sh

# Custom schedule
export SCHEDULE_EXPRESSION="cron(0 3 * * ? *)"  # 3 AM UTC
./scripts/setup_eventbridge_crawler.sh
```

This creates:
- Lambda function for web crawler
- EventBridge rule for daily execution
- IAM role with necessary permissions

**Expected Duration**: 3-5 minutes

### Step 5: Backend Deployment

Deploy the FastAPI backend application:

#### Option A: EC2 Deployment

```bash
export DEPLOYMENT_TYPE=ec2
export EC2_INSTANCE_ID=<instance-id-from-stack>
./scripts/deploy_backend.sh
```

#### Option B: ECS Deployment

```bash
export DEPLOYMENT_TYPE=ecs
export ECS_CLUSTER=aws-pricing-assistant-cluster
./scripts/deploy_backend.sh
```

**Expected Duration**: 5-10 minutes

### Step 6: Frontend Deployment

Deploy the web interface to S3 and CloudFront:

```bash
# Get backend URL from infrastructure stack
export BACKEND_API_URL=<alb-url-from-stack>
export S3_BUCKET=<frontend-bucket-from-stack>
export CLOUDFRONT_ENABLED=true

./scripts/deploy_frontend.sh
```

**Expected Duration**: 3-5 minutes (plus 15-20 minutes for CloudFront distribution)

### Step 7: CloudWatch Logging Setup

Configure CloudWatch log groups and monitoring:

```bash
python3 scripts/setup_cloudwatch_logs.py
```

**Expected Duration**: 1-2 minutes

### Step 8: Verification

Verify the deployment:

```bash
# Run verification script
python3 verify_setup.py

# Test backend API
curl http://<alb-url>/health

# Test frontend
curl http://<cloudfront-url>
```

## Configuration

### Environment Variables

Edit `.env` file with your configuration:

```bash
# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=123456789012

# Bedrock Configuration
BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0
BEDROCK_KNOWLEDGE_BASE_ID=<your-kb-id>

# DynamoDB Tables
DYNAMODB_USERS_TABLE=aws-pricing-assistant-users
DYNAMODB_SESSIONS_TABLE=aws-pricing-assistant-sessions
DYNAMODB_QUOTES_TABLE=aws-pricing-assistant-quotes
DYNAMODB_CLOUD_SERVICES_TABLE=aws-pricing-assistant-cloud-services
DYNAMODB_MAPPING_CACHE_TABLE=aws-pricing-assistant-mapping-cache

# S3 Buckets
FRONTEND_BUCKET=<frontend-bucket-name>
QUOTE_BUCKET=<quote-bucket-name>
KNOWLEDGE_BASE_BUCKET=<kb-bucket-name>

# Authentication
JWT_SECRET_KEY=<generate-secure-random-string>
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=30

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4

# Logging
LOG_LEVEL=INFO
CLOUDWATCH_LOG_GROUP=/aws/pricing-assistant/production

# Web Crawler
CRAWLER_SCHEDULE=cron(0 2 * * ? *)
CRAWLER_TIMEOUT=900
```

### Secrets Manager

Update secrets in AWS Secrets Manager:

```bash
aws secretsmanager update-secret \
  --secret-id aws-pricing-assistant-secrets \
  --secret-string '{
    "JWT_SECRET_KEY": "your-secure-random-string",
    "ENCRYPTION_KEY": "your-encryption-key"
  }'
```

### Generate Secure Keys

```bash
# Generate JWT secret key
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate encryption key
python3 scripts/generate_encryption_key.py
```

## Troubleshooting

### Common Issues

#### 1. Bedrock Access Denied

**Error**: `AccessDeniedException: Could not access Bedrock`

**Solution**:
- Go to AWS Console → Bedrock → Model access
- Request access to Claude models
- Wait for approval

#### 2. DynamoDB Table Already Exists

**Error**: `ResourceInUseException: Table already exists`

**Solution**:
- Tables already exist, skip creation
- Or delete existing tables and recreate:
  ```bash
  aws dynamodb delete-table --table-name aws-pricing-assistant-users
  ```

#### 3. EC2 Instance Not Accessible

**Error**: Cannot SSH to EC2 instance

**Solution**:
- Check security group allows SSH (port 22)
- Verify key pair is correct
- Check instance is in public subnet with public IP

#### 4. Frontend Not Loading

**Error**: Frontend shows blank page or errors

**Solution**:
- Check `config.js` has correct backend URL
- Verify CORS is enabled on backend
- Check CloudFront distribution is deployed
- Clear browser cache

#### 5. Knowledge Base Not Found

**Error**: `ResourceNotFoundException: Knowledge Base not found`

**Solution**:
- Verify Knowledge Base ID in `.env`
- Check Knowledge Base is created in correct region
- Ensure S3 bucket has data and is accessible

### Logs and Debugging

#### View Application Logs

```bash
# CloudWatch Logs
aws logs tail /aws/pricing-assistant/production --follow

# EC2 Instance Logs
ssh -i ~/.ssh/aws-pricing-assistant-key.pem ec2-user@<instance-ip>
sudo journalctl -u pricing-assistant -f
```

#### Check Service Status

```bash
# On EC2 instance
sudo systemctl status pricing-assistant

# Check backend health
curl http://<alb-url>/health
```

#### Debug Lambda Function

```bash
# View Lambda logs
aws logs tail /aws/lambda/aws-pricing-assistant-crawler --follow

# Invoke Lambda manually
aws lambda invoke \
  --function-name aws-pricing-assistant-crawler \
  --invocation-type RequestResponse \
  output.json
```

## Maintenance

### Regular Tasks

#### Update Application

```bash
# Pull latest code
git pull origin main

# Redeploy backend
./scripts/deploy_backend.sh

# Redeploy frontend
./scripts/deploy_frontend.sh
```

#### Update Knowledge Base

```bash
# Update knowledge base data
python3 scripts/setup_knowledge_base_s3.py

# Sync Knowledge Base
aws bedrock-agent start-ingestion-job \
  --knowledge-base-id <kb-id> \
  --data-source-id <data-source-id>
```

#### Monitor Crawler

```bash
# Check crawler execution history
aws events list-rule-names-by-target \
  --target-arn <lambda-arn>

# View recent crawler runs
aws lambda list-invocations \
  --function-name aws-pricing-assistant-crawler
```

#### Database Maintenance

```bash
# Backup DynamoDB tables
aws dynamodb create-backup \
  --table-name aws-pricing-assistant-users \
  --backup-name users-backup-$(date +%Y%m%d)

# Check table metrics
aws dynamodb describe-table \
  --table-name aws-pricing-assistant-users
```

### Scaling

#### Scale EC2 Instances

```bash
# Update Auto Scaling Group
aws autoscaling set-desired-capacity \
  --auto-scaling-group-name aws-pricing-assistant-asg \
  --desired-capacity 4
```

#### Scale DynamoDB

```bash
# Update table capacity
aws dynamodb update-table \
  --table-name aws-pricing-assistant-users \
  --provisioned-throughput ReadCapacityUnits=10,WriteCapacityUnits=10
```

## Security Best Practices

### 1. Network Security

- ✅ Use VPC with private subnets for sensitive resources
- ✅ Configure security groups with least privilege
- ✅ Enable VPC Flow Logs
- ✅ Use AWS WAF for ALB protection

### 2. Data Security

- ✅ Enable encryption at rest for DynamoDB
- ✅ Enable S3 bucket encryption
- ✅ Use HTTPS/TLS for all communications
- ✅ Rotate encryption keys regularly

### 3. Access Control

- ✅ Use IAM roles instead of access keys
- ✅ Enable MFA for AWS Console access
- ✅ Implement least privilege IAM policies
- ✅ Regularly audit IAM permissions

### 4. Monitoring and Logging

- ✅ Enable CloudTrail for audit logging
- ✅ Set up CloudWatch alarms for critical metrics
- ✅ Monitor application logs for errors
- ✅ Enable AWS Config for compliance

### 5. Application Security

- ✅ Use strong JWT secret keys
- ✅ Implement rate limiting
- ✅ Validate and sanitize all inputs
- ✅ Keep dependencies up to date

### Security Checklist

Before going to production:

- [ ] Change all default passwords and keys
- [ ] Enable HTTPS with valid SSL certificate
- [ ] Configure AWS WAF rules
- [ ] Set up CloudWatch alarms
- [ ] Enable CloudTrail logging
- [ ] Review and restrict security group rules
- [ ] Enable DynamoDB point-in-time recovery
- [ ] Set up S3 bucket lifecycle policies
- [ ] Configure backup and disaster recovery
- [ ] Document incident response procedures

## Cost Optimization

### Estimated Monthly Costs

Based on moderate usage (1000 quotes/month):

- **EC2 (2x t3.medium)**: ~$60
- **ALB**: ~$20
- **DynamoDB (on-demand)**: ~$10
- **S3**: ~$5
- **CloudFront**: ~$10
- **Bedrock**: ~$50 (varies by usage)
- **Lambda**: ~$5
- **CloudWatch**: ~$5

**Total**: ~$165/month

### Cost Reduction Tips

1. **Use Reserved Instances** for EC2 (save up to 70%)
2. **Enable S3 Intelligent-Tiering** for quote storage
3. **Use DynamoDB on-demand** for variable workloads
4. **Set S3 lifecycle policies** to delete old quotes
5. **Monitor Bedrock usage** and optimize prompts
6. **Use CloudFront caching** to reduce origin requests

## Support

For issues or questions:

1. Check this documentation
2. Review troubleshooting section
3. Check application logs
4. Contact AWS Support for infrastructure issues
5. File an issue in the project repository

## Additional Resources

- [AWS Well-Architected Framework](https://aws.amazon.com/architecture/well-architected/)
- [Amazon Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [DynamoDB Best Practices](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/best-practices.html)
