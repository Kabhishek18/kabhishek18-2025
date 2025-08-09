"""
LinkedIn Configuration Service
Provides utilities for managing and validating LinkedIn API configurations.
"""

import logging
from typing import Optional, Dict, Any
from django.utils import timezone
from django.core.exceptions import ValidationError
from ..linkedin_models import LinkedInConfig
from ..utils.encryption import credential_encryption

logger = logging.getLogger(__name__)


class LinkedInConfigService:
    """Service for managing LinkedIn API configurations"""
    
    @staticmethod
    def get_active_config() -> Optional[LinkedInConfig]:
        """
        Get the active LinkedIn configuration.
        
        Returns:
            LinkedInConfig or None: The active configuration
        """
        return LinkedInConfig.get_active_config()
    
    @staticmethod
    def validate_config(config: LinkedInConfig) -> Dict[str, Any]:
        """
        Validate a LinkedIn configuration comprehensively.
        
        Args:
            config: The configuration to validate
            
        Returns:
            dict: Validation results with detailed information
        """
        results = {
            'is_valid': False,
            'errors': [],
            'warnings': [],
            'credential_status': {},
            'token_status': {},
        }
        
        # Basic validation
        if not config.client_id:
            results['errors'].append("Client ID is required")
        elif len(config.client_id) < 10:
            results['warnings'].append("Client ID appears to be too short")
        
        # Credential validation
        credential_validation = config.validate_credentials()
        results['credential_status'] = credential_validation
        
        if not credential_validation['client_secret_valid']:
            results['errors'].append("Client secret is invalid or cannot be decrypted")
        
        if not credential_validation['access_token_valid']:
            results['errors'].append("Access token is invalid or cannot be decrypted")
        
        if not credential_validation['refresh_token_valid']:
            results['warnings'].append("Refresh token is invalid or missing")
        
        # Token status validation
        token_status = config.get_credential_status()
        results['token_status'] = token_status
        
        if token_status['token_expired']:
            results['errors'].append("Access token has expired")
        elif token_status['needs_refresh']:
            results['warnings'].append("Access token expires soon and should be refreshed")
        
        # Overall validation
        results['is_valid'] = (
            len(results['errors']) == 0 and 
            config.has_valid_credentials()
        )
        
        return results
    
    @staticmethod
    def create_config(client_id: str, client_secret: str, 
                     access_token: str = None, refresh_token: str = None,
                     expires_in: int = None) -> LinkedInConfig:
        """
        Create a new LinkedIn configuration with encrypted credentials.
        
        Args:
            client_id: LinkedIn app client ID
            client_secret: LinkedIn app client secret
            access_token: OAuth access token (optional)
            refresh_token: OAuth refresh token (optional)
            expires_in: Token lifetime in seconds (optional)
            
        Returns:
            LinkedInConfig: The created configuration
            
        Raises:
            ValidationError: If configuration is invalid
        """
        # Deactivate existing configurations
        LinkedInConfig.objects.filter(is_active=True).update(is_active=False)
        
        config = LinkedInConfig(
            client_id=client_id,
            is_active=True
        )
        
        # Set encrypted credentials
        config.set_client_secret(client_secret)
        
        if access_token:
            config.set_access_token(access_token)
        
        if refresh_token:
            config.set_refresh_token(refresh_token)
        
        if expires_in:
            config.token_expires_at = timezone.now() + timezone.timedelta(seconds=expires_in)
        
        # Validate before saving
        config.full_clean()
        config.save()
        
        logger.info(f"Created new LinkedIn configuration {config.id}")
        return config
    
    @staticmethod
    def update_tokens(config: LinkedInConfig, access_token: str,
                     refresh_token: str = None, expires_in: int = None) -> bool:
        """
        Update tokens for an existing configuration.
        
        Args:
            config: The configuration to update
            access_token: New access token
            refresh_token: New refresh token (optional)
            expires_in: Token lifetime in seconds (optional)
            
        Returns:
            bool: True if update was successful
        """
        try:
            config.update_tokens(access_token, refresh_token, expires_in)
            logger.info(f"Updated tokens for LinkedIn configuration {config.id}")
            return True
        except Exception as e:
            logger.error(f"Failed to update tokens for config {config.id}: {e}")
            return False
    
    @staticmethod
    def test_encryption() -> Dict[str, Any]:
        """
        Test the encryption system with sample data.
        
        Returns:
            dict: Test results
        """
        test_data = "test_credential_12345"
        results = {
            'encryption_working': False,
            'decryption_working': False,
            'error': None
        }
        
        try:
            # Test encryption
            encrypted = credential_encryption.encrypt(test_data)
            results['encryption_working'] = True
            
            # Test decryption
            decrypted = credential_encryption.decrypt(encrypted)
            results['decryption_working'] = (decrypted == test_data)
            
        except Exception as e:
            results['error'] = str(e)
            logger.error(f"Encryption test failed: {e}")
        
        return results
    
    @staticmethod
    def get_config_summary() -> Dict[str, Any]:
        """
        Get a summary of all LinkedIn configurations.
        
        Returns:
            dict: Summary information
        """
        configs = LinkedInConfig.objects.all()
        active_config = LinkedInConfig.get_active_config()
        
        summary = {
            'total_configs': configs.count(),
            'active_config_id': active_config.id if active_config else None,
            'has_valid_active_config': False,
            'configs': []
        }
        
        if active_config:
            validation = LinkedInConfigService.validate_config(active_config)
            summary['has_valid_active_config'] = validation['is_valid']
        
        for config in configs:
            config_info = {
                'id': config.id,
                'client_id': config.client_id,
                'is_active': config.is_active,
                'created_at': config.created_at,
                'has_credentials': bool(config.get_client_secret() and config.get_access_token()),
                'token_expired': config.is_token_expired(),
            }
            summary['configs'].append(config_info)
        
        return summary
    
    @staticmethod
    def cleanup_old_configs(keep_count: int = 5) -> int:
        """
        Clean up old inactive configurations, keeping only the most recent ones.
        
        Args:
            keep_count: Number of inactive configs to keep
            
        Returns:
            int: Number of configurations deleted
        """
        # Get inactive configs ordered by creation date (newest first)
        inactive_configs = LinkedInConfig.objects.filter(
            is_active=False
        ).order_by('-created_at')
        
        # Get configs to delete (beyond the keep_count)
        configs_to_delete = inactive_configs[keep_count:]
        
        deleted_count = 0
        for config in configs_to_delete:
            config_id = config.id
            config.delete()
            deleted_count += 1
            logger.info(f"Deleted old LinkedIn configuration {config_id}")
        
        return deleted_count
    
    @staticmethod
    def export_config_data(config: LinkedInConfig, include_secrets: bool = False) -> Dict[str, Any]:
        """
        Export configuration data for backup or migration.
        
        Args:
            config: The configuration to export
            include_secrets: Whether to include decrypted secrets (dangerous!)
            
        Returns:
            dict: Exported configuration data
        """
        data = {
            'id': config.id,
            'client_id': config.client_id,
            'is_active': config.is_active,
            'token_expires_at': config.token_expires_at.isoformat() if config.token_expires_at else None,
            'created_at': config.created_at.isoformat(),
            'updated_at': config.updated_at.isoformat(),
            'has_client_secret': bool(config.client_secret),
            'has_access_token': bool(config.access_token),
            'has_refresh_token': bool(config.refresh_token),
        }
        
        if include_secrets:
            logger.warning(f"Exporting secrets for LinkedIn configuration {config.id}")
            data['secrets'] = {
                'client_secret': config.get_client_secret(),
                'access_token': config.get_access_token(),
                'refresh_token': config.get_refresh_token(),
            }
        
        return data