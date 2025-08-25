#!/usr/bin/env python3
"""
Test script to verify LinkedIn image posting configuration is respected.
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'your_project.settings')
django.setup()

from blog.linkedin_models import LinkedInConfig
from blog.services.linkedin_service import LinkedInAPIService

def test_image_posting_config():
    """Test that image posting configuration is properly respected."""
    
    print("Testing LinkedIn image posting configuration...")
    
    # Get or create a LinkedIn config
    config, created = LinkedInConfig.objects.get_or_create(
        defaults={
            'client_id': 'test_client_id',
            'client_secret': 'test_secret',
            'is_active': True,
            'enable_image_posting': False,  # Disable image posting
            'image_posting_strategy': 'never'
        }
    )
    
    if not created:
        # Update existing config to disable image posting
        config.enable_image_posting = False
        config.image_posting_strategy = 'never'
        config.save()
    
    print(f"Config created/updated: enable_image_posting={config.enable_image_posting}")
    
    # Test the should_include_image_in_post method
    should_include = config.should_include_image_in_post()
    print(f"should_include_image_in_post() returned: {should_include}")
    
    if should_include:
        print("❌ FAIL: Image posting should be disabled but method returned True")
        return False
    else:
        print("✅ PASS: Image posting correctly disabled")
    
    # Test with image posting enabled
    config.enable_image_posting = True
    config.image_posting_strategy = 'always'
    config.save()
    
    should_include = config.should_include_image_in_post()
    print(f"After enabling: should_include_image_in_post() returned: {should_include}")
    
    if not should_include:
        print("❌ FAIL: Image posting should be enabled but method returned False")
        return False
    else:
        print("✅ PASS: Image posting correctly enabled")
    
    return True

if __name__ == "__main__":
    try:
        success = test_image_posting_config()
        if success:
            print("\n🎉 All tests passed!")
            sys.exit(0)
        else:
            print("\n💥 Some tests failed!")
            sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)