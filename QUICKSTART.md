# Quick Start Guide

Get AWS Pricing Assistant up and running in 5 minutes!

## Prerequisites

- Python 3.11+
- AWS Account with Bedrock access
- AWS CLI configured

## Step 1: Install Dependencies

```bash
cd aws-pricing-assistant
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Step 2: Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and set:
- `AWS_REGION` - Your AWS region
- `BEDROCK_KNOWLEDGE_BASE_ID` - Your Bedrock KB ID (optional for now)
- `JWT_SECRET_KEY` - A secure random string

## Step 3: Initialize Database

```bash
python scripts/init_dynamodb.py
```

This creates the required DynamoDB tables.

## Step 4: Run the Application

```bash
uvicorn src.api.main:app --reload
```

The API will be available at http://localhost:8000

## Step 5: Test the API

Open http://localhost:8000/docs to see the interactive API documentation.

Test the health endpoint:
```bash
curl http://localhost:8000/health
```

## Next Steps

1. Set up Bedrock Knowledge Base (see docs/DEPLOYMENT.md)
2. Configure web crawler for cloud service data
3. Create admin user account
4. Explore the API documentation
5. Customize the frontend

## Using Docker (Alternative)

```bash
docker-compose up
```

Access:
- API: http://localhost:8000
- Frontend: http://localhost:3000

## Troubleshooting

**Issue**: Import errors
**Solution**: Make sure you're in the virtual environment and all dependencies are installed

**Issue**: AWS credentials not found
**Solution**: Configure AWS CLI or set environment variables

**Issue**: Bedrock access denied
**Solution**: Ensure your AWS account has Bedrock access enabled in the console

## Getting Help

- Check the logs in `logs/` directory
- Review documentation in `docs/`
- Check CloudWatch logs if deployed to AWS

## Development Mode

For development with auto-reload:
```bash
make run
```

Run tests:
```bash
make test
```

Format code:
```bash
make format
```
