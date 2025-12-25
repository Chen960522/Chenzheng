# AWS Pricing Assistant - Troubleshooting Guide

This guide helps you diagnose and resolve common issues with the AWS Pricing Assistant.

## Table of Contents

1. [Deployment Issues](#deployment-issues)
2. [Backend Issues](#backend-issues)
3. [Frontend Issues](#frontend-issues)
4. [Database Issues](#database-issues)
5. [Bedrock and AI Issues](#bedrock-and-ai-issues)
6. [Crawler Issues](#crawler-issues)
7. [Performance Issues](#performance-issues)
8. [Security Issues](#security-issues)

## Deployment Issues

### CloudFormation Stack Creation Failed

**Symptoms**: Stack creation fails with error message

**Common Causes**:
1. Insufficient IAM permissions
2. Resource limits exceeded
3. Invalid parameters
4. Resource name conflicts

**Solutions**:

```bash
# Check stack events for detailed error
aws cloudformation describe-stack-events \
  --stack-name aws-pricing-assistant \
  --max-items 20

# Check IAM permissions
aws iam get-user
aws iam list-attached-user-policies --user-name <your-username>

# Check service quotas
aws service-quotas list-service-quotas \
  --service-code ec2 \
  --query 'Quotas[?QuotaName==`Running On-Demand Standard instances`]'

# Delete failed stack and retry
aws cloudformation delete-stack --stack-name aws-pricing-assistant
aws cloudformation wait stack-delete-complete --stack-name aws-pricing-assistant
```

### EC2 Instances Not Starting

**Symptoms**: Auto Scaling Group shows 0 instances or instances fail health checks

**Solutions**:

```bash
# Check Auto Scaling Group status
aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names aws-pricing-assistant-asg

# Check EC2 instance logs
aws ec2 get-console-output --instance-id <instance-id>

# SSH to instance and check logs
ssh -i ~/.ssh/aws-pricing-assistant-key.pem ec2-user@<instance-ip>
sudo journalctl -xe

# Check user data script execution
sudo cat /var/log/cloud-init-output.log
```

### S3 Bucket Creation Failed

**Symptoms**: Bucket name already exists or access denied

**Solutions**:

```bash
# Bucket names must be globally unique
# Add account ID or random suffix to bucket name
export S3_BUCKET=aws-pricing-assistant-frontend-$(aws sts get-caller-identity --query Account --output text)

# Check bucket ownership
aws s3api head-bucket --bucket <bucket-name>

# List buckets in your account
aws s3 ls
```

## Backend Issues

### Backend API Not Responding

**Symptoms**: HTTP 502/503 errors or timeouts

**Diagnosis**:

```bash
# Check ALB target health
aws elbv2 describe-target-health \
  --target-group-arn <target-group-arn>

# Check backend service status on EC2
ssh -i ~/.ssh/aws-pricing-assistant-key.pem ec2-user@<instance-ip>
sudo systemctl status pricing-assistant

# Check application logs
sudo journalctl -u pricing-assistant -n 100 --no-pager
```

**Solutions**:

```bash
# Restart backend service
sudo systemctl restart pricing-assistant

# Check for port conflicts
sudo netstat -tlnp | grep 8000

# Verify environment variables
sudo cat /opt/aws-pricing-assistant/.env

# Check Python dependencies
cd /opt/aws-pricing-assistant
python3 -m pip list
```

### Authentication Failures

**Symptoms**: Login fails with 401 Unauthorized

**Diagnosis**:

```bash
# Check JWT secret key
aws secretsmanager get-secret-value \
  --secret-id aws-pricing-assistant-secrets \
  --query SecretString --output text

# Test authentication endpoint
curl -X POST http://<alb-url>/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password"}'
```

**Solutions**:

1. Verify JWT_SECRET_KEY in Secrets Manager matches .env
2. Check password hashing is working correctly
3. Verify user exists in DynamoDB users table
4. Check session expiration settings

### Rate Limiting Errors

**Symptoms**: HTTP 429 Too Many Requests

**Solutions**:

```bash
# Check rate limit configuration in .env
grep RATE_LIMIT /opt/aws-pricing-assistant/.env

# Temporarily disable rate limiting for testing
# Edit src/api/middleware.py and restart service

# Monitor request patterns
aws logs filter-log-events \
  --log-group-name /aws/pricing-assistant/production \
  --filter-pattern "429"
```

## Frontend Issues

### Frontend Not Loading

**Symptoms**: Blank page or 404 errors

**Diagnosis**:

```bash
# Check S3 bucket contents
aws s3 ls s3://<frontend-bucket>/

# Check bucket website configuration
aws s3api get-bucket-website --bucket <frontend-bucket>

# Check CloudFront distribution status
aws cloudfront list-distributions \
  --query "DistributionList.Items[?Origins.Items[0].DomainName=='<bucket-name>.s3-website-<region>.amazonaws.com']"
```

**Solutions**:

```bash
# Redeploy frontend
./scripts/deploy_frontend.sh

# Invalidate CloudFront cache
aws cloudfront create-invalidation \
  --distribution-id <distribution-id> \
  --paths "/*"

# Check browser console for errors
# Open browser DevTools (F12) and check Console tab
```

### CORS Errors

**Symptoms**: Browser console shows CORS policy errors

**Solutions**:

```bash
# Check backend CORS configuration
# Edit src/api/main.py and verify CORS settings

# Update CORS origins
# Add frontend URL to allowed origins list

# Restart backend service
sudo systemctl restart pricing-assistant

# Test CORS headers
curl -H "Origin: https://<frontend-url>" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type" \
  -X OPTIONS \
  http://<backend-url>/api/quotes/create -v
```

### WebSocket Connection Failed

**Symptoms**: Real-time updates not working

**Solutions**:

```bash
# Check WebSocket endpoint
curl -i -N \
  -H "Connection: Upgrade" \
  -H "Upgrade: websocket" \
  -H "Sec-WebSocket-Version: 13" \
  -H "Sec-WebSocket-Key: test" \
  http://<backend-url>/api/ws/quote-status

# Check ALB WebSocket support
# Ensure ALB listener has WebSocket enabled

# Check security group allows WebSocket traffic
aws ec2 describe-security-groups \
  --group-ids <backend-sg-id>
```

## Database Issues

### DynamoDB Access Denied

**Symptoms**: `AccessDeniedException` in logs

**Solutions**:

```bash
# Check IAM role permissions
aws iam get-role-policy \
  --role-name aws-pricing-assistant-ec2-role \
  --policy-name PricingAssistantPolicy

# Verify table names in .env match actual tables
aws dynamodb list-tables

# Test DynamoDB access
aws dynamodb scan \
  --table-name aws-pricing-assistant-users \
  --max-items 1
```

### Table Not Found

**Symptoms**: `ResourceNotFoundException: Table not found`

**Solutions**:

```bash
# List all tables
aws dynamodb list-tables

# Create missing tables
./scripts/setup_dynamodb.sh

# Verify table names in configuration
grep DYNAMODB_ .env
```

### Slow Query Performance

**Symptoms**: API responses are slow

**Diagnosis**:

```bash
# Check table metrics
aws dynamodb describe-table \
  --table-name aws-pricing-assistant-quotes

# Check consumed capacity
aws cloudwatch get-metric-statistics \
  --namespace AWS/DynamoDB \
  --metric-name ConsumedReadCapacityUnits \
  --dimensions Name=TableName,Value=aws-pricing-assistant-quotes \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average
```

**Solutions**:

1. Add indexes for frequently queried attributes
2. Use Query instead of Scan operations
3. Enable DynamoDB auto-scaling
4. Consider switching to on-demand billing mode

## Bedrock and AI Issues

### Bedrock Access Denied

**Symptoms**: `AccessDeniedException: Could not access Bedrock`

**Solutions**:

```bash
# Check Bedrock model access
aws bedrock list-foundation-models

# Request model access in AWS Console
# Go to Bedrock → Model access → Request access

# Verify IAM permissions
aws iam simulate-principal-policy \
  --policy-source-arn <role-arn> \
  --action-names bedrock:InvokeModel \
  --resource-arns "*"

# Check region supports Bedrock
# Bedrock is available in: us-east-1, us-west-2, ap-southeast-1, etc.
```

### Knowledge Base Not Found

**Symptoms**: `ResourceNotFoundException: Knowledge Base not found`

**Solutions**:

```bash
# List Knowledge Bases
aws bedrock-agent list-knowledge-bases

# Verify Knowledge Base ID in .env
grep BEDROCK_KNOWLEDGE_BASE_ID .env

# Check Knowledge Base status
aws bedrock-agent get-knowledge-base \
  --knowledge-base-id <kb-id>

# Recreate Knowledge Base if needed
python3 scripts/create_bedrock_knowledge_base.py
```

### Poor AI Response Quality

**Symptoms**: Incorrect service mappings or pricing

**Solutions**:

1. **Update Knowledge Base data**:
   ```bash
   python3 scripts/setup_knowledge_base_s3.py
   aws bedrock-agent start-ingestion-job \
     --knowledge-base-id <kb-id> \
     --data-source-id <data-source-id>
   ```

2. **Improve prompts**:
   - Edit `src/agents/prompts.py`
   - Add more examples and context
   - Test with different prompt variations

3. **Adjust model parameters**:
   - Increase temperature for more creative responses
   - Decrease temperature for more deterministic responses
   - Adjust max_tokens for longer responses

### Bedrock Throttling

**Symptoms**: `ThrottlingException: Rate exceeded`

**Solutions**:

```bash
# Check Bedrock quotas
aws service-quotas list-service-quotas \
  --service-code bedrock

# Request quota increase
aws service-quotas request-service-quota-increase \
  --service-code bedrock \
  --quota-code <quota-code> \
  --desired-value 100

# Implement exponential backoff in code
# Add retry logic with increasing delays
```

## Crawler Issues

### Crawler Not Running

**Symptoms**: No new services in database

**Diagnosis**:

```bash
# Check EventBridge rule
aws events describe-rule \
  --name aws-pricing-assistant-daily-crawler

# Check Lambda function
aws lambda get-function \
  --function-name aws-pricing-assistant-crawler

# Check recent invocations
aws lambda list-invocations \
  --function-name aws-pricing-assistant-crawler
```

**Solutions**:

```bash
# Manually invoke crawler
aws lambda invoke \
  --function-name aws-pricing-assistant-crawler \
  --invocation-type RequestResponse \
  output.json

cat output.json

# Check Lambda logs
aws logs tail /aws/lambda/aws-pricing-assistant-crawler --follow

# Update crawler schedule
aws events put-rule \
  --name aws-pricing-assistant-daily-crawler \
  --schedule-expression "cron(0 3 * * ? *)"
```

### Crawler Timeout

**Symptoms**: Lambda function times out

**Solutions**:

```bash
# Increase Lambda timeout
aws lambda update-function-configuration \
  --function-name aws-pricing-assistant-crawler \
  --timeout 900

# Increase memory (improves CPU)
aws lambda update-function-configuration \
  --function-name aws-pricing-assistant-crawler \
  --memory-size 1024

# Split crawler into multiple functions
# Create separate Lambda for each cloud provider
```

### Crawler Data Quality Issues

**Symptoms**: Low quality scores or manual review flags

**Solutions**:

1. Check crawler logs for errors
2. Verify website structure hasn't changed
3. Update crawler selectors in code
4. Improve data validation logic
5. Add more robust error handling

## Performance Issues

### Slow API Response Times

**Diagnosis**:

```bash
# Check ALB metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApplicationELB \
  --metric-name TargetResponseTime \
  --dimensions Name=LoadBalancer,Value=<alb-name> \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average

# Profile application
# Add timing logs to identify bottlenecks
```

**Solutions**:

1. **Enable caching**:
   - Cache service mappings
   - Cache pricing data
   - Use Redis/ElastiCache

2. **Optimize database queries**:
   - Add indexes
   - Use batch operations
   - Implement pagination

3. **Scale infrastructure**:
   - Increase EC2 instance size
   - Add more instances
   - Enable auto-scaling

### High Memory Usage

**Diagnosis**:

```bash
# Check EC2 memory metrics
ssh -i ~/.ssh/aws-pricing-assistant-key.pem ec2-user@<instance-ip>
free -h
top -o %MEM

# Check application memory
ps aux | grep uvicorn
```

**Solutions**:

1. Reduce worker processes
2. Implement memory limits
3. Fix memory leaks in code
4. Upgrade instance type

## Security Issues

### Unauthorized Access Attempts

**Symptoms**: Multiple failed login attempts in logs

**Solutions**:

```bash
# Check CloudWatch logs for failed logins
aws logs filter-log-events \
  --log-group-name /aws/pricing-assistant/production \
  --filter-pattern "401"

# Enable AWS WAF rate limiting
# Create WAF rule to block IPs with >100 requests/5min

# Review security group rules
aws ec2 describe-security-groups \
  --group-ids <sg-id>

# Enable CloudTrail for audit logging
aws cloudtrail create-trail \
  --name pricing-assistant-trail \
  --s3-bucket-name <audit-bucket>
```

### Data Encryption Issues

**Symptoms**: Encryption errors in logs

**Solutions**:

```bash
# Verify encryption keys
aws secretsmanager get-secret-value \
  --secret-id aws-pricing-assistant-secrets

# Regenerate encryption key
python3 scripts/generate_encryption_key.py

# Update Secrets Manager
aws secretsmanager update-secret \
  --secret-id aws-pricing-assistant-secrets \
  --secret-string '{"ENCRYPTION_KEY":"<new-key>"}'

# Restart application
sudo systemctl restart pricing-assistant
```

## Getting Help

If you can't resolve the issue:

1. **Check logs**:
   - Application logs: `/var/log/pricing-assistant/`
   - CloudWatch logs: `/aws/pricing-assistant/production`
   - System logs: `journalctl -u pricing-assistant`

2. **Collect diagnostic information**:
   ```bash
   # System info
   uname -a
   python3 --version
   aws --version
   
   # Application status
   sudo systemctl status pricing-assistant
   
   # Recent errors
   sudo journalctl -u pricing-assistant -n 100 --no-pager
   ```

3. **Contact support**:
   - AWS Support for infrastructure issues
   - Project repository for application issues
   - Include diagnostic information and error messages

## Useful Commands

```bash
# Quick health check
curl http://<alb-url>/health

# View all logs
aws logs tail /aws/pricing-assistant/production --follow

# Restart all services
sudo systemctl restart pricing-assistant

# Check all resources
aws cloudformation describe-stack-resources \
  --stack-name aws-pricing-assistant

# Monitor costs
aws ce get-cost-and-usage \
  --time-period Start=$(date -d '7 days ago' +%Y-%m-%d),End=$(date +%Y-%m-%d) \
  --granularity DAILY \
  --metrics BlendedCost \
  --filter file://cost-filter.json
```
