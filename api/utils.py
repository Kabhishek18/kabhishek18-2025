# api/utils.py - API Authentication Utilities

import secrets
import hashlib
import uuid
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from cryptography.fernet import Fernet
from typing import Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class APIKeyGenerator:
    """Utility class for generating and managing API keys"""
    
    @staticmethod
    def generate_secure_key(length: int = 32) -> str:
        """
        Generate a cryptographically secure random API key
        
        Args:
            length: Length of the key in bytes (default 32)
            
        Returns:
            URL-safe base64 encoded string
        """
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def generate_encryption_key() -> bytes:
        """
        Generate a Fernet encryption key
        
        Returns:
            Fernet encryption key as bytes
        """
        return Fernet.generate_key()
    
    @staticmethod
    def hash_api_key(api_key: str) -> str:
        """
        Create a SHA-256 hash of the API key for secure storage
        
        Args:
            api_key: The plain text API key
            
        Returns:
            Hexadecimal hash string
        """
        return hashlib.sha256(api_key.encode('utf-8')).hexdigest()
    
    @staticmethod
    def verify_api_key(api_key: str, stored_hash: str) -> bool:
        """
        Verify an API key against its stored hash
        
        Args:
            api_key: The plain text API key to verify
            stored_hash: The stored hash to compare against
            
        Returns:
            True if the key matches the hash
        """
        return hashlib.sha256(api_key.encode('utf-8')).hexdigest() == stored_hash
    
    @classmethod
    def generate_key_pair(cls, expiration_hours: int = 24) -> Dict[str, any]:
        """
        Generate a complete API key pair with encryption key
        
        Args:
            expiration_hours: Hours until the key expires (default 24)
            
        Returns:
            Dictionary containing api_key, key_hash, encryption_key, and expires_at
        """
        # Generate the API key
        api_key = cls.generate_secure_key()
        
        # Generate encryption key
        encryption_key = cls.generate_encryption_key()
        
        # Create hash for storage
        key_hash = cls.hash_api_key(api_key)
        
        # Calculate expiration
        expires_at = timezone.now() + timedelta(hours=expiration_hours)
        
        return {
            'api_key': api_key,
            'key_hash': key_hash,
            'encryption_key': encryption_key.decode('utf-8'),
            'expires_at': expires_at
        }


class APIKeyValidator:
    """Utility class for validating API keys and checking permissions"""
    
    @staticmethod
    def is_key_expired(expires_at) -> bool:
        """
        Check if an API key has expired
        
        Args:
            expires_at: DateTime when the key expires
            
        Returns:
            True if the key has expired
        """
        return timezone.now() > expires_at
    
    @staticmethod
    def get_expiration_warning(expires_at, warning_hours: int = 2) -> Optional[str]:
        """
        Get a warning message if the key is close to expiration
        
        Args:
            expires_at: DateTime when the key expires
            warning_hours: Hours before expiration to start warning (default 2)
            
        Returns:
            Warning message or None
        """
        time_until_expiry = expires_at - timezone.now()
        warning_threshold = timedelta(hours=warning_hours)
        
        if time_until_expiry <= warning_threshold and time_until_expiry > timedelta(0):
            hours_left = int(time_until_expiry.total_seconds() / 3600)
            minutes_left = int((time_until_expiry.total_seconds() % 3600) / 60)
            
            if hours_left > 0:
                return f"API key expires in {hours_left} hours and {minutes_left} minutes"
            else:
                return f"API key expires in {minutes_left} minutes"
        
        return None
    
    @staticmethod
    def validate_client_permissions(client, action: str) -> Tuple[bool, str]:
        """
        Validate if a client has permission for a specific action
        
        Args:
            client: APIClient instance
            action: Action to check ('read_posts', 'write_posts', 'delete_posts', etc.)
            
        Returns:
            Tuple of (is_allowed, error_message)
        """
        if not client.is_active:
            return False, "Client is inactive"
        
        permission_map = {
            'read_posts': client.can_read_posts,
            'write_posts': client.can_write_posts,
            'delete_posts': client.can_delete_posts,
            'manage_categories': client.can_manage_categories,
            'access_users': client.can_access_users,
            'access_pages': client.can_access_pages,
        }
        
        if action not in permission_map:
            return False, f"Unknown action: {action}"
        
        if not permission_map[action]:
            return False, f"Client does not have permission for: {action}"
        
        return True, ""


class IPValidator:
    """Utility class for IP address validation and restrictions"""
    
    @staticmethod
    def is_ip_allowed(client_ip: str, allowed_ips: list) -> bool:
        """
        Check if a client IP is in the allowed list
        
        Args:
            client_ip: The client's IP address
            allowed_ips: List of allowed IP addresses
            
        Returns:
            True if IP is allowed or no restrictions are set
        """
        if not allowed_ips:  # No restrictions
            return True
        
        return client_ip in allowed_ips
    
    @staticmethod
    def get_client_ip(request) -> str:
        """
        Extract the client's IP address from the request
        
        Args:
            request: Django request object
            
        Returns:
            Client IP address as string
        """
        # Check for forwarded IP first (for load balancers/proxies)
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        
        # Check for real IP (some proxies use this)
        x_real_ip = request.META.get('HTTP_X_REAL_IP')
        if x_real_ip:
            return x_real_ip
        
        # Fall back to remote address
        return request.META.get('REMOTE_ADDR', '')


