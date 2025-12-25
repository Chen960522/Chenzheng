#!/usr/bin/env python3
"""Generate encryption key for data encryption."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.encryption import DataEncryption


def main():
    """Generate a new encryption key."""
    print("=" * 60)
    print("AWS Pricing Assistant - Encryption Key Generator")
    print("=" * 60)
    print()
    
    # Generate key
    key = DataEncryption.generate_key()
    
    print("Generated encryption key:")
    print()
    print(f"  {key}")
    print()
    print("To use this key, set the following environment variable:")
    print(f"  export DATA_ENCRYPTION_KEY={key}")
    print()
    print("Or add it to your .env file:")
    print(f"  DATA_ENCRYPTION_KEY={key}")
    print()
    print("IMPORTANT: Keep this key secure!")
    print("- Store it in AWS Secrets Manager or similar secure storage")
    print("- Never commit it to version control")
    print("- If the key is lost, encrypted data cannot be recovered")
    print()


if __name__ == "__main__":
    main()
