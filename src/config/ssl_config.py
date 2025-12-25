"""SSL/TLS configuration for HTTPS enforcement."""

import os
from pathlib import Path
from typing import Optional, Tuple

from src.utils.logger import get_logger

logger = get_logger(__name__)


class SSLConfig:
    """SSL/TLS configuration manager."""
    
    def __init__(self):
        """Initialize SSL configuration."""
        self.cert_path: Optional[Path] = None
        self.key_path: Optional[Path] = None
        self.ca_bundle_path: Optional[Path] = None
        self.enforce_https = os.getenv("ENFORCE_HTTPS", "true").lower() == "true"
        
        # Load certificate paths from environment
        self._load_certificate_paths()
    
    def _load_certificate_paths(self):
        """Load SSL certificate paths from environment variables."""
        cert_path_str = os.getenv("SSL_CERT_PATH")
        key_path_str = os.getenv("SSL_KEY_PATH")
        ca_bundle_str = os.getenv("SSL_CA_BUNDLE_PATH")
        
        if cert_path_str:
            self.cert_path = Path(cert_path_str)
            if not self.cert_path.exists():
                logger.warning(f"SSL certificate not found at {self.cert_path}")
                self.cert_path = None
        
        if key_path_str:
            self.key_path = Path(key_path_str)
            if not self.key_path.exists():
                logger.warning(f"SSL key not found at {self.key_path}")
                self.key_path = None
        
        if ca_bundle_str:
            self.ca_bundle_path = Path(ca_bundle_str)
            if not self.ca_bundle_path.exists():
                logger.warning(f"CA bundle not found at {self.ca_bundle_path}")
                self.ca_bundle_path = None
    
    def get_ssl_context(self) -> Optional[Tuple[str, str]]:
        """
        Get SSL context for uvicorn.
        
        Returns:
            Tuple of (cert_path, key_path) or None if SSL not configured
        """
        if self.cert_path and self.key_path:
            return (str(self.cert_path), str(self.key_path))
        return None
    
    def is_ssl_enabled(self) -> bool:
        """Check if SSL is properly configured."""
        return self.cert_path is not None and self.key_path is not None
    
    def should_enforce_https(self) -> bool:
        """Check if HTTPS should be enforced."""
        return self.enforce_https
    
    def generate_self_signed_cert(self, output_dir: Path):
        """
        Generate self-signed certificate for development.
        
        Args:
            output_dir: Directory to store generated certificates
        
        Note:
            This should only be used for development/testing.
            Production should use proper CA-signed certificates.
        """
        try:
            from cryptography import x509
            from cryptography.x509.oid import NameOID
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.asymmetric import rsa
            from cryptography.hazmat.primitives import serialization
            import datetime
            
            # Generate private key
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
            )
            
            # Generate certificate
            subject = issuer = x509.Name([
                x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
                x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "California"),
                x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "AWS Pricing Assistant"),
                x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
            ])
            
            cert = x509.CertificateBuilder().subject_name(
                subject
            ).issuer_name(
                issuer
            ).public_key(
                private_key.public_key()
            ).serial_number(
                x509.random_serial_number()
            ).not_valid_before(
                datetime.datetime.utcnow()
            ).not_valid_after(
                datetime.datetime.utcnow() + datetime.timedelta(days=365)
            ).add_extension(
                x509.SubjectAlternativeName([
                    x509.DNSName("localhost"),
                    x509.DNSName("127.0.0.1"),
                ]),
                critical=False,
            ).sign(private_key, hashes.SHA256())
            
            # Create output directory
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Write certificate
            cert_path = output_dir / "cert.pem"
            with open(cert_path, "wb") as f:
                f.write(cert.public_bytes(serialization.Encoding.PEM))
            
            # Write private key
            key_path = output_dir / "key.pem"
            with open(key_path, "wb") as f:
                f.write(private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.TraditionalOpenSSL,
                    encryption_algorithm=serialization.NoEncryption()
                ))
            
            self.cert_path = cert_path
            self.key_path = key_path
            
            logger.info(f"Generated self-signed certificate at {cert_path}")
            logger.warning("Self-signed certificates should only be used for development!")
            
        except ImportError:
            logger.error("cryptography package required for certificate generation")
            raise
        except Exception as e:
            logger.error(f"Failed to generate self-signed certificate: {e}")
            raise


# Global SSL configuration instance
ssl_config = SSLConfig()
