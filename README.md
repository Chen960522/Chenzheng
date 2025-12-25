# AWS Pricing Assistant

AWS智能定价助手 - An AI-powered sales support tool that converts cloud service configurations from other providers (Alibaba Cloud, Huawei Cloud, Tencent Cloud, GCP, Azure) into AWS service quotes.

## 🚀 Quick Start

**Ready to deploy?** Choose your preferred method:

- 🎯 **[一键部署](部署说明.md)** - 最简单的部署方式（推荐）
- ✅ **[快速部署检查清单](docs/快速部署检查清单.md)** - 逐步指导
- 📖 **[完整部署指南](docs/部署指南.md)** - 详细文档

### One-Command Deployment

```bash
# Linux/Mac
./一键部署.sh

# Windows
一键部署.bat
```

**Deployment time**: ~30-40 minutes

## Features

- Multi-cloud configuration parsing (JSON, YAML, CSV, plain text)
- Intelligent service mapping using Bedrock Knowledge Base
- AWS pricing calculation across all regions
- Quote generation (PDF, Excel, JSON)
- Web-based user interface
- User authentication and management
- Automated web crawler for cloud service data

## Technology Stack

- **Backend**: Python 3.11+, FastAPI
- **AI/ML**: Amazon Bedrock, Strands Agents SDK, AgentCore
- **Database**: DynamoDB
- **Storage**: S3
- **Authentication**: JWT with Argon2id password hashing
- **Frontend**: HTML5, CSS3, JavaScript

## Project Structure

```
aws-pricing-assistant/
├── src/
│   ├── api/              # FastAPI endpoints
│   ├── agents/           # Strands Agent implementation
│   ├── services/         # Business logic services
│   ├── models/           # Data models
│   ├── utils/            # Utility functions
│   └── config/           # Configuration management
├── frontend/             # Web interface
├── tests/                # Test suite
├── scripts/              # Deployment and utility scripts
└── docs/                 # Documentation
```

## 📚 Documentation

### Deployment Guides
- 🚀 **[部署说明](部署说明.md)** - Start here! (中文)
- ✅ **[快速部署检查清单](docs/快速部署检查清单.md)** - Step-by-step checklist (中文)
- 📖 **[部署指南](docs/部署指南.md)** - Complete deployment guide (中文)
- 📖 **[Deployment Guide](docs/DEPLOYMENT_GUIDE.md)** - Complete deployment guide (English)

### Configuration & Maintenance
- 🔧 **[Configuration Guide](docs/CONFIGURATION.md)** - Environment variables and settings
- 🛠️ **[Troubleshooting](docs/TROUBLESHOOTING.md)** - Common issues and solutions
- 💻 **[Development Guide](docs/DEVELOPMENT.md)** - Local development setup

### Project Documentation
- 📋 **[Project Structure](PROJECT_STRUCTURE.md)** - Code organization
- ✅ **[Project Completion Summary](PROJECT_COMPLETION_SUMMARY.md)** - Development status
- 🎯 **[Production Readiness Checklist](PRODUCTION_READINESS_CHECKLIST.md)** - Pre-deployment checklist

## 🎓 Quick Setup (Development)

For local development:

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your settings
```

3. Set up AWS credentials:
```bash
aws configure
```

4. Initialize DynamoDB tables:
```bash
python scripts/init_dynamodb.py
```

5. Run the application:
```bash
uvicorn src.api.main:app --reload
```

For production deployment, see the [deployment guides](#-documentation) above.

## 💰 Cost Estimate

Based on moderate usage (1000 quotes/month):

- **EC2**: ~$60/month
- **ALB**: ~$20/month
- **DynamoDB**: ~$10/month
- **S3**: ~$5/month
- **CloudFront**: ~$10/month
- **Bedrock**: ~$50/month
- **Other**: ~$10/month

**Total**: ~$165/month

💡 Use Reserved Instances to save up to 70% on EC2 costs.

## 🆘 Support

- 📖 Check the [documentation](#-documentation)
- 🐛 Report issues in the project repository
- 💬 Contact AWS Support for infrastructure issues

## License

Proprietary - Internal Use Only
