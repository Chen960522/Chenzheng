# AWS Pricing Assistant - Configuration Reference

This document provides detailed information about all configuration options for the AWS Pricing Assistant.

## Table of Contents

1. [Environment Variables](#environment-variables)
2. [AWS Configuration](#aws-configuration)
3. [Application Configuration](#application-configuration)
4. [Security Configuration](#security-configuration)
5. [Performance Tuning](#performance-tuning)
6. [Advanced Configuration](#advanced-configuration)

## Environment Variables

All configuration is managed through environment variables defined in the `.env` file.

### AWS Configuration

```bash
# AWS Region
AWS_REGION=us-east-1
# Description: AWS region for all resources
# Default: us-east-1
# Options: Any valid AWS region (us-east-1, us-west-2, eu-west-1, etc.)

# AWS Account ID
AWS_ACCOUNT_ID=123456789012
# Description: Your AWS account ID
# Required: Yes
# How to get: aws sts get-caller-identity --query Account --output text
```

### Bedrock Configuration

```bash
# Bedrock Model ID
BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0
# Description: Bedrock model for AI processing
# Default: anthropic.claude-3-5-sonnet-20241022-v2:0
# Options:
#   - anthropic.claude-3-5-sonnet-20241022-v2:0 (recommended)
#   - anthropic.claude-3-sonnet-20240229-v1:0
#   - anthropic.claude-3-haiku-20240307-v1:0

# Bedrock Knowledge Base ID
BEDROCK_KNOWLEDGE_BASE_ID=ABCDEFGHIJ
# Description: Knowledge Base ID for service mappings
# Required: Yes
# How to get: aws bedrock-agent list-knowledge-bases

# Bedrock Embedding Model
BEDROCK_EMBEDDING_MODEL=amazon.titan-embed-text-v2:0
# Description: Model for Knowledge Base embeddings
# Default: amazon.titan-embed-text-v2:0
# Options:
#   - amazon.titan-embed-text-v2:0
#   - amazon.titan-embed-text-v1

# Bedrock Max Tokens
BEDROCK_MAX_TOKENS=4096
# Description: Maximum tokens for model responses
# Default: 4096
# Range: 1-200000 (depends on model)

# Bedrock Temperature
BEDROCK_TEMPERATURE=0.7
# Description: Model temperature (creativity)
# Default: 0.7
# Range: 0.0-1.0 (0=deterministic, 1=creative)
```

### DynamoDB Configuration

```bash
# Table Name Prefix
TABLE_PREFIX=aws-pricing-assistant
# Description: Prefix for all DynamoDB tables
# Default: aws-pricing-assistant

# Users Table
DYNAMODB_USERS_TABLE=aws-pricing-assistant-users
# Description: Table for user accounts
# Required: Yes

# Sessions Table
DYNAMODB_SESSIONS_TABLE=aws-pricing-assistant-sessions
# Description: Table for user sessions
# Required: Yes

# Quotes Table
DYNAMODB_QUOTES_TABLE=aws-pricing-assistant-quotes
# Description: Table for quote history
# Required: Yes

# Cloud Services Table
DYNAMODB_CLOUD_SERVICES_TABLE=aws-pricing-assistant-cloud-services
# Description: Table for crawled cloud service data
# Required: Yes

# Mapping Cache Table
DYNAMODB_MAPPING_CACHE_TABLE=aws-pricing-assistant-mapping-cache
# Description: Table for cached service mappings
# Required: Yes

# DynamoDB Endpoint (for local development)
DYNAMODB_ENDPOINT_URL=
# Description: Custom DynamoDB endpoint (leave empty for AWS)
# Default: (empty - uses AWS)
# Example: http://localhost:8000 (for DynamoDB Local)
```

### S3 Configuration

```bash
# Frontend Bucket
FRONTEND_BUCKET=aws-pricing-assistant-frontend-123456789012
# Description: S3 bucket for frontend files
# Required: Yes

# Quote Bucket
QUOTE_BUCKET=aws-pricing-assistant-quotes-123456789012
# Description: S3 bucket for generated quotes
# Required: Yes

# Knowledge Base Bucket
KNOWLEDGE_BASE_BUCKET=aws-pricing-assistant-knowledge-base-123456789012
# Description: S3 bucket for Knowledge Base data
# Required: Yes

# S3 Presigned URL Expiration
S3_PRESIGNED_URL_EXPIRATION=3600
# Description: Presigned URL expiration in seconds
# Default: 3600 (1 hour)
# Range: 1-604800 (1 second to 7 days)
```

### Authentication Configuration

```bash
# JWT Secret Key
JWT_SECRET_KEY=your-super-secret-key-change-this
# Description: Secret key for JWT token signing
# Required: Yes
# Security: MUST be changed in production
# Generate: python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# JWT Algorithm
JWT_ALGORITHM=HS256
# Description: Algorithm for JWT signing
# Default: HS256
# Options: HS256, HS384, HS512, RS256, RS384, RS512

# JWT Expiration
JWT_EXPIRATION_MINUTES=30
# Description: JWT token expiration time in minutes
# Default: 30
# Range: 5-1440 (5 minutes to 24 hours)

# Password Hash Algorithm
PASSWORD_HASH_ALGORITHM=argon2
# Description: Algorithm for password hashing
# Default: argon2
# Options: argon2, bcrypt

# Session Timeout
SESSION_TIMEOUT_MINUTES=30
# Description: Session inactivity timeout
# Default: 30
# Range: 5-1440
```

### API Configuration

```bash
# API Host
API_HOST=0.0.0.0
# Description: Host to bind API server
# Default: 0.0.0.0 (all interfaces)
# Options: 0.0.0.0, 127.0.0.1, specific IP

# API Port
API_PORT=8000
# Description: Port for API server
# Default: 8000
# Range: 1024-65535

# API Workers
API_WORKERS=4
# Description: Number of Uvicorn worker processes
# Default: 4
# Recommendation: (2 x CPU cores) + 1

# API Reload
API_RELOAD=false
# Description: Enable auto-reload on code changes
# Default: false
# Options: true (development), false (production)

# CORS Origins
CORS_ORIGINS=http://localhost:3000,https://example.com
# Description: Allowed CORS origins (comma-separated)
# Default: * (all origins)
# Example: http://localhost:3000,https://app.example.com

# Rate Limit
RATE_LIMIT_PER_MINUTE=100
# Description: Maximum requests per minute per user
# Default: 100
# Range: 1-10000
```

### Logging Configuration

```bash
# Log Level
LOG_LEVEL=INFO
# Description: Application log level
# Default: INFO
# Options: DEBUG, INFO, WARNING, ERROR, CRITICAL

# CloudWatch Log Group
CLOUDWATCH_LOG_GROUP=/aws/pricing-assistant/production
# Description: CloudWatch log group name
# Required: Yes

# CloudWatch Log Stream
CLOUDWATCH_LOG_STREAM=backend
# Description: CloudWatch log stream name
# Default: backend

# Enable CloudWatch Logging
ENABLE_CLOUDWATCH_LOGGING=true
# Description: Send logs to CloudWatch
# Default: true
# Options: true, false

# Log Format
LOG_FORMAT=json
# Description: Log output format
# Default: json
# Options: json, text
```

### Web Crawler Configuration

```bash
# Crawler Schedule
CRAWLER_SCHEDULE=cron(0 2 * * ? *)
# Description: EventBridge schedule expression
# Default: cron(0 2 * * ? *) (daily at 2 AM UTC)
# Format: cron(minutes hours day-of-month month day-of-week year)
# Examples:
#   - cron(0 2 * * ? *) - Daily at 2 AM
#   - cron(0 */6 * * ? *) - Every 6 hours
#   - cron(0 0 ? * MON *) - Every Monday at midnight

# Crawler Timeout
CRAWLER_TIMEOUT=900
# Description: Crawler execution timeout in seconds
# Default: 900 (15 minutes)
# Range: 60-900

# Crawler User Agent
CRAWLER_USER_AGENT=AWS-Pricing-Assistant-Bot/1.0
# Description: User agent for web requests
# Default: AWS-Pricing-Assistant-Bot/1.0

# Crawler Retry Attempts
CRAWLER_RETRY_ATTEMPTS=3
# Description: Number of retry attempts on failure
# Default: 3
# Range: 1-10

# Crawler Retry Delay
CRAWLER_RETRY_DELAY=5
# Description: Delay between retries in seconds
# Default: 5
# Range: 1-60
```

### Encryption Configuration

```bash
# Encryption Key
ENCRYPTION_KEY=your-encryption-key-change-this
# Description: Key for encrypting sensitive data
# Required: Yes
# Security: MUST be changed in production
# Generate: python3 scripts/generate_encryption_key.py

# Encryption Algorithm
ENCRYPTION_ALGORITHM=AES-256-GCM
# Description: Encryption algorithm
# Default: AES-256-GCM
# Options: AES-256-GCM, AES-256-CBC
```

## AWS Configuration

### IAM Permissions

The application requires the following IAM permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem",
        "dynamodb:GetItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem",
        "dynamodb:Query",
        "dynamodb:Scan"
      ],
      "Resource": "arn:aws:dynamodb:*:*:table/aws-pricing-assistant-*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::aws-pricing-assistant-*",
        "arn:aws:s3:::aws-pricing-assistant-*/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:Retrieve"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:*:*:secret:aws-pricing-assistant-*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:log-group:/aws/pricing-assistant/*"
    }
  ]
}
```

### Secrets Manager

Store sensitive configuration in AWS Secrets Manager:

```bash
# Create secret
aws secretsmanager create-secret \
  --name aws-pricing-assistant-secrets \
  --secret-string '{
    "JWT_SECRET_KEY": "your-jwt-secret",
    "ENCRYPTION_KEY": "your-encryption-key",
    "DATABASE_PASSWORD": "your-db-password"
  }'

# Update secret
aws secretsmanager update-secret \
  --secret-id aws-pricing-assistant-secrets \
  --secret-string '{
    "JWT_SECRET_KEY": "new-jwt-secret",
    "ENCRYPTION_KEY": "new-encryption-key"
  }'

# Retrieve secret
aws secretsmanager get-secret-value \
  --secret-id aws-pricing-assistant-secrets \
  --query SecretString --output text
```

## Application Configuration

### Frontend Configuration

Frontend configuration is in `frontend/config.js`:

```javascript
const API_CONFIG = {
    // Backend API URL
    baseURL: 'http://your-alb-url.amazonaws.com',
    
    // WebSocket URL
    wsURL: 'ws://your-alb-url.amazonaws.com/api/ws',
    
    // Request timeout (ms)
    timeout: 30000,
    
    // Retry configuration
    retryAttempts: 3,
    retryDelay: 1000,
    
    // Language
    defaultLanguage: 'en',
    supportedLanguages: ['en', 'zh']
};
```

### Agent Configuration

Agent configuration is in `src/agents/pricing_agent.py`:

```python
AGENT_CONFIG = {
    # Model configuration
    'model_id': 'anthropic.claude-3-5-sonnet-20241022-v2:0',
    'max_tokens': 4096,
    'temperature': 0.7,
    
    # Tool configuration
    'tools': [
        'parse_configuration',
        'map_services',
        'calculate_pricing',
        'generate_quote',
        'query_knowledge_base'
    ],
    
    # Timeout configuration
    'timeout': 300,  # 5 minutes
    'max_retries': 3
}
```

## Security Configuration

### HTTPS Configuration

For production, configure HTTPS:

1. **Obtain SSL Certificate**:
   ```bash
   # Request certificate from ACM
   aws acm request-certificate \
     --domain-name pricing.example.com \
     --validation-method DNS
   ```

2. **Configure ALB**:
   - Add HTTPS listener (port 443)
   - Attach SSL certificate
   - Redirect HTTP to HTTPS

3. **Update CloudFormation**:
   - Set `CertificateArn` parameter
   - Enable HTTPS listener

### WAF Configuration

Configure AWS WAF for additional security:

```bash
# Create WAF web ACL
aws wafv2 create-web-acl \
  --name pricing-assistant-waf \
  --scope REGIONAL \
  --default-action Allow={} \
  --rules file://waf-rules.json

# Associate with ALB
aws wafv2 associate-web-acl \
  --web-acl-arn <waf-acl-arn> \
  --resource-arn <alb-arn>
```

## Performance Tuning

### Database Optimization

```bash
# Enable DynamoDB auto-scaling
aws application-autoscaling register-scalable-target \
  --service-namespace dynamodb \
  --resource-id table/aws-pricing-assistant-quotes \
  --scalable-dimension dynamodb:table:ReadCapacityUnits \
  --min-capacity 5 \
  --max-capacity 100

# Enable DynamoDB DAX (caching)
aws dax create-cluster \
  --cluster-name pricing-assistant-dax \
  --node-type dax.t3.small \
  --replication-factor 3
```

### Caching Configuration

```bash
# Enable ElastiCache Redis
aws elasticache create-cache-cluster \
  --cache-cluster-id pricing-assistant-cache \
  --cache-node-type cache.t3.micro \
  --engine redis \
  --num-cache-nodes 1

# Update .env
REDIS_ENDPOINT=pricing-assistant-cache.abc123.0001.use1.cache.amazonaws.com:6379
ENABLE_CACHING=true
CACHE_TTL=3600
```

## Advanced Configuration

### Multi-Region Deployment

For multi-region deployment:

1. Deploy infrastructure in each region
2. Configure Route 53 for DNS routing
3. Set up cross-region replication for S3
4. Use DynamoDB Global Tables

### Custom Domain Configuration

```bash
# Create Route 53 hosted zone
aws route53 create-hosted-zone \
  --name pricing.example.com \
  --caller-reference $(date +%s)

# Create A record for ALB
aws route53 change-resource-record-sets \
  --hosted-zone-id <zone-id> \
  --change-batch file://dns-record.json
```

### Monitoring and Alerts

```bash
# Create CloudWatch alarm for errors
aws cloudwatch put-metric-alarm \
  --alarm-name pricing-assistant-errors \
  --alarm-description "Alert on high error rate" \
  --metric-name Errors \
  --namespace AWS/ApplicationELB \
  --statistic Sum \
  --period 300 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2
```

## Configuration Best Practices

1. **Never commit secrets** to version control
2. **Use Secrets Manager** for sensitive data
3. **Enable encryption** for all data at rest
4. **Use HTTPS** for all communications
5. **Implement rate limiting** to prevent abuse
6. **Monitor and log** all configuration changes
7. **Test configuration** in staging before production
8. **Document all changes** to configuration
9. **Use infrastructure as code** for reproducibility
10. **Regular security audits** of configuration

## Configuration Validation

Validate your configuration:

```bash
# Run validation script
python3 verify_setup.py

# Check all environment variables
python3 -c "from src.config.settings import Settings; print(Settings().dict())"

# Test AWS connectivity
aws sts get-caller-identity
aws bedrock list-foundation-models
aws dynamodb list-tables
```
