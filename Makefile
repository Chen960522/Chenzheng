.PHONY: help install test lint format clean run init-db setup-kb create-kb

help:
	@echo "AWS Pricing Assistant - Development Commands"
	@echo ""
	@echo "make install     - Install dependencies"
	@echo "make test        - Run tests"
	@echo "make lint        - Run linters"
	@echo "make format      - Format code"
	@echo "make clean       - Clean temporary files"
	@echo "make run         - Run development server"
	@echo "make init-db     - Initialize DynamoDB tables"
	@echo "make setup-kb    - Setup Knowledge Base S3 bucket and upload content"
	@echo "make create-kb   - Create Bedrock Knowledge Base and sync data"

install:
	pip install -r requirements.txt

test:
	pytest

test-cov:
	pytest --cov=src --cov-report=html --cov-report=term

lint:
	flake8 src/ tests/
	mypy src/

format:
	black src/ tests/ scripts/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage

run:
	uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

init-db:
	python scripts/init_dynamodb.py

setup-kb:
	python scripts/setup_knowledge_base_s3.py

create-kb:
	python scripts/create_bedrock_knowledge_base.py
