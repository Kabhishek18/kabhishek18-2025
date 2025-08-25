#!/usr/bin/env python3
"""
Test script to verify LinkedIn service respects image posting configuration.
"""

import os
import sys
import django
from unittest.mock import Mock, patch

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kabhishek18.settings')
django.setup()

from blog.linkedin_models import LinkedInConfig
from blog.services.linkedin_service import LinkedInAPIService

def test_linkedin_service_config():
    """Test that LinkedIn service respects image posting configuration."""
    
    print("Testing LinkedIn service image posting configuration...")
    
    # Create a test config with image posting disabled
    config = LinkedInConfig(
        client_id='test_client_id',
        client_secret='test_secret',
        is_active=True,
        enable_image_posting=False,  # Disable image posting
        image_posting_strategy='never'
    )
    
    # Mock the encryption/decryption methods
    with patch.object(config, 'get_client_secret', return_value='test_secret'):
        with patch.object(config, 'get_access_token', return_value='test_token'):
            with patch.object(config, 'is_token_expired', return_value=False):
                
                # Create service instance
                service = LinkedInAPIService(config=config)
                
                # Mock the _create_text_only_post method to avoid actual API calls
                with patch.object(service, '_create_text_only_post') as mock_text_post:
                    mock_text_post.return_value = {
                        'id': 'test_post_id',
                        'created': True,
                        '_media_info': {
                            'has_media': False,
                            'fallback_used': True,
                            'original_image_url': 'https://example.com/image.jpg'
                        }
                    }
                    
                    # Test 1: Image posting disabled - should create text-only post
                    print("\nTest 1: Image posting disabled")
                    result = service.create_post(
                        title="Test Post",
                        content="Test content",
                        url="https://example.com",
                        image_url="https://example.com/image.jpg"
                    )
                    
                    # Verify text-only post was called
                    mock_text_post.assert_called_once()
                    
                    # Verify media info indicates fallback was used
                    media_info = result.get('_media_info', {})
                    if media_info.get('fallback_used') and not media_info.get('has_media'):
                        print("✅ PASS: Image was ignored, text-only post created")
                    else:
                        print("❌ FAIL: Image should have been ignored")
                        return False
                
                # Test 2: Image posting enabled
                print("\nTest 2: Image posting enabled")
                config.enable_image_posting = True
                config.image_posting_strategy = 'always'
                
                # Mock the upload_media and create_post_with_media methods
                with patch.object(service, 'upload_media') as mock_upload:
                    with patch.object(service, 'create_post_with_media') as mock_media_post:
                        mock_upload.return_value = 'urn:li:digitalmediaAsset:test123'
                        mock_media_post.return_value = {
                            'id': 'test_post_with_media_id',
                            'created': True,
                            '_media_info': {
                                'has_media': True,
                                'fallback_used': False,
                                'media_urn': 'urn:li:digitalmediaAsset:test123'
                            }
                        }
                        
                        result = service.create_post(
                            title="Test Post with Image",
                            content="Test content",
                            url="https://example.com",
                            image_url="https://example.com/image.jpg"
                        )
                        
                        # Verify media upload and post creation were called
                        mock_upload.assert_called_once_with("https://example.com/image.jpg")
                        mock_media_post.assert_called_once()
                        
                        # Verify media info indicates image was used
                        media_info = result.get('_media_info', {})
                        if media_info.get('has_media') and not media_info.get('fallback_used'):
                            print("✅ PASS: Image was included in post")
                        else:
                            print("❌ FAIL: Image should have been included")
                            return False
    
    return True

if __name__ == "__main__":
    try:
        success = test_linkedin_service_config()
        if success:
            print("\n🎉 All LinkedIn service configuration tests passed!")
            sys.exit(0)
        else:
            print("\n💥 Some tests failed!")
            sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)