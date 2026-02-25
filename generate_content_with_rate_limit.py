#!/usr/bin/env python3
"""
Generate Content with Rate Limit Handling

This script generates high-quality content while respecting Gemini API rate limits.
It automatically waits between requests to avoid quota exceeded errors.
"""

import os
import sys
import time
import django
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kabhishek18.settings')
django.setup()

from django.core.management import call_command

def generate_content_with_delays(count=5, min_quality=85):
    """Generate content with automatic rate limiting"""
    
    print("🚀 Generating High-Quality Content with Rate Limiting")
    print("=" * 60)
    print(f"Target: {count} posts with {min_quality}+ quality score")
    print("Rate Limit: 90 seconds between posts (safe for free tier)")
    print("")
    
    successful_posts = 0
    failed_posts = 0
    
    for i in range(count):
        print(f"📝 Generating Post {i + 1}/{count}")
        print(f"Time: {datetime.now().strftime('%H:%M:%S')}")
        
        try:
            # Generate single post
            call_command(
                'generate_crag_content',
                count=1,
                min_quality=min_quality,
                publish=False,  # Save as draft for review
                verbosity=1
            )
            
            successful_posts += 1
            print(f"✅ Post {i + 1} generated successfully")
            
        except Exception as e:
            failed_posts += 1
            print(f"❌ Post {i + 1} failed: {str(e)}")
            
            # If rate limit error, wait longer
            if "429" in str(e) or "quota" in str(e).lower():
                print("⏳ Rate limit detected, waiting 2 minutes...")
                time.sleep(120)  # Wait 2 minutes for rate limit
        
        # Wait between posts (except for the last one)
        if i < count - 1:
            print("⏳ Waiting 90 seconds to respect rate limits...")
            for remaining in range(90, 0, -10):
                print(f"   {remaining} seconds remaining...", end='\r')
                time.sleep(10)
            print("   Ready for next post!        ")
            print("")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 GENERATION SUMMARY")
    print("=" * 60)
    print(f"✅ Successful: {successful_posts}/{count}")
    print(f"❌ Failed: {failed_posts}/{count}")
    
    if successful_posts > 0:
        print(f"\n📝 Next Steps:")
        print(f"1. Review generated posts in Django admin")
        print(f"2. Publish high-quality posts")
        print(f"3. Continue generating until you have 20+ total posts")
        print(f"4. Run quality audit: python manage.py upgrade_to_crag --audit-only")

def regenerate_low_quality_with_delays(max_posts=2):
    """Regenerate low-quality posts with rate limiting"""
    
    print("🔧 Regenerating Low-Quality Posts with Rate Limiting")
    print("=" * 60)
    print(f"Target: Up to {max_posts} low-quality posts")
    print("Rate Limit: 2 minutes between posts")
    print("")
    
    for i in range(max_posts):
        print(f"🔄 Regenerating Post {i + 1}/{max_posts}")
        print(f"Time: {datetime.now().strftime('%H:%M:%S')}")
        
        try:
            call_command(
                'upgrade_to_crag',
                regenerate_low_quality=True,
                max_posts=1,  # One at a time
                verbosity=1
            )
            
            print(f"✅ Regeneration {i + 1} completed")
            
        except Exception as e:
            print(f"❌ Regeneration {i + 1} failed: {str(e)}")
            
            # If rate limit error, wait longer
            if "429" in str(e) or "quota" in str(e).lower():
                print("⏳ Rate limit detected, waiting 3 minutes...")
                time.sleep(180)
        
        # Wait between regenerations
        if i < max_posts - 1:
            print("⏳ Waiting 2 minutes for rate limit...")
            for remaining in range(120, 0, -10):
                print(f"   {remaining} seconds remaining...", end='\r')
                time.sleep(10)
            print("   Ready for next regeneration!")
            print("")

def main():
    """Main function with user choices"""
    
    print("🎯 Content Generation with Rate Limit Management")
    print("=" * 60)
    print("")
    print("Choose an option:")
    print("1. Generate new high-quality posts (recommended)")
    print("2. Regenerate existing low-quality posts")
    print("3. Generate 1 post quickly (test)")
    print("4. Exit")
    print("")
    
    try:
        choice = input("Enter your choice (1-4): ").strip()
        
        if choice == "1":
            count = input("How many posts to generate? (default: 5): ").strip()
            count = int(count) if count else 5
            
            quality = input("Minimum quality score? (default: 85): ").strip()
            quality = int(quality) if quality else 85
            
            generate_content_with_delays(count, quality)
            
        elif choice == "2":
            max_posts = input("Max posts to regenerate? (default: 2): ").strip()
            max_posts = int(max_posts) if max_posts else 2
            
            regenerate_low_quality_with_delays(max_posts)
            
        elif choice == "3":
            print("🧪 Generating 1 test post...")
            generate_content_with_delays(1, 85)
            
        elif choice == "4":
            print("👋 Goodbye!")
            
        else:
            print("❌ Invalid choice")
            
    except KeyboardInterrupt:
        print("\n\n⏹️ Generation stopped by user")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")

if __name__ == "__main__":
    main()