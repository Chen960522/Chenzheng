# Deployment Guide

## Prerequisites

- Python 3.11 or higher
- AWS Account with appropriate permissions
- AWS CLI configured
- Access to Amazon Bedrock (Claude models)

## Setup Steps

### 1. Clone and Install Dependencies

```bash
cd aws-pricing-assistant
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy `.env.example` to `.env` and update with your values:

```bash
cp .env.example .env
```

Required configurations:
- AWS credentials and region
- Bedrock model IDs and Knowledge Base ID
- DynamoDB table names
- S3 bucket names
- JWT secret key (generate a secure random string)

### 3. Initialize DynamoDB Tables

```bash
python scripts/init_dynamodb.py
```

This will create the following tables:
- `aws-pricing-assistant-users`
- `aws-pricing-assistant-sessions`
- `aws-pricing-assistant-quotes`
- `aws-pricing-assistant-cloud-services`
- `aws-pricing-assistant-mapping-cache`

### 4. Set Up Bedrock Knowledge Base

1. Create an S3 bucket for Knowledge Base data
2. Upload service mapping rules and pricing data
3. Create a Bedrock Knowledge Base pointing to the S3 bucket
4. Update `BEDROCK_KNOWLEDGE_BASE_ID` in `.env`

### 5. Run the Application

Development mode:
```bash
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

Production mode:
```bash
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 6. Access the Application

- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Frontend: Open `frontend/index.html` in a browser

## Production Deployment

### Option 1: EC2 Deployment

1. Launch an EC2 instance (t3.medium or larger)
2. Install Python and dependencies
3. Configure systemd service
4. Set up Nginx as reverse proxy
5. Configure SSL/TLS certificates

### Option 2: ECS Deployment

1. Build Docker image
2. Push to ECR
3. Create ECS task definition
4. Deploy to ECS cluster with ALB

### Option 3: Lambda + API Gateway

1. Package application with dependencies
2. Deploy to Lambda
3. Configure API Gateway
4. Set up CloudFront for frontend

## Security Checklist

- [ ] Change JWT_SECRET_KEY to a secure random value
- [ ] Enable HTTPS/TLS
- [ ] Configure security groups to restrict access
- [ ] Enable CloudWatch logging
- [ ] Set up AWS WAF rules
- [ ] Enable DynamoDB encryption at rest
- [ ] Enable S3 bucket encryption
- [ ] Configure IAM roles with least privilege
- [ ] Set up CloudTrail for audit logging

## Monitoring

- CloudWatch Logs: `/aws/pricing-assistant`
- CloudWatch Metrics: Custom metrics for API requests, errors
- X-Ray: Distributed tracing (optional)

## Troubleshooting

### Common Issues

1. **Bedrock Access Denied**: Ensure your AWS account has Bedrock access enabled
2. **DynamoDB Errors**: Check IAM permissions for DynamoDB operations
3. **Knowledge Base Not Found**: Verify Knowledge Base ID in configuration
4. **Import Errors**: Ensure all dependencies are installed

### Logs

Check application logs:
```bash
tail -f logs/application.log
```

Check CloudWatch logs:
```bash
aws logs tail /aws/pricing-assistant --follow
```
