"""Data encryption utilities for sensitive information."""

import base64
import os
from typing import Optional, Union
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

from src.utils.logger import get_logger

logger = get_logger(__name__)


class DataEncryption:
    """
    Encryption utility for sensitive data.
    
    Uses Fernet (symmetric encryption) for encrypting sensitive fields
    in DynamoDB and other storage systems.
    """
    
    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialize encryption with a key.
        
        Args:
            encryption_key: Base64-encoded encryption key. If not provided,
                          will be loaded from environment variable.
        """
        if encryption_key is None:
            encryption_key = os.getenv("DATA_ENCRYPTION_KEY")
        
        if not encryption_key:
            logger.warning("No encryption key provided - data encryption disabled")
            self._cipher = None
        else:
            try:
                # Decode the key
                key_bytes = base64.urlsafe_b64decode(encryption_key.encode())
                self._cipher = Fernet(key_bytes)
                logger.info("Data encryption initialized")
            except Exception as e:
                logger.error(f"Failed to initialize encryption: {e}")
                self._cipher = None
    
    def is_enabled(self) -> bool:
        """Check if encryption is enabled."""
        return self._cipher is not None
    
    def encrypt(self, data: Union[str, bytes]) -> Optional[str]:
        """
        Encrypt data.
        
        Args:
            data: Data to encrypt (string or bytes)
        
        Returns:
            Base64-encoded encrypted data, or None if encryption disabled
        """
        if not self.is_enabled():
            logger.warning("Encryption not enabled - returning data as-is")
            return data if isinstance(data, str) else data.decode('utf-8')
        
        try:
            # Convert to bytes if string
            if isinstance(data, str):
                data = data.encode('utf-8')
            
            # Encrypt
            encrypted = self._cipher.encrypt(data)
            
            # Return as base64 string
            return base64.urlsafe_b64encode(encrypted).decode('utf-8')
        
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise
    
    def decrypt(self, encrypted_data: str) -> Optional[str]:
        """
        Decrypt data.
        
        Args:
            encrypted_data: Base64-encoded encrypted data
        
        Returns:
            Decrypted data as string, or None if decryption failed
        """
        if not self.is_enabled():
            logger.warning("Encryption not enabled - returning data as-is")
            return encrypted_data
        
        try:
            # Decode from base64
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
            
            # Decrypt
            decrypted = self._cipher.decrypt(encrypted_bytes)
            
            # Return as string
            return decrypted.decode('utf-8')
        
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise
    
    @staticmethod
    def generate_key() -> str:
        """
        Generate a new encryption key.
        
        Returns:
            Base64-encoded encryption key
        """
        key = Fernet.generate_key()
        return base64.urlsafe_b64encode(key).decode('utf-8')
    
    @staticmethod
    def derive_key_from_password(password: str, salt: Optional[bytes] = None) -> tuple[str, str]:
        """
        Derive an encryption key from a password.
        
        Args:
            password: Password to derive key from
            salt: Optional salt (will be generated if not provided)
        
        Returns:
            Tuple of (base64-encoded key, base64-encoded salt)
        """
        if salt is None:
            salt = os.urandom(16)
        
        # Use PBKDF2 to derive key
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        
        return (
            key.decode('utf-8'),
            base64.urlsafe_b64encode(salt).decode('utf-8')
        )


class FieldEncryption:
    """
    Helper for encrypting specific fields in data structures.
    
    This class provides utilities for selectively encrypting sensitive fields
    in dictionaries (e.g., before storing in DynamoDB).
    """
    
    def __init__(self, encryption: DataEncryption):
        """
        Initialize field encryption.
        
        Args:
            encryption: DataEncryption instance
        """
        self.encryption = encryption
    
    def encrypt_fields(self, data: dict, fields: list[str]) -> dict:
        """
        Encrypt specified fields in a dictionary.
        
        Args:
            data: Dictionary containing data
            fields: List of field names to encrypt
        
        Returns:
            Dictionary with encrypted fields
        """
        if not self.encryption.is_enabled():
            return data
        
        encrypted_data = data.copy()
        
        for field in fields:
            if field in encrypted_data and encrypted_data[field] is not None:
                try:
                    encrypted_data[field] = self.encryption.encrypt(str(encrypted_data[field]))
                    # Mark field as encrypted
                    encrypted_data[f"__{field}_encrypted"] = True
                except Exception as e:
                    logger.error(f"Failed to encrypt field {field}: {e}")
        
        return encrypted_data
    
    def decrypt_fields(self, data: dict, fields: list[str]) -> dict:
        """
        Decrypt specified fields in a dictionary.
        
        Args:
            data: Dictionary containing encrypted data
            fields: List of field names to decrypt
        
        Returns:
            Dictionary with decrypted fields
        """
        if not self.encryption.is_enabled():
            return data
        
        decrypted_data = data.copy()
        
        for field in fields:
            # Check if field is marked as encrypted
            if decrypted_data.get(f"__{field}_encrypted"):
                try:
                    decrypted_data[field] = self.encryption.decrypt(decrypted_data[field])
                    # Remove encryption marker
                    del decrypted_data[f"__{field}_encrypted"]
                except Exception as e:
                    logger.error(f"Failed to decrypt field {field}: {e}")
        
        return decrypted_data


# Global encryption instance
_encryption_instance = None


def get_encryption() -> DataEncryption:
    """Get global encryption instance."""
    global _encryption_instance
    if _encryption_instance is None:
        _encryption_instance = DataEncryption()
    return _encryption_instance


def get_field_encryption() -> FieldEncryption:
    """Get field encryption helper."""
    return FieldEncryption(get_encryption())



# Convenience functions for direct use
def encrypt_sensitive_data(data: Union[str, bytes]) -> Optional[str]:
    """
    Encrypt sensitive data using the global encryption instance.
    
    Args:
        data: Data to encrypt
    
    Returns:
        Encrypted data as base64 string
    """
    return get_encryption().encrypt(data)


def decrypt_sensitive_data(encrypted_data: str) -> Optional[str]:
    """
    Decrypt sensitive data using the global encryption instance.
    
    Args:
        encrypted_data: Base64-encoded encrypted data
    
    Returns:
        Decrypted data as string
    """
    return get_encryption().decrypt(encrypted_data)


def encrypt_dict_fields(data: dict, fields: list[str]) -> dict:
    """
    Encrypt specified fields in a dictionary.
    
    Args:
        data: Dictionary containing data
        fields: List of field names to encrypt
    
    Returns:
        Dictionary with encrypted fields
    """
    return get_field_encryption().encrypt_fields(data, fields)


def decrypt_dict_fields(data: dict, fields: list[str]) -> dict:
    """
    Decrypt specified fields in a dictionary.
    
    Args:
        data: Dictionary containing encrypted data
        fields: List of field names to decrypt
    
    Returns:
        Dictionary with decrypted fields
    """
    return get_field_encryption().decrypt_fields(data, fields)
