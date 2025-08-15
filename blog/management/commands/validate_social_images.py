from django.core.management.base import BaseCommand
from django.conf import settings
from blog.models import Post, MediaItem
from blog.templatetags.media_tags import get_social_image_url, get_image_dimensions
from django.test import RequestFactory
import requests
from PIL import Image
import os


class Command(BaseCommand):
    help = 'Validate social sharing images for blog posts'

    def add_arguments(self, parser):
        parser.add_argument(
            '--post-slug',
            type=str,
            help='Validate specific post by slug',
        )
        parser.add_argument(
            '--check-dimensions',
            action='store_true',
            help='Check image dimensions for LinkedIn compatibility',
        )
        parser.add_argument(
            '--fix-missing',
            action='store_true',
            help='Attempt to fix posts with missing social images',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting social image validation...'))
        
        # Create a mock request for URL building
        factory = RequestFactory()
        request = factory.get('/')
        request.META['HTTP_HOST'] = getattr(settings, 'ALLOWED_HOSTS', ['localhost'])[0]
        request.META['SERVER_PORT'] = '80'
        request.is_secure = lambda: True
        
        posts = Post.objects.filter(status='published')
        if options['post_slug']:
            posts = posts.filter(slug=options['post_slug'])
        
        total_posts = posts.count()
        posts_with_images = 0
        posts_without_images = 0
        dimension_issues = 0
        
        for post in posts:
            self.stdout.write(f"\nValidating: {post.title}")
            
            # Get social image URL
            image_url = get_social_image_url(post, request)
            has_custom_image = bool(post.social_image or post.featured_image or 
                                  post.media_items.filter(media_type='image').exists())
            
            if has_custom_image:
                posts_with_images += 1
                self.stdout.write(f"  ✓ Has image: {image_url}")
                
                if options['check_dimensions']:
                    # Check dimensions
                    dimensions = self._get_actual_dimensions(post)
                    if dimensions:
                        width, height = dimensions['width'], dimensions['height']
                        self.stdout.write(f"  Dimensions: {width}x{height}")
                        
                        # LinkedIn recommendations: 1200x627 optimal, min 200x200
                        if width < 200 or height < 200:
                            dimension_issues += 1
                            self.stdout.write(
                                self.style.WARNING(f"  ⚠ Too small for LinkedIn (min 200x200)")
                            )
                        elif width > 7680 or height > 4320:
                            dimension_issues += 1
                            self.stdout.write(
                                self.style.WARNING(f"  ⚠ Too large for LinkedIn (max 7680x4320)")
                            )
                        else:
                            aspect_ratio = width / height
                            if aspect_ratio < 0.52 or aspect_ratio > 1.91:  # 1:1.91 to 1.91:1
                                self.stdout.write(
                                    self.style.WARNING(f"  ⚠ Aspect ratio {aspect_ratio:.2f} not optimal for LinkedIn")
                                )
            else:
                posts_without_images += 1
                self.stdout.write(f"  ⚠ Using fallback: {image_url}")
                
                if options['fix_missing']:
                    self._attempt_fix(post)
        
        # Summary
        self.stdout.write(f"\n{self.style.SUCCESS('=== SUMMARY ===')}")
        self.stdout.write(f"Total posts: {total_posts}")
        self.stdout.write(f"Posts with custom images: {posts_with_images}")
        self.stdout.write(f"Posts using fallback: {posts_without_images}")
        
        if options['check_dimensions']:
            self.stdout.write(f"Posts with dimension issues: {dimension_issues}")
        
        # Recommendations
        if posts_without_images > 0:
            self.stdout.write(f"\n{self.style.WARNING('RECOMMENDATIONS:')}")
            self.stdout.write("- Add featured_image or social_image to posts without custom images")
            self.stdout.write("- Consider creating MediaItem entries for posts with content images")
        
        if dimension_issues > 0:
            self.stdout.write("- Resize images to LinkedIn-friendly dimensions (1200x627 recommended)")
            self.stdout.write("- Ensure images are between 200x200 and 7680x4320 pixels")

    def _get_actual_dimensions(self, post):
        """Get actual image dimensions from the post's primary image"""
        if post.social_image:
            return get_image_dimensions(post.social_image)
        elif post.featured_image:
            return get_image_dimensions(post.featured_image)
        else:
            featured_media = post.media_items.filter(is_featured=True, media_type='image').first()
            if featured_media:
                if featured_media.large_image:
                    return get_image_dimensions(featured_media.large_image)
                elif featured_media.medium_image:
                    return get_image_dimensions(featured_media.medium_image)
                elif featured_media.original_image:
                    return get_image_dimensions(featured_media.original_image)
        return None

    def _attempt_fix(self, post):
        """Attempt to fix posts with missing social images"""
        self.stdout.write(f"  Attempting to fix {post.title}...")
        
        # Look for images in content or create a MediaItem from first available image
        # This is a placeholder for more sophisticated image detection
        # In a real implementation, you might parse the content for img tags
        # or use AI to generate appropriate social images
        
        self.stdout.write("  Fix functionality would be implemented here")