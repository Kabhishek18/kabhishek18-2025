#!/usr/bin/env python
"""
Demo script to showcase social sharing functionality.
Run this script to see the social sharing features in action.
"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kabhishek18.settings')
django.setup()

from django.contrib.auth.models import User
from blog.models import Post, Category, SocialShare
from blog.services import SocialShareService


def create_demo_data():
    """Create demo blog post and user for testing."""
    print("Creating demo data...")
    
    # Create user if doesn't exist
    user, created = User.objects.get_or_create(
        username='demo_user',
        defaults={
            'email': 'demo@example.com',
            'first_name': 'Demo',
            'last_name': 'User'
        }
    )
    if created:
        print(f"✓ Created user: {user.username}")
    else:
        print(f"✓ Using existing user: {user.username}")
    
    # Create category if doesn't exist
    category, created = Category.objects.get_or_create(
        name='Demo Category',
        defaults={'slug': 'demo-category'}
    )
    if created:
        print(f"✓ Created category: {category.name}")
    else:
        print(f"✓ Using existing category: {category.name}")
    
    # Create demo post if doesn't exist
    post, created = Post.objects.get_or_create(
        slug='demo-social-sharing-post',
        defaults={
            'title': 'Demo Social Sharing Post',
            'author': user,
            'content': '<p>This is a demo post to showcase social sharing functionality.</p>',
            'excerpt': 'A demo post for testing social sharing features.',
            'status': 'published'
        }
    )
    if created:
        post.categories.add(category)
        print(f"✓ Created post: {post.title}")
    else:
        print(f"✓ Using existing post: {post.title}")
    
    return post


def demo_social_sharing_service(post):
    """Demonstrate the SocialShareService functionality."""
    print("\n" + "="*50)
    print("SOCIAL SHARING SERVICE DEMO")
    print("="*50)
    
    # 1. Generate share URLs
    print("\n1. Generating share URLs:")
    share_urls = SocialShareService.generate_share_urls(post)
    for platform, config in share_urls.items():
        print(f"   {config['name']}: {config['url'][:80]}...")
    
    # 2. Track some shares
    print("\n2. Tracking social shares:")
    platforms_to_test = ['facebook', 'twitter', 'linkedin', 'reddit']
    
    for platform in platforms_to_test:
        # Simulate multiple shares
        shares_to_add = {'facebook': 15, 'twitter': 8, 'linkedin': 5, 'reddit': 3}
        
        for _ in range(shares_to_add.get(platform, 1)):
            SocialShareService.track_share(post, platform)
        
        print(f"   ✓ Added {shares_to_add.get(platform, 1)} shares for {platform}")
    
    # 3. Get share counts
    print("\n3. Current share counts:")
    share_counts = SocialShareService.get_share_counts(post)
    for platform, count in share_counts.items():
        if count > 0:
            print(f"   {platform.capitalize()}: {count} shares")
    
    # 4. Get total shares
    total_shares = SocialShareService.get_total_shares(post)
    print(f"\n4. Total shares across all platforms: {total_shares}")
    
    # 5. Get platform configurations
    print("\n5. Platform configurations:")
    for platform in ['facebook', 'twitter', 'linkedin']:
        config = SocialShareService.get_platform_config(platform)
        print(f"   {config['name']}: {config['icon']} ({config['color']})")


def demo_social_share_model(post):
    """Demonstrate the SocialShare model functionality."""
    print("\n" + "="*50)
    print("SOCIAL SHARE MODEL DEMO")
    print("="*50)
    
    # Get all social shares for the post
    social_shares = SocialShare.objects.filter(post=post)
    
    print(f"\nSocial shares for '{post.title}':")
    for share in social_shares:
        print(f"   {share}")
    
    # Demonstrate increment functionality
    if social_shares.exists():
        first_share = social_shares.first()
        old_count = first_share.share_count
        first_share.increment_share_count()
        print(f"\n✓ Incremented {first_share.platform} shares from {old_count} to {first_share.share_count}")


def demo_admin_features():
    """Show information about admin features."""
    print("\n" + "="*50)
    print("ADMIN INTERFACE FEATURES")
    print("="*50)
    
    print("\nThe following admin features are available:")
    print("   ✓ SocialShare model registered in Django admin")
    print("   ✓ List view shows post, platform, share count, and last shared date")
    print("   ✓ Filtering by platform and date")
    print("   ✓ Search by post title")
    print("   ✓ Read-only timestamps for data integrity")
    
    print("\nTo access the admin interface:")
    print("   1. Create a superuser: python manage.py createsuperuser")
    print("   2. Run the server: python manage.py runserver")
    print("   3. Visit: http://localhost:8000/admin/")
    print("   4. Navigate to Blog > Social shares")


def demo_template_integration():
    """Show information about template integration."""
    print("\n" + "="*50)
    print("TEMPLATE INTEGRATION")
    print("="*50)
    
    print("\nSocial sharing widget features:")
    print("   ✓ Platform-specific share buttons (Facebook, Twitter, LinkedIn, etc.)")
    print("   ✓ Share count display for each platform")
    print("   ✓ Total share count display")
    print("   ✓ Copy link functionality")
    print("   ✓ Mobile Web Share API support")
    print("   ✓ AJAX share tracking")
    print("   ✓ Responsive design")
    print("   ✓ Platform-specific colors and icons")
    
    print("\nEnhanced meta tags:")
    print("   ✓ Open Graph meta tags for rich social previews")
    print("   ✓ Twitter Card meta tags")
    print("   ✓ Dynamic image selection (social_image or featured_image)")
    print("   ✓ Article metadata (author, publish date, categories, tags)")


def main():
    """Run the complete social sharing demo."""
    print("🚀 SOCIAL SHARING FUNCTIONALITY DEMO")
    print("="*60)
    
    try:
        # Create demo data
        post = create_demo_data()
        
        # Run demos
        demo_social_sharing_service(post)
        demo_social_share_model(post)
        demo_admin_features()
        demo_template_integration()
        
        print("\n" + "="*60)
        print("✅ DEMO COMPLETED SUCCESSFULLY!")
        print("="*60)
        
        print(f"\nDemo post URL: /blog/{post.slug}/")
        print("You can now test the social sharing functionality in your browser.")
        
    except Exception as e:
        print(f"\n❌ Error during demo: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()