"""
Encryption utilities for secure credential management.
Provides encryption/decryption functionality for sensitive data like API tokens.
"""

import base64
import os
from typing import Optional, Union
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
import logging

logger = logging.getLogger(__name__)


class CredentialEncryption:
    """
    Handles encryption and decryption of sensitive credentials.
    Uses Fernet symmetric encryption with key derivation from settings.
    """
    
    def __init__(self):
        self._fernet = None
        self._key = None
    
    def _get_encryption_key(self) -> bytes:
        """
        Get or derive encryption key for sensitive data.
        
        Returns:
            bytes: The encryption key
            
        Raises:
            ImproperlyConfigured: If no encryption key is configured
        """
        if self._key:
            return self._key
        
        # Try to get key from settings
        key = getattr(settings, 'LINKEDIN_ENCRYPTION_KEY', None)
        
        if key:
            if isinstance(key, str):
                # If it's a string, it should be a valid Fernet key (base64 encoded)
                try:
                    # Try to use it directly as a Fernet key
                    self._key = key.encode()
                    return self._key
                except Exception as e:
                    logger.error(f"Failed to use encryption key from settings: {e}")
                    raise ImproperlyConfigured("Invalid LINKEDIN_ENCRYPTION_KEY format")
            elif isinstance(key, bytes):
                self._key = key
                return self._key
        
        # Try to get from environment variable
        env_key = os.environ.get('LINKEDIN_ENCRYPTION_KEY')
        if env_key:
            try:
                # Use the key directly as it's already base64 encoded
                self._key = env_key.encode()
                return self._key
            except Exception as e:
                logger.error(f"Failed to use encryption key from environment: {e}")
                raise ImproperlyConfigured("Invalid LINKEDIN_ENCRYPTION_KEY environment variable")
        
        # Generate a key from Django's SECRET_KEY as fallback
        # This is less secure but allows the system to work without additional configuration
        logger.warning("Using derived key from SECRET_KEY. Consider setting LINKEDIN_ENCRYPTION_KEY for better security.")
        
        secret_key = settings.SECRET_KEY.encode()
        salt = b'linkedin_salt_2024'  # Fixed salt for consistency
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        self._key = base64.urlsafe_b64encode(kdf.derive(secret_key))
        return self._key
    
    def _get_fernet(self) -> Fernet:
        """Get Fernet instance for encryption/decryption."""
        if not self._fernet:
            key = self._get_encryption_key()
            self._fernet = Fernet(key)
        return self._fernet
    
    def encrypt(self, value: Union[str, bytes]) -> str:
        """
        Encrypt a value and return base64 encoded string.
        
        Args:
            value: The value to encrypt (string or bytes)
            
        Returns:
            str: Base64 encoded encrypted value
            
        Raises:
            ValueError: If value is None or empty
        """
        if not value:
            raise ValueError("Cannot encrypt empty or None value")
        
        if isinstance(value, str):
            value = value.encode('utf-8')
        
        try:
            fernet = self._get_fernet()
            encrypted_value = fernet.encrypt(value)
            return base64.b64encode(encrypted_value).decode('utf-8')
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise ValueError(f"Failed to encrypt value: {e}")
    
    def decrypt(self, encrypted_value: str) -> Optional[str]:
        """
        Decrypt a base64 encoded encrypted value.
        
        Args:
            encrypted_value: Base64 encoded encrypted string
            
        Returns:
            str: Decrypted value or None if decryption fails
        """
        if not encrypted_value:
            return None
        
        try:
            fernet = self._get_fernet()
            decoded_value = base64.b64decode(encrypted_value.encode('utf-8'))
            decrypted_value = fernet.decrypt(decoded_value)
            return decrypted_value.decode('utf-8')
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            return None
    
    def is_encrypted(self, value: str) -> bool:
        """
        Check if a value appears to be encrypted.
        
        Args:
            value: The value to check
            
        Returns:
            bool: True if value appears to be encrypted
        """
        if not value:
            return False
        
        try:
            # Try to base64 decode - encrypted values should be base64 encoded
            base64.b64decode(value.encode('utf-8'))
            # If it decodes successfully and is long enough, it might be encrypted
            return len(value) > 50  # Encrypted values are typically longer
        except Exception:
            return False
    
    @classmethod
    def generate_key(cls) -> str:
        """
        Generate a new encryption key for use in settings.
        
        Returns:
            str: Base64 encoded encryption key
        """
        key = Fernet.generate_key()
        return base64.urlsafe_b64encode(key).decode('utf-8')


# Global instance for easy access
credential_encryption = CredentialEncryption()


def encrypt_credential(value: Union[str, bytes]) -> str:
    """
    Convenience function to encrypt a credential.
    
    Args:
        value: The credential to encrypt
        
    Returns:
        str: Encrypted credential
    """
    return credential_encryption.encrypt(value)


def decrypt_credential(encrypted_value: str) -> Optional[str]:
    """
    Convenience function to decrypt a credential.
    
    Args:
        encrypted_value: The encrypted credential
        
    Returns:
        str: Decrypted credential or None if decryption fails
    """
    return credential_encryption.decrypt(encrypted_value)


def is_credential_encrypted(value: str) -> bool:
    """
    Convenience function to check if a credential is encrypted.
    
    Args:
        value: The credential to check
        
    Returns:
        bool: True if credential appears to be encrypted
    """
    return credential_encryption.is_encrypted(value)