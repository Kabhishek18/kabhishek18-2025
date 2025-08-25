#!/usr/bin/env python3

import os
import sys
import django

# Add the project directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kabhishek18.settings')
django.setup()

# Now we can import Django models
from blog.services.linkedin_content_formatter import HashtagGenerator

def test_hashtag_generator():
    """Simple test to verify HashtagGenerator works."""
    print("Testing HashtagGenerator...")
    
    # Test initialization
    generator = HashtagGenerator()
    print("✓ HashtagGenerator initialized successfully")
    
    # Test validation
    assert generator.validate_hashtag("python") == True
    assert generator.validate_hashtag("123") == False
    print("✓ Hashtag validation works")
    
    # Test formatting
    assert generator.format_hashtag("Python") == "#python"
    assert generator.format_hashtag("Web Development") == "#webDevelopment"
    print("✓ Hashtag formatting works")
    
    print("All basic tests passed!")

if __name__ == "__main__":
    test_hashtag_simple()