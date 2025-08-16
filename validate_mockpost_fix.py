#!/usr/bin/env python
"""
Quick validation script to test MockPost fixes.
Run this to verify the LinkedIn integration fixes work correctly.
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kabhishek18.settings')
django.setup()

def test_mockpost_attributes():
    """Test that MockPost has all required attributes."""
    print("Testing MockPost attribute fixes...")
    
    try:
        from blog.services.linkedin_service import LinkedInAPIService
        
        # Create LinkedIn service instance
        service = LinkedInAPIService()
        
        # Test _format_post_content method with MockPost
        test_title = "Test Blog Post Title"
        test_content = "This is a test blog post content for LinkedIn integration testing."
        test_url = "https://kabhishek18.com/blog/test-post/"
        
        print(f"Testing with:")
        print(f"  Title: {test_title}")
        print(f"  Content: {test_content[:50]}...")
        print(f"  URL: {test_url}")
        
        # This should not raise AttributeError anymore
        formatted_text = service._format_post_content(test_title, test_content, test_url)
        
        print("✅ SUCCESS: MockPost attributes test passed!")
        print(f"Formatted text length: {len(formatted_text)} characters")
        print(f"Formatted text preview: {formatted_text[:100]}...")
        
        return True
        
    except AttributeError as e:
        if "MockPost" in str(e):
            print(f"❌ FAILED: MockPost still missing attributes: {e}")
            return False
        else:
            print(f"❌ FAILED: Other AttributeError: {e}")
            return False
    except Exception as e:
        print(f"❌ FAILED: Unexpected error: {e}")
        return False

def test_allowed_hosts_config():
    """Test ALLOWED_HOSTS configuration."""
    print("\nTesting ALLOWED_HOSTS configuration...")
    
    try:
        from django.conf import settings
        
        allowed_hosts = settings.ALLOWED_HOSTS
        print(f"Current ALLOWED_HOSTS: {allowed_hosts}")
        
        required_hosts = ['13.200.82.14', 'kabhishek18.com']
        missing_hosts = []
        
        for host in required_hosts:
            if host not in allowed_hosts:
                missing_hosts.append(host)
        
        if missing_hosts:
            print(f"❌ FAILED: Missing required hosts: {missing_hosts}")
            return False
        else:
            print("✅ SUCCESS: All required hosts are in ALLOWED_HOSTS!")
            return True
            
    except Exception as e:
        print(f"❌ FAILED: Error checking ALLOWED_HOSTS: {e}")
        return False

def test_linkedin_service_initialization():
    """Test LinkedIn service can be initialized without errors."""
    print("\nTesting LinkedIn service initialization...")
    
    try:
        from blog.services.linkedin_service import LinkedInAPIService
        
        service = LinkedInAPIService()
        print("✅ SUCCESS: LinkedIn service initialized successfully!")
        
        # Test configuration check
        is_configured = service.is_configured()
        print(f"LinkedIn configured: {is_configured}")
        
        return True
        
    except Exception as e:
        print(f"❌ FAILED: LinkedIn service initialization error: {e}")
        return False

def main():
    """Run all validation tests."""
    print("=" * 60)
    print("LINKEDIN INTEGRATION FIX VALIDATION")
    print("=" * 60)
    
    tests = [
        test_allowed_hosts_config,
        test_linkedin_service_initialization,
        test_mockpost_attributes,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ FAILED: Test {test.__name__} crashed: {e}")
    
    print("\n" + "=" * 60)
    print(f"VALIDATION RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! Ready for production deployment.")
        return 0
    else:
        print("⚠️  SOME TESTS FAILED! Review issues before deployment.")
        return 1

if __name__ == "__main__":
    sys.exit(main())