class RateLimitValidator:
    """Utility class for rate limiting validation"""
    
    @staticmethod
    def check_rate_limit(client, current_usage: Dict[str, int]) -> Tuple[bool, str, Dict[str, int]]:
        """
        Check if client has exceeded rate limits
        
        Args:
            client: APIClient instance
            current_usage: Dictionary with 'minute' and 'hour' usage counts
            
        Returns:
            Tuple of (is_allowed, error_message, retry_after_seconds)
        """
        minute_usage = current_usage.get('minute', 0)
        hour_usage = current_usage.get('hour', 0)
        
        # Check per-minute limit
        if minute_usage >= client.requests_per_minute:
            return False, f"Rate limit exceeded: {minute_usage}/{client.requests_per_minute} requests per minute", {'retry_after': 60}
        
        # Check per-hour limit
        if hour_usage >= client.requests_per_hour:
            return False, f"Rate limit exceeded: {hour_usage}/{client.requests_per_hour} requests per hour", {'retry_after': 3600}
        
        return True, "", {}


class EncryptionUtils:
    """Utility class for encryption and decryption operations"""
    
    @staticmethod
    def encrypt_data(data: str, encryption_key: str) -> str:
        """
        Encrypt data using Fernet encryption
        
        Args:
            data: String data to encrypt
            encryption_key: Base64 encoded Fernet key
            
        Returns:
            Base64 encoded encrypted data
        """
        try:
            fernet = Fernet(encryption_key.encode())
            encrypted_data = fernet.encrypt(data.encode())
            return encrypted_data.decode()
        except Exception as e:
            logger.error(f"Encryption failed: {str(e)}")
            raise ValueError("Failed to encrypt data")
    
    @staticmethod
    def decrypt_data(encrypted_data: str, encryption_key: str) -> str:
        """
        Decrypt data using Fernet encryption
        
        Args:
            encrypted_data: Base64 encoded encrypted data
            encryption_key: Base64 encoded Fernet key
            
        Returns:
            Decrypted string data
        """
        try:
            fernet = Fernet(encryption_key.encode())
            decrypted_data = fernet.decrypt(encrypted_data.encode())
            return decrypted_data.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {str(e)}")
            raise ValueError("Failed to decrypt data")
    
    @staticmethod
    def verify_signature(data: str, signature: str, encryption_key: str) -> bool:
        """
        Verify a data signature using HMAC
        
        Args:
            data: Original data
            signature: Signature to verify
            encryption_key: Key used for signing
            
        Returns:
            True if signature is valid
        """
        import hmac
        try:
            expected_signature = hmac.new(
                encryption_key.encode(),
                data.encode(),
                hashlib.sha256
            ).hexdigest()
            return hmac.compare_digest(signature, expected_signature)
        except Exception as e:
            logger.error(f"Signature verification failed: {str(e)}")
            return False


# Configuration helpers
def get_api_config(key: str, default=None):
    """
    Get API-specific configuration values
    
    Args:
        key: Configuration key
        default: Default value if key not found
        
    Returns:
        Configuration value
    """
    config_map = {
        'DEFAULT_KEY_EXPIRATION_HOURS': getattr(settings, 'API_KEY_EXPIRATION_HOURS', 24),
        'DEFAULT_RATE_LIMIT_PER_MINUTE': getattr(settings, 'API_RATE_LIMIT_PER_MINUTE', 60),
        'DEFAULT_RATE_LIMIT_PER_HOUR': getattr(settings, 'API_RATE_LIMIT_PER_HOUR', 1000),
        'ENABLE_IP_WHITELIST': getattr(settings, 'API_ENABLE_IP_WHITELIST', False),
        'REQUIRE_HTTPS': getattr(settings, 'API_REQUIRE_HTTPS', True),
        'KEY_EXPIRATION_WARNING_HOURS': getattr(settings, 'API_KEY_EXPIRATION_WARNING_HOURS', 2),
    }
    
    return config_map.get(key, default)


# Logging helpers
def log_api_usage(client, endpoint: str, method: str, status_code: int, 
                 response_time: float, request, api_key=None, error_message: str = ""):
    """
    Log API usage for monitoring and analytics
    
    Args:
        client: APIClient instance
        endpoint: API endpoint accessed
        method: HTTP method
        status_code: Response status code
        response_time: Response time in seconds
        request: Django request object
        api_key: APIKey instance (optional)
        error_message: Error message if any
    """
    try:
        from .models import APIUsageLog
        
        # Get request/response sizes (approximate)
        request_size = len(request.body) if hasattr(request, 'body') else 0
        response_size = 0  # This would need to be calculated in middleware
        
        APIUsageLog.objects.create(
            client=client,
            api_key=api_key,
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            response_time=response_time,
            ip_address=IPValidator.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            request_size=request_size,
            response_size=response_size,
            error_message=error_message
        )
    except Exception as e:
        logger.error(f"Failed to log API usage: {str(e)}")