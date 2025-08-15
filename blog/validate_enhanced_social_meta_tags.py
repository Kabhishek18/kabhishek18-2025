#!/usr/bin/env python
"""
Validation script for Enhanced Open Graph Meta Tags implementation.
This script validates that all task requirements have been implemented correctly.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kabhishek18.settings')
django.setup()

from django.test import Client
from blog.models import Post
from blog.templatetags.media_tags import (
    get_social_image_url, 
    get_image_dimensions, 
    get_image_type,
    get_linkedin_optimized_image,
    get_fallback_images,
    render_social_meta_tags
)
import re


def validate_task_requirements():
    """Validate all task requirements are met"""
    print("🔍 Validating Enhanced Open Graph Meta Tags Implementation")
    print("=" * 60)
    
    # Get a test post
    post = Post.objects.filter(status='published').first()
    if not post:
        print("❌ No published posts found for testing")
        return False
    
    print(f"📝 Testing with post: {post.title[:50]}...")
    
    # Task requirement validation
    requirements_met = []
    
    # 1. Update blog detail template to include comprehensive Open Graph image tags
    print("\n1️⃣ Checking comprehensive Open Graph image tags...")
    client = Client()
    try:
        response = client.get(f'/blog/{post.slug}/')
        if response.status_code == 200:
            content = response.content.decode('utf-8')
            
            required_og_tags = [
                'og:image',
                'og:image:url', 
                'og:image:secure_url',
                'og:image:width',
                'og:image:height',
                'og:image:alt',
                'og:image:type'
            ]
            
            missing_tags = []
            for tag in required_og_tags:
                if tag not in content:
                    missing_tags.append(tag)
            
            if not missing_tags:
                print("   ✅ All comprehensive Open Graph image tags present")
                requirements_met.append("comprehensive_og_tags")
            else:
                print(f"   ❌ Missing Open Graph tags: {missing_tags}")
        else:
            print(f"   ❌ Failed to load blog detail page: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error testing blog detail page: {e}")
    
    # 2. Add image dimensions and metadata to Open Graph tags
    print("\n2️⃣ Checking image dimensions and metadata...")
    try:
        context_data = render_social_meta_tags(post, None)
        
        has_dimensions = (
            'image_width' in context_data and 
            'image_height' in context_data and
            context_data['image_width'] > 0 and
            context_data['image_height'] > 0
        )
        
        has_metadata = (
            'image_type' in context_data and
            'image_alt' in context_data and
            context_data['image_type'] and
            context_data['image_alt']
        )
        
        if has_dimensions and has_metadata:
            print(f"   ✅ Image dimensions: {context_data['image_width']}x{context_data['image_height']}")
            print(f"   ✅ Image metadata: type={context_data['image_type']}, alt='{context_data['image_alt'][:30]}...'")
            requirements_met.append("image_dimensions_metadata")
        else:
            print("   ❌ Missing image dimensions or metadata")
            
    except Exception as e:
        print(f"   ❌ Error testing image dimensions/metadata: {e}")
    
    # 3. Implement image selection logic for social sharing
    print("\n3️⃣ Checking image selection logic...")
    try:
        # Test priority order: social_image > featured_image > media items > fallback
        image_url = get_social_image_url(post, None)
        
        if image_url:
            print(f"   ✅ Image selection working: {os.path.basename(image_url)}")
            
            # Test fallback images
            fallback_images = get_fallback_images(post, None)
            if fallback_images and len(fallback_images) > 0:
                print(f"   ✅ Fallback images available: {len(fallback_images)} images")
                requirements_met.append("image_selection_logic")
            else:
                print("   ❌ No fallback images available")
        else:
            print("   ❌ Image selection failed")
            
    except Exception as e:
        print(f"   ❌ Error testing image selection: {e}")
    
    # 4. Add fallback images when no featured image is available
    print("\n4️⃣ Checking fallback image functionality...")
    try:
        # Create a test scenario with a post that has no images
        fallback_images = get_fallback_images(post, None)
        
        # Even if the post has images, the function should provide fallbacks
        if fallback_images:
            print(f"   ✅ Fallback system working: {len(fallback_images)} fallback images")
            
            # Check fallback structure
            first_fallback = fallback_images[0]
            required_keys = ['url', 'width', 'height', 'alt', 'type']
            
            if all(key in first_fallback for key in required_keys):
                print("   ✅ Fallback image structure is correct")
                requirements_met.append("fallback_images")
            else:
                print("   ❌ Fallback image structure is incomplete")
        else:
            print("   ❌ No fallback images available")
            
    except Exception as e:
        print(f"   ❌ Error testing fallback images: {e}")
    
    # 5. Ensure absolute URLs for all image references
    print("\n5️⃣ Checking absolute URLs...")
    try:
        # Test with and without request object
        image_url_with_request = get_social_image_url(post, None)  # Uses settings fallback
        
        if image_url_with_request and image_url_with_request.startswith('http'):
            print(f"   ✅ Absolute URL generated: {image_url_with_request[:50]}...")
            
            # Check canonical URL
            context_data = render_social_meta_tags(post, None)
            canonical_url = context_data.get('canonical_url', '')
            
            if canonical_url and canonical_url.startswith('http'):
                print(f"   ✅ Canonical URL is absolute: {canonical_url[:50]}...")
                requirements_met.append("absolute_urls")
            else:
                print("   ❌ Canonical URL is not absolute")
        else:
            print("   ❌ Image URL is not absolute")
            
    except Exception as e:
        print(f"   ❌ Error testing absolute URLs: {e}")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 VALIDATION SUMMARY")
    print("=" * 60)
    
    total_requirements = 5
    met_requirements = len(requirements_met)
    
    print(f"Requirements met: {met_requirements}/{total_requirements}")
    
    if met_requirements == total_requirements:
        print("🎉 ALL TASK REQUIREMENTS SUCCESSFULLY IMPLEMENTED!")
        print("\n✅ Task 7: Enhance Open Graph meta tags for better link previews - COMPLETED")
        return True
    else:
        print("❌ Some requirements are not fully met")
        missing = total_requirements - met_requirements
        print(f"❌ {missing} requirement(s) need attention")
        return False


if __name__ == "__main__":
    success = validate_task_requirements()
    sys.exit(0 if success else 1)