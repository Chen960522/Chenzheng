# Project Structure

This document describes the complete project structure for AWS Pricing Assistant.

## Directory Structure

```
aws-pricing-assistant/
├── src/                          # Source code
│   ├── __init__.py
│   ├── api/                      # FastAPI endpoints
│   │   ├── __init__.py
│   │   └── main.py              # Main API application
│   ├── agents/                   # Strands Agent implementation
│   │   └── __init__.py
│   ├── services/                 # Business logic services
│   │   └── __init__.py
│   ├── models/                   # Data models and schemas
│   │   └── __init__.py
│   ├── utils/                    # Utility functions
│   │   ├── __init__.py
│   │   └── logger.py            # Logging configuration
│   └── config/                   # Configuration management
│       ├── __init__.py
│       ├── settings.py          # Application settings
│       └── aws_clients.py       # AWS client initialization
│
├── frontend/                     # Web interface
│   ├── index.html               # Main HTML page
│   ├── styles.css               # CSS styles
│   └── app.js                   # JavaScript application
│
├── tests/                        # Test suite
│   ├── __init__.py
│   ├── conftest.py              # Pytest configuration
│   └── test_config.py           # Configuration tests
│
├── scripts/                      # Utility scripts
│   ├── __init__.py
│   └── init_dynamodb.py         # DynamoDB table initialization
│
├── docs/                         # Documentation
│   ├── DEPLOYMENT.md            # Deployment guide
│   └── DEVELOPMENT.md           # Development guide
│
├── .env.example                  # Environment variables template
├── .gitignore                    # Git ignore rules
├── docker-compose.yml            # Docker Compose configuration
├── Dockerfile                    # Docker image definition
├── Makefile                      # Development commands
├── pytest.ini                    # Pytest configuration
├── QUICKSTART.md                 # Quick start guide
├── README.md                     # Project overview
├── requirements.txt              # Python dependencies
├── setup.py                      # Package setup
└── verify_setup.py              # Setup verification script
```

## Key Components

### Configuration (`src/config/`)
- **settings.py**: Centralized configuration using Pydantic Settings
- **aws_clients.py**: Singleton AWS client manager for DynamoDB, S3, Bedrock, etc.

### API (`src/api/`)
- **main.py**: FastAPI application with CORS, health checks, and startup/shutdown events

### Utilities (`src/utils/`)
- **logger.py**: Logging configuration with CloudWatch integration

### Scripts (`scripts/`)
- **init_dynamodb.py**: Creates all required DynamoDB tables with proper indexes and TTL

### Frontend (`frontend/`)
- Basic HTML/CSS/JS structure ready for development

### Tests (`tests/`)
- **conftest.py**: Pytest fixtures and configuration
- **test_config.py**: Configuration module tests

### Documentation (`docs/`)
- **DEPLOYMENT.md**: Complete deployment guide for AWS
- **DEVELOPMENT.md**: Development setup and guidelines

## Configuration Files

### Environment Variables (`.env.example`)
Template for all required environment variables:
- AWS credentials and region
- Bedrock configuration
- DynamoDB table names
- S3 bucket names
- JWT authentication settings
- API configuration
- CloudWatch logging
- Web crawler settings

### Docker Configuration
- **Dockerfile**: Multi-stage build with non-root user
- **docker-compose.yml**: API and frontend services

### Development Tools
- **Makefile**: Common development commands
- **pytest.ini**: Test configuration with coverage
- **setup.py**: Package installation configuration

## DynamoDB Tables

The following tables are created by `scripts/init_dynamodb.py`:

1. **users**: User accounts with username index
2. **sessions**: User sessions with TTL and user index
3. **quotes**: Quote history with user-quotes index
4. **cloud_services**: Crawled cloud service data with category and date indexes
5. **service_mapping_cache**: Cached service mappings

## Next Steps

After setting up the project structure:

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your AWS credentials and settings
   ```

3. **Initialize Database**
   ```bash
   python scripts/init_dynamodb.py
   ```

4. **Run Application**
   ```bash
   uvicorn src.api.main:app --reload
   ```

5. **Verify Setup**
   ```bash
   python verify_setup.py
   ```

## Development Workflow

1. Create feature branch
2. Implement feature in appropriate module
3. Write tests in `tests/`
4. Run tests: `make test`
5. Format code: `make format`
6. Check linting: `make lint`
7. Submit pull request

## Technology Stack

- **Backend**: Python 3.11+, FastAPI, Uvicorn
- **AI/ML**: Amazon Bedrock, Strands Agents SDK, AgentCore
- **Database**: DynamoDB
- **Storage**: S3
- **Authentication**: JWT with Argon2id
- **Testing**: Pytest, Hypothesis
- **Deployment**: Docker, AWS ECS/EC2
- **Monitoring**: CloudWatch

## Status

✅ Project structure complete
✅ Configuration management implemented
✅ AWS client initialization implemented
✅ Logging with CloudWatch integration
✅ FastAPI application skeleton
✅ DynamoDB table initialization script
✅ Docker configuration
✅ Development tools (Makefile, pytest)
✅ Documentation (deployment, development, quickstart)
✅ Frontend skeleton
✅ Test infrastructure

Ready for implementation of core features!
