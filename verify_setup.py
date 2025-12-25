"""Verify project setup and structure."""

import os
import sys

def check_directory_structure():
    """Check that all required directories exist."""
    required_dirs = [
        'src',
        'src/api',
        'src/agents',
        'src/services',
        'src/models',
        'src/utils',
        'src/config',
        'frontend',
        'tests',
        'scripts',
        'docs'
    ]
    
    print("Checking directory structure...")
    all_exist = True
    for dir_path in required_dirs:
        exists = os.path.isdir(dir_path)
        status = "✓" if exists else "✗"
        print(f"  {status} {dir_path}")
        if not exists:
            all_exist = False
    
    return all_exist


def check_required_files():
    """Check that all required files exist."""
    required_files = [
        'README.md',
        'requirements.txt',
        '.env.example',
        '.gitignore',
        'setup.py',
        'pytest.ini',
        'Makefile',
        'Dockerfile',
        'docker-compose.yml',
        'QUICKSTART.md',
        'src/__init__.py',
        'src/config/__init__.py',
        'src/config/settings.py',
        'src/config/aws_clients.py',
        'src/utils/__init__.py',
        'src/utils/logger.py',
        'src/api/__init__.py',
        'src/api/main.py',
        'scripts/init_dynamodb.py',
        'tests/__init__.py',
        'tests/conftest.py',
        'tests/test_config.py',
        'docs/DEPLOYMENT.md',
        'docs/DEVELOPMENT.md',
        'frontend/index.html',
        'frontend/styles.css',
        'frontend/app.js'
    ]
    
    print("\nChecking required files...")
    all_exist = True
    for file_path in required_files:
        exists = os.path.isfile(file_path)
        status = "✓" if exists else "✗"
        print(f"  {status} {file_path}")
        if not exists:
            all_exist = False
    
    return all_exist


def main():
    """Run all verification checks."""
    print("=" * 60)
    print("AWS Pricing Assistant - Setup Verification")
    print("=" * 60)
    
    dirs_ok = check_directory_structure()
    files_ok = check_required_files()
    
    print("\n" + "=" * 60)
    if dirs_ok and files_ok:
        print("✓ All checks passed! Project structure is complete.")
        print("\nNext steps:")
        print("  1. Install dependencies: pip install -r requirements.txt")
        print("  2. Configure environment: cp .env.example .env")
        print("  3. Initialize database: python scripts/init_dynamodb.py")
        print("  4. Run application: uvicorn src.api.main:app --reload")
        return 0
    else:
        print("✗ Some checks failed. Please review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
