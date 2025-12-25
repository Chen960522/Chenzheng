#!/usr/bin/env python3
"""Generate self-signed SSL certificates for development."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.ssl_config import ssl_config
from src.utils.logger import get_logger

logger = get_logger(__name__)


def main():
    """Generate self-signed certificates for development."""
    print("=" * 60)
    print("AWS Pricing Assistant - Development Certificate Generator")
    print("=" * 60)
    print()
    
    # Determine output directory
    certs_dir = Path(__file__).parent.parent / "certs"
    
    print(f"Generating self-signed certificates in: {certs_dir}")
    print()
    print("WARNING: These certificates are for DEVELOPMENT ONLY!")
    print("Do NOT use self-signed certificates in production.")
    print()
    
    try:
        # Generate certificates
        ssl_config.generate_self_signed_cert(certs_dir)
        
        print()
        print("✓ Certificates generated successfully!")
        print()
        print("Certificate files:")
        print(f"  - Certificate: {certs_dir / 'cert.pem'}")
        print(f"  - Private Key: {certs_dir / 'key.pem'}")
        print()
        print("To use these certificates, set the following environment variables:")
        print(f"  export SSL_CERT_PATH={certs_dir / 'cert.pem'}")
        print(f"  export SSL_KEY_PATH={certs_dir / 'key.pem'}")
        print(f"  export ENFORCE_HTTPS=true")
        print()
        print("Or add them to your .env file:")
        print(f"  SSL_CERT_PATH={certs_dir / 'cert.pem'}")
        print(f"  SSL_KEY_PATH={certs_dir / 'key.pem'}")
        print(f"  ENFORCE_HTTPS=true")
        print()
        
    except Exception as e:
        print(f"✗ Error generating certificates: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
