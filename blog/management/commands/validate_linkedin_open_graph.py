"""
LinkedIn Open Graph Tags Validation Command

This management command validates Open Graph meta tags for LinkedIn compatibility
and tests link preview functionality.

Usage:
    python manage.py validate_linkedin_open_graph [options]

Requirements covered: 2.1, 2.4
"""

import os
import requests
import tempfile
import shutil
from urllib.parse import urljoin, urlparse
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.test.client import RequestFactory
from django.template import Context, Template
from django.urls import reverse
from django.conf import settings
from PIL import Image
import json

try:
    from blog.models import Post, Category, Tag
    from blog.views import blog_detail
except ImportError as e:
    print(f"Import error: {e}")


class Command(BaseCommand):
    help = 'Validate Open Graph tags for LinkedIn compatibility'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--post-id',
            type=int,
            help='Validate specific post by ID'
        )
        parser.add_argument(
            '--create-test-posts',
            action='store_true',
            help='Create test posts for validation'
        )
        parser.add_argument(
            '--validate-images',
            action='store_true',
            help='Validate image URLs and accessibility'
        )
        parser.add_argument(
            '--linkedin-preview',
            action='store_true',
            help='Test LinkedIn preview compatibility'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Run all validation tests'
        )
        parser.add_argument(
            '--output-json',
            type=str,
            help='Output results to JSON file'
        )
    
    def handle(self, *args, **options):
        """Main command handler."""
        self.stdout.write(
            self.style.SUCCESS('LinkedIn Open Graph Tags Validation')
        )
        self.stdout.write('=' * 60)
        
        self.factory = RequestFactory()
        self.validation_results = {
            'posts_validated': 0,
            'posts_passed': 0,
            'posts_failed': 0,
            'issues_found': [],
            'recommendations': []
        }
        
        try:
            # Create test posts if requested
            if options['create_test_posts'] or options['all']:
                self._create_test_posts()
            
            # Validate specific post or all posts
            if options['post_id']:
                self._validate_post(options['post_id'], options)
            else:
                self._validate_all_posts(options)
            
            # Generate summary report
            self._generate_summary_report()
            
            # Output to JSON if requested
            if options['output_json']:
                self._output_json_report(options['output_json'])
        
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Validation failed: {e}')
            )
            raise CommandError(f'Validation error: {e}')
        
        self.stdout.write(
            self.style.SUCCESS('\nValidation complete!')
        )
    
    def _create_test_posts(self):
        """Create test posts for Open Graph validation."""
        self.stdout.write('Creating test posts for validation...')
        
        # Create test user if doesn't exist
        user, created = User.objects.get_or_create(
            username='og_test_user',
            defaults={
                'email': 'ogtest@example.com',
                'first_name': 'OG',
                'last_name': 'Tester'
            }
        )
        
        # Create test category
        category, created = Category.objects.get_or_create(
            name='Open Graph Test',
            defaults={'slug': 'open-graph-test'}
        )
        
        # Create temporary directory for test images
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Test post scenarios
            test_scenarios = [
                {
                    'title': 'OG Test - Perfect Social Image',
                    'slug': 'og-test-perfect-social-image',
                    'has_social_image': True,
                    'image_dimensions': (1200, 627),
                    'description': 'Test post with perfect LinkedIn social image dimensions'
                },
                {
                    'title': 'OG Test - Featured Image Fallback',
                    'slug': 'og-test-featured-image-fallback',
                    'has_featured_image': True,
                    'image_dimensions': (1920, 1080),
                    'description': 'Test post using featured image as Open Graph fallback'
                },
                {
                    'title': 'OG Test - No Images',
                    'slug': 'og-test-no-images',
                    'has_social_image': False,
                    'has_featured_image': False,
                    'description': 'Test post with no images for fallback testing'
                },
                {
                    'title': 'OG Test - Long Title for Truncation Testing',
                    'slug': 'og-test-long-title-truncation',
                    'has_social_image': True,
                    'image_dimensions': (800, 600),
                    'description': 'Test post with very long title to test Open Graph title truncation and handling'
                }
            ]
            
            for scenario in test_scenarios:
                # Check if post already exists
                if Post.objects.filter(slug=scenario['slug']).exists():
                    self.stdout.write(f'  Post already exists: {scenario["title"]}')
                    continue
                
                # Create post
                post = Post.objects.create(
                    title=scenario['title'],
                    slug=scenario['slug'],
                    author=user,
                    content=f'''
                    This is a test post for Open Graph validation.
                    
                    Scenario: {scenario['description']}
                    
                    This post is used to validate:
                    - Open Graph meta tag generation
                    - LinkedIn preview compatibility
                    - Image URL accessibility
                    - Fallback behavior
                    
                    The content includes multiple paragraphs to test excerpt generation
                    and meta description handling for social media sharing.
                    ''',
                    excerpt=scenario['description'],
                    status='published',
                    meta_description=f'Open Graph test: {scenario["description"]}'
                )
                post.categories.add(category)
                
                # Add images based on scenario
                if scenario.get('has_social_image'):
                    social_img = self._create_test_image(
                        temp_dir, 
                        f'social_{scenario["slug"]}.jpg',
                        scenario['image_dimensions']
                    )
                    post.social_image = social_img
                
                if scenario.get('has_featured_image'):
                    featured_img = self._create_test_image(
                        temp_dir,
                        f'featured_{scenario["slug"]}.jpg',
                        scenario['image_dimensions']
                    )
                    post.featured_image = featured_img
                
                post.save()
                self.stdout.write(f'  Created: {scenario["title"]}')
        
        finally:
            shutil.rmtree(temp_dir)
        
        self.stdout.write(f'Test posts creation complete')
    
    def _create_test_image(self, temp_dir, filename, dimensions):
        """Create a test image file."""
        from django.core.files.uploadedfile import SimpleUploadedFile
        
        width, height = dimensions
        img = Image.new('RGB', (width, height), color=(70, 130, 180))
        
        # Add some text to make it more realistic
        try:
            from PIL import ImageDraw, ImageFont
            draw = ImageDraw.Draw(img)
            # Use default font
            draw.text((50, 50), f'Test Image\n{width}x{height}', fill=(255, 255, 255))
        except:
            # If PIL text rendering fails, just use solid color
            pass
        
        temp_path = os.path.join(temp_dir, filename)
        img.save(temp_path, 'JPEG', quality=85)
        
        with open(temp_path, 'rb') as f:
            return SimpleUploadedFile(
                filename,
                f.read(),
                content_type='image/jpeg'
            )
    
    def _validate_all_posts(self, options):
        """Validate Open Graph tags for all published posts."""
        posts = Post.objects.filter(status='published').order_by('-created_at')[:20]  # Limit to recent posts
        
        self.stdout.write(f'Validating {posts.count()} published posts...')
        
        for post in posts:
            self._validate_post(post.id, options)
    
    def _validate_post(self, post_id, options):
        """Validate Open Graph tags for a specific post."""
        try:
            post = Post.objects.get(id=post_id)
        except Post.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Post with ID {post_id} not found')
            )
            return
        
        self.stdout.write(f'\nValidating post: {post.title}')
        self.stdout.write('-' * 50)
        
        self.validation_results['posts_validated'] += 1
        post_issues = []
        
        # Create request context
        request = self.factory.get(f'/blog/{post.slug}/')
        request.META['HTTP_HOST'] = 'testserver.com'
        request.META['wsgi.url_scheme'] = 'https'
        
        # Generate Open Graph tags
        og_tags = self._generate_og_tags(post, request)
        
        # Validate required tags
        required_tags = ['og:title', 'og:description', 'og:url', 'og:type', 'og:image']
        for tag in required_tags:
            if tag not in og_tags:
                issue = f'Missing required Open Graph tag: {tag}'
                post_issues.append(issue)
                self.stdout.write(self.style.ERROR(f'  ✗ {issue}'))
            else:
                self.stdout.write(self.style.SUCCESS(f'  ✓ {tag}: {og_tags[tag][:60]}...'))
        
        # Validate tag content
        self._validate_og_content(post, og_tags, post_issues)
        
        # Validate images if requested
        if options.get('validate_images') or options.get('all'):
            self._validate_og_images(og_tags, post_issues)
        
        # Test LinkedIn preview compatibility if requested
        if options.get('linkedin_preview') or options.get('all'):
            self._test_linkedin_preview_compatibility(og_tags, post_issues)
        
        # Record results
        if post_issues:
            self.validation_results['posts_failed'] += 1
            self.validation_results['issues_found'].extend([
                {'post_id': post.id, 'post_title': post.title, 'issue': issue}
                for issue in post_issues
            ])
            self.stdout.write(
                self.style.ERROR(f'  FAILED: {len(post_issues)} issues found')
            )
        else:
            self.validation_results['posts_passed'] += 1
            self.stdout.write(
                self.style.SUCCESS('  PASSED: All validations successful')
            )
    
    def _generate_og_tags(self, post, request):
        """Generate Open Graph tags for a post."""
        og_tags = {}
        
        # Basic tags
        og_tags['og:title'] = post.title
        og_tags['og:description'] = post.excerpt or post.meta_description or 'Blog post'
        og_tags['og:url'] = request.build_absolute_uri(f'/blog/{post.slug}/')
        og_tags['og:type'] = 'article'
        
        # Image tags
        if post.social_image:
            image_url = f"{request.scheme}://{request.get_host()}{post.social_image.url}"
            og_tags['og:image'] = image_url
            og_tags['og:image:type'] = 'image/jpeg'
            og_tags['og:image:alt'] = post.title
            
            # Try to get image dimensions
            try:
                with Image.open(post.social_image.path) as img:
                    og_tags['og:image:width'] = str(img.width)
                    og_tags['og:image:height'] = str(img.height)
            except:
                pass
        
        elif post.featured_image:
            image_url = f"{request.scheme}://{request.get_host()}{post.featured_image.url}"
            og_tags['og:image'] = image_url
            og_tags['og:image:type'] = 'image/jpeg'
            og_tags['og:image:alt'] = post.title
        
        else:
            # Fallback image
            og_tags['og:image'] = f"{request.scheme}://{request.get_host()}/static/default-og-image.jpg"
        
        # Article-specific tags
        og_tags['article:author'] = post.author.get_full_name() or post.author.username
        og_tags['article:published_time'] = post.created_at.isoformat()
        if post.updated_at != post.created_at:
            og_tags['article:modified_time'] = post.updated_at.isoformat()
        
        # Categories and tags
        if post.categories.exists():
            og_tags['article:section'] = post.categories.first().name
        
        return og_tags
    
    def _validate_og_content(self, post, og_tags, issues):
        """Validate Open Graph tag content."""
        # Title validation
        title = og_tags.get('og:title', '')
        if len(title) > 95:
            issues.append(f'Title too long ({len(title)} chars, recommended: <95)')
        elif len(title) < 10:
            issues.append(f'Title too short ({len(title)} chars, recommended: >10)')
        
        # Description validation
        description = og_tags.get('og:description', '')
        if len(description) > 300:
            issues.append(f'Description too long ({len(description)} chars, recommended: <300)')
        elif len(description) < 50:
            issues.append(f'Description too short ({len(description)} chars, recommended: >50)')
        
        # URL validation
        url = og_tags.get('og:url', '')
        if not url.startswith(('http://', 'https://')):
            issues.append('URL should be absolute (include protocol)')
        
        # Image validation
        image_url = og_tags.get('og:image', '')
        if image_url and not image_url.startswith(('http://', 'https://')):
            issues.append('Image URL should be absolute')
    
    def _validate_og_images(self, og_tags, issues):
        """Validate Open Graph image accessibility and properties."""
        image_url = og_tags.get('og:image')
        if not image_url:
            issues.append('No Open Graph image specified')
            return
        
        self.stdout.write(f'  Validating image: {image_url}')
        
        # Check if image URL is accessible
        try:
            response = requests.head(image_url, timeout=10)
            if response.status_code != 200:
                issues.append(f'Image URL not accessible (HTTP {response.status_code})')
            else:
                # Check content type
                content_type = response.headers.get('content-type', '')
                if not content_type.startswith('image/'):
                    issues.append(f'Invalid image content type: {content_type}')
                
                # Check file size
                content_length = response.headers.get('content-length')
                if content_length:
                    size_mb = int(content_length) / (1024 * 1024)
                    if size_mb > 8:  # LinkedIn recommends <8MB
                        issues.append(f'Image too large ({size_mb:.1f}MB, recommended: <8MB)')
        
        except requests.exceptions.RequestException as e:
            issues.append(f'Image URL validation failed: {e}')
        
        # Validate image dimensions if available
        width = og_tags.get('og:image:width')
        height = og_tags.get('og:image:height')
        
        if width and height:
            width, height = int(width), int(height)
            
            # LinkedIn recommendations
            if width < 200 or height < 200:
                issues.append(f'Image too small ({width}x{height}, minimum: 200x200)')
            
            if width > 8192 or height > 8192:
                issues.append(f'Image too large ({width}x{height}, maximum: 8192x8192)')
            
            # Aspect ratio check
            aspect_ratio = width / height
            if aspect_ratio < 0.5 or aspect_ratio > 2.0:
                issues.append(f'Unusual aspect ratio ({aspect_ratio:.2f}, recommended: 0.5-2.0)')
            
            # Optimal dimensions check
            if width == 1200 and height == 627:
                self.stdout.write(self.style.SUCCESS('  ✓ Perfect LinkedIn dimensions (1200x627)'))
            elif width == 1200 and height == 630:
                self.stdout.write(self.style.SUCCESS('  ✓ Good LinkedIn dimensions (1200x630)'))
    
    def _test_linkedin_preview_compatibility(self, og_tags, issues):
        """Test LinkedIn preview compatibility."""
        self.stdout.write('  Testing LinkedIn preview compatibility...')
        
        # LinkedIn-specific validations
        linkedin_requirements = {
            'title_length': (10, 95),
            'description_length': (50, 300),
            'image_min_dimensions': (200, 200),
            'image_max_dimensions': (8192, 8192),
            'image_recommended_dimensions': [(1200, 627), (1200, 630), (1080, 1080)]
        }
        
        # Check title length
        title = og_tags.get('og:title', '')
        min_title, max_title = linkedin_requirements['title_length']
        if not (min_title <= len(title) <= max_title):
            issues.append(f'Title length not optimal for LinkedIn ({len(title)} chars)')
        
        # Check description length
        description = og_tags.get('og:description', '')
        min_desc, max_desc = linkedin_requirements['description_length']
        if not (min_desc <= len(description) <= max_desc):
            issues.append(f'Description length not optimal for LinkedIn ({len(description)} chars)')
        
        # Check for LinkedIn-specific meta tags
        linkedin_specific_tags = ['og:image:width', 'og:image:height', 'og:image:alt']
        missing_linkedin_tags = [tag for tag in linkedin_specific_tags if tag not in og_tags]
        if missing_linkedin_tags:
            issues.append(f'Missing LinkedIn-recommended tags: {", ".join(missing_linkedin_tags)}')
        
        # Simulate LinkedIn crawler behavior
        self._simulate_linkedin_crawler(og_tags, issues)
    
    def _simulate_linkedin_crawler(self, og_tags, issues):
        """Simulate LinkedIn crawler validation."""
        # LinkedIn crawler checks
        crawler_issues = []
        
        # Check for duplicate content
        title = og_tags.get('og:title', '')
        description = og_tags.get('og:description', '')
        
        if title.lower() in description.lower():
            crawler_issues.append('Title appears in description (may cause redundancy)')
        
        # Check for special characters that might cause issues
        problematic_chars = ['<', '>', '"', "'", '&']
        for char in problematic_chars:
            if char in title:
                crawler_issues.append(f'Title contains potentially problematic character: {char}')
            if char in description:
                crawler_issues.append(f'Description contains potentially problematic character: {char}')
        
        # Check URL structure
        url = og_tags.get('og:url', '')
        if '?' in url:
            crawler_issues.append('URL contains query parameters (may affect caching)')
        
        if crawler_issues:
            issues.extend(crawler_issues)
            self.stdout.write(
                self.style.WARNING(f'  LinkedIn crawler simulation found {len(crawler_issues)} potential issues')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('  ✓ LinkedIn crawler simulation passed')
            )
    
    def _generate_summary_report(self):
        """Generate validation summary report."""
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('VALIDATION SUMMARY'))
        self.stdout.write('=' * 60)
        
        results = self.validation_results
        
        self.stdout.write(f'Posts Validated: {results["posts_validated"]}')
        self.stdout.write(f'Posts Passed: {results["posts_passed"]}')
        self.stdout.write(f'Posts Failed: {results["posts_failed"]}')
        
        if results['posts_validated'] > 0:
            success_rate = (results['posts_passed'] / results['posts_validated']) * 100
            self.stdout.write(f'Success Rate: {success_rate:.1f}%')
            
            if success_rate >= 90:
                self.stdout.write(self.style.SUCCESS('✓ EXCELLENT Open Graph validation'))
            elif success_rate >= 75:
                self.stdout.write(self.style.SUCCESS('✓ GOOD Open Graph validation'))
            elif success_rate >= 50:
                self.stdout.write(self.style.WARNING('⚠ NEEDS IMPROVEMENT'))
            else:
                self.stdout.write(self.style.ERROR('✗ POOR Open Graph validation'))
        
        # Issues summary
        if results['issues_found']:
            self.stdout.write(f'\nIssues Found: {len(results["issues_found"])}')
            
            # Group issues by type
            issue_types = {}
            for issue_record in results['issues_found']:
                issue = issue_record['issue']
                issue_type = issue.split(':')[0] if ':' in issue else 'General'
                if issue_type not in issue_types:
                    issue_types[issue_type] = 0
                issue_types[issue_type] += 1
            
            self.stdout.write('\nIssue Types:')
            for issue_type, count in sorted(issue_types.items()):
                self.stdout.write(f'  {issue_type}: {count}')
        
        # Generate recommendations
        self._generate_recommendations()
    
    def _generate_recommendations(self):
        """Generate optimization recommendations."""
        recommendations = []
        
        results = self.validation_results
        
        if results['posts_failed'] > 0:
            recommendations.append('Review and fix failed post validations')
        
        # Common issue-based recommendations
        common_issues = {}
        for issue_record in results['issues_found']:
            issue = issue_record['issue']
            if 'too long' in issue.lower():
                common_issues['length'] = common_issues.get('length', 0) + 1
            elif 'missing' in issue.lower():
                common_issues['missing'] = common_issues.get('missing', 0) + 1
            elif 'image' in issue.lower():
                common_issues['image'] = common_issues.get('image', 0) + 1
        
        if common_issues.get('length', 0) > 2:
            recommendations.append('Review content length guidelines for titles and descriptions')
        
        if common_issues.get('missing', 0) > 2:
            recommendations.append('Ensure all required Open Graph tags are implemented')
        
        if common_issues.get('image', 0) > 2:
            recommendations.append('Review image optimization and accessibility')
        
        # General recommendations
        recommendations.extend([
            'Use LinkedIn Post Inspector to test URLs: https://www.linkedin.com/post-inspector/',
            'Implement automated Open Graph tag testing in CI/CD pipeline',
            'Consider using structured data for enhanced rich snippets',
            'Monitor social media engagement metrics to validate improvements'
        ])
        
        if recommendations:
            self.stdout.write('\nRECOMMENDATIONS:')
            for i, rec in enumerate(recommendations, 1):
                self.stdout.write(f'  {i}. {rec}')
        
        self.validation_results['recommendations'] = recommendations
    
    def _output_json_report(self, output_file):
        """Output validation results to JSON file."""
        try:
            with open(output_file, 'w') as f:
                json.dump(self.validation_results, f, indent=2, default=str)
            
            self.stdout.write(f'\nValidation results saved to: {output_file}')
        
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Failed to save JSON report: {e}')
            )