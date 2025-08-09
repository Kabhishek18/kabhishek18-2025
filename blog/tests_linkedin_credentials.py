"""
Tests for LinkedIn credential management functionality.
"""

from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from blog.linkedin_models import LinkedInConfig
from blog.services.linkedin_config_service import LinkedInConfigService
from blog.utils.encryption import credential_encryption


class CredentialEncryptionTests(TestCase):
    """Test encryption utilities"""
    
    def test_encrypt_decrypt_cycle(self):
        """Test that encryption and decryption work correctly"""
        original_value = "test_secret_12345"
        encrypted = credential_encryption.encrypt(original_value)
        decrypted = credential_encryption.decrypt(encrypted)
        
        self.assertEqual(original_value, decrypted)
        self.assertNotEqual(original_value, encrypted)
        self.assertTrue(len(encrypted) > len(original_value))
    
    def test_encrypt_empty_value(self):
        """Test encryption of empty values"""
        with self.assertRaises(ValueError):
            credential_encryption.encrypt("")
        
        with self.assertRaises(ValueError):
            credential_encryption.encrypt(None)
    
    def test_decrypt_invalid_value(self):
        """Test decryption of invalid values"""
        result = credential_encryption.decrypt("invalid_encrypted_data")
        self.assertIsNone(result)
        
        result = credential_encryption.decrypt("")
        self.assertIsNone(result)
    
    def test_is_encrypted_detection(self):
        """Test detection of encrypted values"""
        plain_text = "plain_text"
        encrypted_text = credential_encryption.encrypt("test_value")
        
        self.assertFalse(credential_encryption.is_encrypted(plain_text))
        self.assertTrue(credential_encryption.is_encrypted(encrypted_text))


class LinkedInConfigTests(TestCase):
    """Test LinkedIn configuration model"""
    
    def test_create_config(self):
        """Test creating a LinkedIn configuration"""
        config = LinkedInConfig.objects.create(
            client_id="test_client_id",
            is_active=True
        )
        
        config.set_client_secret("test_secret")
        config.set_access_token("test_token")
        
        self.assertEqual(config.client_id, "test_client_id")
        self.assertEqual(config.get_client_secret(), "test_secret")
        self.assertEqual(config.get_access_token(), "test_token")
        self.assertTrue(config.is_active)
    
    def test_only_one_active_config(self):
        """Test that only one active configuration is allowed"""
        # Create first active config
        config1 = LinkedInConfig.objects.create(
            client_id="test_client_1",
            is_active=True
        )
        
        # Try to create second active config
        config2 = LinkedInConfig(
            client_id="test_client_2",
            is_active=True
        )
        
        with self.assertRaises(ValidationError):
            config2.full_clean()
    
    def test_token_expiration(self):
        """Test token expiration functionality"""
        config = LinkedInConfig.objects.create(
            client_id="test_client_id",
            is_active=True
        )
        
        # Test with no expiration date
        self.assertTrue(config.is_token_expired())
        
        # Test with future expiration
        config.token_expires_at = timezone.now() + timedelta(hours=1)
        self.assertFalse(config.is_token_expired())
        
        # Test with past expiration
        config.token_expires_at = timezone.now() - timedelta(hours=1)
        self.assertTrue(config.is_token_expired())
    
    def test_needs_token_refresh(self):
        """Test token refresh detection"""
        config = LinkedInConfig.objects.create(
            client_id="test_client_id",
            is_active=True
        )
        
        # No expiration date
        self.assertTrue(config.needs_token_refresh())
        
        # Expires in 1 hour (within default 30 min buffer)
        config.token_expires_at = timezone.now() + timedelta(minutes=15)
        self.assertTrue(config.needs_token_refresh())
        
        # Expires in 2 hours (outside buffer)
        config.token_expires_at = timezone.now() + timedelta(hours=2)
        self.assertFalse(config.needs_token_refresh())


class LinkedInConfigServiceTests(TestCase):
    """Test LinkedIn configuration service"""
    
    def test_create_config_service(self):
        """Test creating config through service"""
        config = LinkedInConfigService.create_config(
            client_id="service_test_id",
            client_secret="service_test_secret",
            access_token="service_test_token",
            expires_in=3600
        )
        
        self.assertEqual(config.client_id, "service_test_id")
        self.assertEqual(config.get_client_secret(), "service_test_secret")
        self.assertEqual(config.get_access_token(), "service_test_token")
        self.assertTrue(config.is_active)
        self.assertIsNotNone(config.token_expires_at)
    
    def test_validate_config(self):
        """Test configuration validation"""
        config = LinkedInConfig.objects.create(
            client_id="test_client_id",
            is_active=True
        )
        config.set_client_secret("test_secret")
        
        validation = LinkedInConfigService.validate_config(config)
        
        self.assertFalse(validation['is_valid'])  # No access token
        self.assertTrue(validation['credential_status']['client_secret_valid'])
        self.assertFalse(validation['credential_status']['access_token_valid'])
    
    def test_encryption_test(self):
        """Test encryption system test"""
        result = LinkedInConfigService.test_encryption()
        
        self.assertTrue(result['encryption_working'])
        self.assertTrue(result['decryption_working'])
        self.assertIsNone(result['error'])