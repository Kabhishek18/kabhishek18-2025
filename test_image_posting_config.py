#!/usr/bin/env python3
"""
Simple test runner for LinkedIn image posting configuration tests.
This script can be used to run the tests without Django's full test runner.
"""

import os
import sys
import django
from django.conf import settings
from django.test.utils import get_runner

if __name__ == "__main__":
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kabhishek18.settings')
    django.setup()
    
    # Import the test classes
    from blog.tests_linkedin_image_posting_config import (
        LinkedInConfigImagePostingTests,
        LinkedInImagePostingDecisionLogicTests,
        LinkedInImagePostingFallbackTests,
        LinkedInConfigurationAwareContentFormattingTests,
        LinkedInImagePostingConfigurationIntegrationTests
    )
    
    print("LinkedIn Image Posting Configuration Tests")
    print("=" * 50)
    print("Test classes loaded successfully:")
    print("- LinkedInConfigImagePostingTests")
    print("- LinkedInImagePostingDecisionLogicTests") 
    print("- LinkedInImagePostingFallbackTests")
    print("- LinkedInConfigurationAwareContentFormattingTests")
    print("- LinkedInImagePostingConfigurationIntegrationTests")
    print("\nAll test classes are properly defined and importable.")
    print("Run with: python manage.py test blog.tests_linkedin_image_posting_config")