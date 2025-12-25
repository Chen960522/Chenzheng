# Development Guide

## Project Structure

```
aws-pricing-assistant/
├── src/
│   ├── api/              # FastAPI endpoints and routes
│   ├── agents/           # Strands Agent implementation
│   ├── services/         # Business logic (parsers, mappers, calculators)
│   ├── models/           # Data models and schemas
│   ├── utils/            # Utility functions (logging, helpers)
│   └── config/           # Configuration management
├── frontend/             # Web interface (HTML/CSS/JS)
├── tests/                # Test suite
├── scripts/              # Utility scripts
└── docs/                 # Documentation
```

## Development Setup

1. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Install development tools:
```bash
pip install black flake8 mypy pytest pytest-cov
```

4. Set up pre-commit hooks (optional):
```bash
pip install pre-commit
pre-commit install
```

## Running Tests

Run all tests:
```bash
pytest
```

Run specific test categories:
```bash
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
pytest -m property      # Property-based tests only
```

Run with coverage:
```bash
pytest --cov=src --cov-report=html
```

## Code Style

Format code with Black:
```bash
black src/ tests/
```

Check code style:
```bash
flake8 src/ tests/
```

Type checking:
```bash
mypy src/
```

## Adding New Features

1. Create feature branch
2. Implement feature with tests
3. Update documentation
4. Run full test suite
5. Submit pull request

## Testing Guidelines

- Write unit tests for all business logic
- Write property-based tests for core algorithms
- Write integration tests for API endpoints
- Aim for >80% code coverage
- Use mocks for external services (AWS, Bedrock)

## Debugging

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Use FastAPI debug mode:
```bash
uvicorn src.api.main:app --reload --log-level debug
```

## Common Tasks

### Add a new API endpoint

1. Create route handler in `src/api/`
2. Add request/response models in `src/models/`
3. Implement business logic in `src/services/`
4. Write tests in `tests/api/`

### Add a new service

1. Create service class in `src/services/`
2. Add data models in `src/models/`
3. Write unit tests in `tests/services/`
4. Write property tests if applicable

### Update configuration

1. Add setting to `src/config/settings.py`
2. Add to `.env.example`
3. Update documentation

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Strands Agents SDK](https://github.com/strands-ai/strands-agents)
- [Amazon Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [Hypothesis (Property Testing)](https://hypothesis.readthedocs.io/)
