"""
End-to-end integration tests for LinkedIn image posting workflow.

This test suite covers Task 9 requirements:
- Test complete workflow from blog post to LinkedIn with images
- Test image processing pipeline with real image files
- Test Open Graph tag generation and validation
- Test fallback scenarios when images are unavailable
- Test performance with various image sizes and formats

Requirements covered: 1.1, 1.5, 2.4, 3.2, 3.5
"""

import os
import tempfile
import shutil
import time
import json
from unittest.mock import Mock, patch, MagicMock, call
from django.test import TestCase, TransactionTestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.models import User
from django.utils import timezone
from django.test.client import RequestFactory
from django.template.loader import render_to_string
from django.template import Context, Template
from PIL import Image
from io import BytesIO
import requests

try:
    from blog.models import Post, MediaItem, Category, Tag
    from blog.services.linkedin_image_service import LinkedInImageService
    from blog.services.linkedin_service import LinkedInAPIService, LinkedInAPIError
    from blog.services.linkedin_content_formatter import LinkedInContentFormatter
    from blog.utils.image_processor import ImageProcessor, ImageProcessingError
    from blog.linkedin_models import LinkedInConfig, LinkedInPost
    from blog.tasks import post_to_linkedin
except ImportError as e:
    # Handle import errors gracefully for validation
    print(f"Import warning: {e}")
    pass


class LinkedInImageE2EWorkflowTest(TransactionTestCase):
    """
    Test complete workflow from blog post to LinkedIn with images.
    
    This test class verifies the complete end-to-end workflow:
    1. Blog post is created with images
    2. Image processing pipeline processes images
    3. LinkedIn API service uploads images
    4. LinkedIn post is created with images
    5. Results are tracked and logged
    
    Requirements: 1.1, 1.5, 3.2
    """
    
    def setUp(self):
        """Set up test data for end-to-end workflow testing."""
        # Create test user
        self.user = User.objects.create_user(
            username='testauthor',
            email='author@example.com',
            password='testpass123'
        )
        
        # Create test category and tag
        self.category = Category.objects.create(name='Technology', slug='technology')
        self.tag = Tag.objects.create(name='Django', slug='django')
        
        # Create LinkedIn configuration
        self.linkedin_config = LinkedInConfig.objects.create(
            client_id='test_client_id',
            is_active=True
        )
        self.linkedin_config.set_client_secret('test_client_secret')
        self.linkedin_config.set_access_token('test_access_token')
        self.linkedin_config.token_expires_at = timezone.now() + timezone.timedelta(hours=1)
        self.linkedin_config.save()
        
        # Create temporary directory for test images
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.temp_dir)
        
        # Create test images with different characteristics
        self.test_images = self._create_test_images()
    
    def _create_test_images(self):
        """Create test image files with different characteristics for E2E testing."""
        images = {}
        
        # LinkedIn-compatible image (perfect for posting)
        compatible_img = Image.new('RGB', (1200, 627), color='red')
        compatible_path = os.path.join(self.temp_dir, 'compatible.jpg')
        compatible_img.save(compatible_path, 'JPEG', quality=85)
        images['compatible'] = compatible_path
        
        # Large image that needs processing
        large_img = Image.new('RGB', (3000, 2000), color='blue')
        large_path = os.path.join(self.temp_dir, 'large.jpg')
        large_img.save(large_path, 'JPEG', quality=90)
        images['large'] = large_path
        
        # PNG with transparency (needs conversion)
        png_img = Image.new('RGBA', (800, 600), color=(255, 0, 0, 128))
        png_path = os.path.join(self.temp_dir, 'transparent.png')
        png_img.save(png_path, 'PNG')
        images['png'] = png_path
        
        # Small image (below LinkedIn minimum)
        small_img = Image.new('RGB', (150, 150), color='green')
        small_path = os.path.join(self.temp_dir, 'small.jpg')
        small_img.save(small_path, 'JPEG', quality=85)
        images['small'] = small_path
        
        return images
    
    def _create_uploaded_file(self, image_path, field_name='image.jpg'):
        """Create a Django UploadedFile from an image path."""
        with open(image_path, 'rb') as f:
            return SimpleUploadedFile(
                field_name,
                f.read(),
                content_type='image/jpeg'
            )
    
    def _create_post_with_image(self, image_type='compatible', title='E2E Test Post'):
        """Create a blog post with specified image type."""
        post = Post.objects.create(
            title=title,
            slug=title.lower().replace(' ', '-'),
            author=self.user,
            content='This is an end-to-end test blog post with image integration.',
            excerpt='E2E test excerpt for LinkedIn posting with images.',
            status='published'
        )
        post.categories.add(self.category)
        post.tags.add(self.tag)
        
        # Add image based on type
        if image_type in self.test_images:
            image_file = self._create_uploaded_file(
                self.test_images[image_type], 
                f'{image_type}.jpg'
            )
            post.social_image = image_file
            post.save()
        
        return post
    
    @patch('blog.services.linkedin_service.LinkedInAPIService.upload_media')
    @patch('blog.services.linkedin_service.LinkedInAPIService.create_post_with_media')
    @patch('blog.services.linkedin_service.LinkedInAPIService.get_user_profile')
    def test_complete_e2e_workflow_with_compatible_image(self, mock_profile, mock_create_post, mock_upload):
        """
        Test complete E2E workflow with LinkedIn-compatible image.
        
        Verifies:
        - Image selection and validation
        - Image processing (minimal for compatible image)
        - LinkedIn media upload
        - LinkedIn post creation with media
        - Success tracking
        
        Requirements: 1.1, 1.5, 3.2
        """
        # Mock LinkedIn API responses
        mock_profile.return_value = {'id': 'test_user_id'}
        mock_upload.return_value = 'urn:li:digitalmediaAsset:test_media_id'
        mock_create_post.return_value = {
            'id': 'urn:li:ugcPost:test_post_id',
            'permalink': 'https://linkedin.com/posts/test_post'
        }
        
        # Create post with compatible image
        post = self._create_post_with_image('compatible')
        
        # Execute the complete workflow
        start_time = time.time()
        
        with patch('blog.services.linkedin_image_service.LinkedInImageService.process_image_for_linkedin') as mock_process:
            # Mock image processing to return processed path
            mock_process.return_value = self.test_images['compatible']
            
            # Execute LinkedIn posting task
            result = post_to_linkedin(post.id)
        
        end_time = time.time()
        workflow_duration = end_time - start_time
        
        # Verify workflow success
        self.assertTrue(result['success'])
        self.assertEqual(result['post_id'], post.id)
        self.assertEqual(result['linkedin_post_id'], 'urn:li:ugcPost:test_post_id')
        self.assertIn('task_duration', result)
        
        # Verify LinkedIn post record
        linkedin_post = LinkedInPost.objects.get(post=post)
        self.assertEqual(linkedin_post.status, 'success')
        self.assertEqual(linkedin_post.linkedin_post_id, 'urn:li:ugcPost:test_post_id')
        self.assertIsNotNone(linkedin_post.posted_at)
        
        # Verify image-specific fields
        self.assertIn('urn:li:digitalmediaAsset:test_media_id', linkedin_post.media_ids)
        self.assertEqual(linkedin_post.image_upload_status, 'success')
        self.assertEqual(len(linkedin_post.image_urls), 1)
        
        # Verify API calls were made in correct order
        mock_upload.assert_called_once()
        mock_create_post.assert_called_once()
        
        # Verify performance (should be fast for compatible image)
        self.assertLess(workflow_duration, 10.0)  # Should complete within 10 seconds
    
    @patch('blog.services.linkedin_service.LinkedInAPIService.upload_media')
    @patch('blog.services.linkedin_service.LinkedInAPIService.create_post_with_media')
    @patch('blog.services.linkedin_service.LinkedInAPIService.get_user_profile')
    @patch('blog.utils.image_processor.ImageProcessor.process_for_linkedin')
    def test_complete_e2e_workflow_with_large_image_processing(self, mock_process, mock_profile, mock_create_post, mock_upload):
        """
        Test complete E2E workflow with large image requiring processing.
        
        Verifies:
        - Large image detection and processing
        - Image resizing and optimization
        - LinkedIn media upload with processed image
        - Performance with image processing
        
        Requirements: 1.1, 1.5, 3.2
        """
        # Mock LinkedIn API responses
        mock_profile.return_value = {'id': 'test_user_id'}
        mock_upload.return_value = 'urn:li:digitalmediaAsset:processed_media_id'
        mock_create_post.return_value = {
            'id': 'urn:li:ugcPost:processed_post_id',
            'permalink': 'https://linkedin.com/posts/processed_post'
        }
        
        # Mock image processing to return processed image
        processed_path = os.path.join(self.temp_dir, 'processed_large.jpg')
        processed_img = Image.new('RGB', (1200, 800), color='blue')
        processed_img.save(processed_path, 'JPEG', quality=85)
        mock_process.return_value = processed_path
        
        # Create post with large image
        post = self._create_post_with_image('large', 'Large Image E2E Test')
        
        # Execute the workflow
        start_time = time.time()
        result = post_to_linkedin(post.id)
        end_time = time.time()
        
        processing_duration = end_time - start_time
        
        # Verify workflow success
        self.assertTrue(result['success'])
        self.assertEqual(result['linkedin_post_id'], 'urn:li:ugcPost:processed_post_id')
        
        # Verify image processing was called
        mock_process.assert_called_once()
        
        # Verify LinkedIn post record
        linkedin_post = LinkedInPost.objects.get(post=post)
        self.assertEqual(linkedin_post.status, 'success')
        self.assertEqual(linkedin_post.image_upload_status, 'success')
        self.assertIn('urn:li:digitalmediaAsset:processed_media_id', linkedin_post.media_ids)
        
        # Performance should still be reasonable even with processing
        self.assertLess(processing_duration, 30.0)  # Should complete within 30 seconds
    
    @patch('blog.services.linkedin_service.LinkedInAPIService.create_post')
    @patch('blog.services.linkedin_service.LinkedInAPIService.get_user_profile')
    def test_e2e_workflow_fallback_to_text_only(self, mock_profile, mock_create_post):
        """
        Test E2E workflow fallback to text-only when image processing fails.
        
        Verifies:
        - Image processing failure detection
        - Graceful fallback to text-only posting
        - Error logging and tracking
        - Workflow completion despite image failure
        
        Requirements: 1.5, 3.2
        """
        # Mock LinkedIn API responses
        mock_profile.return_value = {'id': 'test_user_id'}
        mock_create_post.return_value = {
            'id': 'urn:li:ugcPost:text_only_post_id',
            'permalink': 'https://linkedin.com/posts/text_only_post'
        }
        
        # Create post with small image (will fail validation)
        post = self._create_post_with_image('small', 'Fallback Test Post')
        
        # Mock image processing to fail
        with patch('blog.services.linkedin_image_service.LinkedInImageService.process_image_for_linkedin') as mock_process:
            mock_process.side_effect = ImageProcessingError("Image too small for LinkedIn")
            
            # Execute the workflow
            result = post_to_linkedin(post.id)
        
        # Verify workflow still succeeds (fallback to text-only)
        self.assertTrue(result['success'])
        self.assertEqual(result['linkedin_post_id'], 'urn:li:ugcPost:text_only_post_id')
        
        # Verify LinkedIn post record shows image failure but overall success
        linkedin_post = LinkedInPost.objects.get(post=post)
        self.assertEqual(linkedin_post.status, 'success')
        self.assertEqual(linkedin_post.image_upload_status, 'failed')
        self.assertIn('Image too small', linkedin_post.image_error_message)
        
        # Verify text-only post was created (not create_post_with_media)
        mock_create_post.assert_called_once()
        
        # Verify no media IDs were stored
        self.assertEqual(len(linkedin_post.media_ids), 0)


class LinkedInImageProcessingPipelineTest(TestCase):
    """
    Test image processing pipeline with real image files.
    
    This test class focuses on the image processing pipeline:
    - Real image file processing
    - Format conversion and optimization
    - Performance with different image types
    - Error handling in processing pipeline
    
    Requirements: 1.1, 3.2, 3.5
    """
    
    def setUp(self):
        """Set up test data for image processing pipeline testing."""
        # Create temporary directory for test images
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.temp_dir)
        
        # Create real test images with various characteristics
        self.test_images = self._create_real_test_images()
        
        # Initialize image processor
        self.processor = ImageProcessor()
    
    def _create_real_test_images(self):
        """Create real test image files with various characteristics."""
        images = {}
        
        # High-resolution JPEG
        hr_img = Image.new('RGB', (4000, 3000), color=(255, 100, 100))
        hr_path = os.path.join(self.temp_dir, 'high_res.jpg')
        hr_img.save(hr_path, 'JPEG', quality=95)
        images['high_res'] = hr_path
        
        # PNG with transparency and complex colors
        png_img = Image.new('RGBA', (1500, 1000), color=(0, 0, 0, 0))
        # Add some complex patterns
        for x in range(0, 1500, 50):
            for y in range(0, 1000, 50):
                color = (x % 255, y % 255, (x + y) % 255, 200)
                png_img.putpixel((x, y), color)
        png_path = os.path.join(self.temp_dir, 'complex.png')
        png_img.save(png_path, 'PNG')
        images['complex_png'] = png_path
        
        # Very small JPEG
        tiny_img = Image.new('RGB', (50, 50), color='yellow')
        tiny_path = os.path.join(self.temp_dir, 'tiny.jpg')
        tiny_img.save(tiny_path, 'JPEG', quality=85)
        images['tiny'] = tiny_path
        
        # Square image (different aspect ratio)
        square_img = Image.new('RGB', (1000, 1000), color='cyan')
        square_path = os.path.join(self.temp_dir, 'square.jpg')
        square_img.save(square_path, 'JPEG', quality=85)
        images['square'] = square_path
        
        return images
    
    def test_high_resolution_image_processing(self):
        """Test processing of high-resolution image."""
        start_time = time.time()
        
        # Process high-resolution image
        output_path = os.path.join(self.temp_dir, 'processed_hr.jpg')
        result_path = self.processor.process_for_linkedin(
            self.test_images['high_res'],
            output_path
        )
        
        processing_time = time.time() - start_time
        
        # Verify processing success
        self.assertEqual(result_path, output_path)
        self.assertTrue(os.path.exists(output_path))
        
        # Verify processed image is LinkedIn compatible
        is_compatible, issues = self.processor.is_linkedin_compatible(output_path)
        self.assertTrue(is_compatible)
        self.assertEqual(len(issues), 0)
        
        # Verify dimensions are within LinkedIn limits
        with Image.open(output_path) as img:
            self.assertLessEqual(img.width, self.processor.MAX_DIMENSIONS[0])
            self.assertLessEqual(img.height, self.processor.MAX_DIMENSIONS[1])
            self.assertGreaterEqual(img.width, self.processor.MIN_DIMENSIONS[0])
            self.assertGreaterEqual(img.height, self.processor.MIN_DIMENSIONS[1])
        
        # Verify file size is reasonable
        file_size = os.path.getsize(output_path)
        self.assertLessEqual(file_size, self.processor.MAX_FILE_SIZE)
        
        # Performance check - should process within reasonable time
        self.assertLess(processing_time, 15.0)  # Should complete within 15 seconds
    
    def test_png_transparency_conversion(self):
        """Test PNG with transparency conversion to JPEG."""
        start_time = time.time()
        
        # Process PNG with transparency
        output_path = os.path.join(self.temp_dir, 'converted_png.jpg')
        result_path = self.processor.process_for_linkedin(
            self.test_images['complex_png'],
            output_path
        )
        
        processing_time = time.time() - start_time
        
        # Verify conversion success
        self.assertEqual(result_path, output_path)
        self.assertTrue(os.path.exists(output_path))
        
        # Verify format conversion
        with Image.open(output_path) as img:
            self.assertEqual(img.format, 'JPEG')
            self.assertEqual(img.mode, 'RGB')  # Should convert from RGBA
        
        # Verify LinkedIn compatibility
        is_compatible, issues = self.processor.is_linkedin_compatible(output_path)
        self.assertTrue(is_compatible)
        
        # Performance check
        self.assertLess(processing_time, 10.0)
    
    def test_small_image_rejection(self):
        """Test that images below minimum size are properly rejected."""
        # Attempt to process tiny image
        output_path = os.path.join(self.temp_dir, 'processed_tiny.jpg')
        
        with self.assertRaises(ImageProcessingError) as context:
            self.processor.process_for_linkedin(
                self.test_images['tiny'],
                output_path
            )
        
        # Verify appropriate error message
        self.assertIn('below minimum', str(context.exception).lower())


class LinkedInOpenGraphTagsTest(TestCase):
    """
    Test Open Graph tag generation and validation.
    
    This test class focuses on:
    - Open Graph meta tag generation
    - Image URL generation for social sharing
    - Tag validation and completeness
    - Fallback behavior for missing images
    
    Requirements: 2.4, 3.5
    """
    
    def setUp(self):
        """Set up test data for Open Graph testing."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.category = Category.objects.create(name='Test Category')
        
        # Create temporary directory for test images
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.temp_dir)
        
        # Create test image
        test_img = Image.new('RGB', (1200, 627), color='red')
        self.test_image_path = os.path.join(self.temp_dir, 'og_test.jpg')
        test_img.save(self.test_image_path, 'JPEG', quality=85)
        
        # Create request factory for template rendering
        self.factory = RequestFactory()
    
    def _create_uploaded_file(self, image_path, field_name='image.jpg'):
        """Create a Django UploadedFile from an image path."""
        with open(image_path, 'rb') as f:
            return SimpleUploadedFile(
                field_name,
                f.read(),
                content_type='image/jpeg'
            )
    
    def test_open_graph_tags_with_social_image(self):
        """Test Open Graph tag generation with social_image."""
        # Create post with social image
        post = Post.objects.create(
            title='Open Graph Test Post',
            slug='open-graph-test-post',
            author=self.user,
            content='Test content for Open Graph tags.',
            excerpt='Test excerpt for social sharing.',
            status='published'
        )
        post.categories.add(self.category)
        
        # Add social image
        social_image_file = self._create_uploaded_file(self.test_image_path, 'social.jpg')
        post.social_image = social_image_file
        post.save()
        
        # Create request context
        request = self.factory.get(f'/blog/{post.slug}/')
        
        # Render Open Graph tags template
        template = Template("""
        {% load blog_extras %}
        <meta property="og:title" content="{{ post.title }}" />
        <meta property="og:description" content="{{ post.excerpt }}" />
        <meta property="og:url" content="{{ request.build_absolute_uri }}" />
        {% if post.social_image %}
        <meta property="og:image" content="{{ request.scheme }}://{{ request.get_host }}{{ post.social_image.url }}" />
        <meta property="og:image:width" content="1200" />
        <meta property="og:image:height" content="627" />
        <meta property="og:image:type" content="image/jpeg" />
        {% endif %}
        <meta property="og:type" content="article" />
        """)
        
        context = Context({'post': post, 'request': request})
        rendered = template.render(context)
        
        # Verify Open Graph tags
        self.assertIn('og:title', rendered)
        self.assertIn('Open Graph Test Post', rendered)
        self.assertIn('og:description', rendered)
        self.assertIn('Test excerpt for social sharing', rendered)
        self.assertIn('og:image', rendered)
        self.assertIn('social.jpg', rendered)
        self.assertIn('og:image:width', rendered)
        self.assertIn('og:image:height', rendered)
        self.assertIn('og:image:type', rendered)
        self.assertIn('og:type', rendered)
        self.assertIn('article', rendered)
    
    def test_open_graph_tags_with_featured_image_fallback(self):
        """Test Open Graph tag generation with featured_image fallback."""
        # Create post with featured image (no social image)
        post = Post.objects.create(
            title='Featured Image OG Test',
            slug='featured-image-og-test',
            author=self.user,
            content='Test content with featured image.',
            excerpt='Test excerpt with featured image.',
            status='published'
        )
        
        # Add featured image
        featured_image_file = self._create_uploaded_file(self.test_image_path, 'featured.jpg')
        post.featured_image = featured_image_file
        post.save()
        
        # Create request context
        request = self.factory.get(f'/blog/{post.slug}/')
        
        # Render template with fallback logic
        template = Template("""
        {% load blog_extras %}
        {% if post.social_image %}
        <meta property="og:image" content="{{ request.scheme }}://{{ request.get_host }}{{ post.social_image.url }}" />
        {% elif post.featured_image %}
        <meta property="og:image" content="{{ request.scheme }}://{{ request.get_host }}{{ post.featured_image.url }}" />
        {% endif %}
        """)
        
        context = Context({'post': post, 'request': request})
        rendered = template.render(context)
        
        # Verify fallback to featured image
        self.assertIn('og:image', rendered)
        self.assertIn('featured.jpg', rendered)
    
    def test_open_graph_image_url_validation(self):
        """Test that Open Graph image URLs are properly formatted."""
        # Create post with social image
        post = Post.objects.create(
            title='URL Validation Test',
            slug='url-validation-test',
            author=self.user,
            content='Test content for URL validation.',
            status='published'
        )
        
        social_image_file = self._create_uploaded_file(self.test_image_path, 'url_test.jpg')
        post.social_image = social_image_file
        post.save()
        
        # Create request context
        request = self.factory.get(f'/blog/{post.slug}/')
        request.META['HTTP_HOST'] = 'example.com'
        request.META['wsgi.url_scheme'] = 'https'
        
        # Get image URL
        image_url = f"{request.scheme}://{request.get_host()}{post.social_image.url}"
        
        # Validate URL format
        from urllib.parse import urlparse
        parsed_url = urlparse(image_url)
        
        self.assertEqual(parsed_url.scheme, 'https')
        self.assertEqual(parsed_url.netloc, 'example.com')
        self.assertTrue(parsed_url.path.endswith('url_test.jpg'))
        
        # Verify URL is absolute
        self.assertTrue(image_url.startswith('https://'))


class LinkedInImageFallbackScenariosTest(TestCase):
    """
    Test fallback scenarios when images are unavailable.
    
    This test class focuses on:
    - Image unavailability handling
    - Graceful degradation to text-only posts
    - Error logging and recovery
    - User experience during failures
    
    Requirements: 1.5, 3.2, 3.5
    """
    
    def setUp(self):
        """Set up test data for fallback scenario testing."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create LinkedIn configuration
        self.linkedin_config = LinkedInConfig.objects.create(
            client_id='test_client_id',
            is_active=True
        )
        self.linkedin_config.set_client_secret('test_secret')
        self.linkedin_config.set_access_token('test_token')
        self.linkedin_config.save()
    
    def test_fallback_broken_image_file(self):
        """Test fallback when image file is broken or missing."""
        # Create post with broken image reference
        post = Post.objects.create(
            title='Broken Image Test',
            slug='broken-image-test',
            author=self.user,
            content='Test content with broken image.',
            status='published'
        )
        
        # Set broken image path
        post.social_image.name = 'non_existent_image.jpg'
        post.save()
        
        # Test image service handles broken image gracefully
        image_service = LinkedInImageService()
        selected_image = image_service.get_post_image(post)
        
        # Should return None for broken image
        self.assertIsNone(selected_image)
        
        # Test fallback images also handles this gracefully
        fallback_images = image_service.get_fallback_images(post)
        self.assertEqual(len(fallback_images), 0)
    
    @patch('blog.services.linkedin_service.LinkedInAPIService.upload_media')
    @patch('blog.services.linkedin_service.LinkedInAPIService.create_post')
    @patch('blog.services.linkedin_service.LinkedInAPIService.get_user_profile')
    def test_fallback_network_error_during_upload(self, mock_profile, mock_create_post, mock_upload):
        """Test fallback when network error occurs during image upload."""
        # Mock LinkedIn API responses
        mock_profile.return_value = {'id': 'test_user_id'}
        mock_upload.side_effect = requests.exceptions.ConnectionError("Network error")
        mock_create_post.return_value = {
            'id': 'urn:li:ugcPost:network_fallback_id',
            'permalink': 'https://linkedin.com/posts/network_fallback'
        }
        
        # Create post (image doesn't matter since upload will fail)
        post = Post.objects.create(
            title='Network Error Test',
            slug='network-error-test',
            author=self.user,
            content='Test content for network error scenario.',
            status='published'
        )
        
        # Execute posting task
        result = post_to_linkedin(post.id)
        
        # Should succeed with fallback to text-only
        self.assertTrue(result['success'])
        self.assertEqual(result['linkedin_post_id'], 'urn:li:ugcPost:network_fallback_id')
        
        # Verify LinkedIn post record shows appropriate status
        linkedin_post = LinkedInPost.objects.get(post=post)
        self.assertEqual(linkedin_post.status, 'success')
        self.assertEqual(linkedin_post.image_upload_status, 'failed')
        self.assertIn('Network error', linkedin_post.image_error_message)
    
    def test_fallback_multiple_image_failures(self):
        """Test fallback when multiple images fail in sequence."""
        # Create post with multiple broken images
        post = Post.objects.create(
            title='Multiple Failures Test',
            slug='multiple-failures-test',
            author=self.user,
            content='Test content with multiple broken images.',
            status='published'
        )
        
        # Add broken social image
        post.social_image.name = 'broken_social.jpg'
        
        # Add broken featured image
        post.featured_image.name = 'broken_featured.jpg'
        post.save()
        
        # Add broken media items
        MediaItem.objects.create(
            post=post,
            media_type='image',
            title='Broken Media 1',
            original_image='broken_media_1.jpg'
        )
        
        # Test image service handles all failures gracefully
        image_service = LinkedInImageService()
        
        # Primary image selection should fail gracefully
        selected_image = image_service.get_post_image(post)
        self.assertIsNone(selected_image)
        
        # Fallback images should also handle failures
        fallback_images = image_service.get_fallback_images(post)
        self.assertEqual(len(fallback_images), 0)
        
        # Best compatible image should return None
        best_image = image_service.select_best_compatible_image(post)
        self.assertIsNone(best_image)


class LinkedInImagePerformanceTest(TestCase):
    """
    Test performance with various image sizes and formats.
    
    This test class focuses on:
    - Performance benchmarking with different image sizes
    - Memory usage monitoring
    - Processing time optimization
    - Scalability testing
    
    Requirements: 3.5
    """
    
    def setUp(self):
        """Set up test data for performance testing."""
        # Create temporary directory
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.temp_dir)
        
        # Create performance test images
        self.performance_images = self._create_performance_test_images()
        
        # Initialize processor
        self.processor = ImageProcessor()
    
    def _create_performance_test_images(self):
        """Create images of various sizes for performance testing."""
        images = {}
        
        # Small image (baseline)
        small_img = Image.new('RGB', (800, 600), color='red')
        small_path = os.path.join(self.temp_dir, 'small.jpg')
        small_img.save(small_path, 'JPEG', quality=85)
        images['small'] = small_path
        
        # Medium image
        medium_img = Image.new('RGB', (1920, 1080), color='green')
        medium_path = os.path.join(self.temp_dir, 'medium.jpg')
        medium_img.save(medium_path, 'JPEG', quality=85)
        images['medium'] = medium_path
        
        # Large image
        large_img = Image.new('RGB', (3840, 2160), color='blue')
        large_path = os.path.join(self.temp_dir, 'large.jpg')
        large_img.save(large_path, 'JPEG', quality=85)
        images['large'] = large_path
        
        # High-quality PNG
        png_img = Image.new('RGBA', (2000, 1500), color=(255, 0, 0, 200))
        png_path = os.path.join(self.temp_dir, 'high_quality.png')
        png_img.save(png_path, 'PNG')
        images['png'] = png_path
        
        return images
    
    def test_processing_time_by_image_size(self):
        """Test processing time scales reasonably with image size."""
        processing_times = {}
        
        for size_name, image_path in self.performance_images.items():
            output_path = os.path.join(self.temp_dir, f'processed_{size_name}.jpg')
            
            start_time = time.time()
            
            try:
                result_path = self.processor.process_for_linkedin(image_path, output_path)
                processing_time = time.time() - start_time
                processing_times[size_name] = processing_time
                
                # Verify processing succeeded
                self.assertTrue(os.path.exists(result_path))
                
            except ImageProcessingError as e:
                continue
        
        # Verify processing times are reasonable
        for size_name, processing_time in processing_times.items():
            if size_name == 'small':
                self.assertLess(processing_time, 5.0)  # Small images should be very fast
            elif size_name == 'medium':
                self.assertLess(processing_time, 10.0)  # Medium images should be fast
            elif size_name == 'large':
                self.assertLess(processing_time, 20.0)  # Large images may take longer
    
    def test_memory_usage_during_processing(self):
        """Test memory usage doesn't grow excessively during processing."""
        try:
            import psutil
            import gc
            
            process = psutil.Process()
            initial_memory = process.memory_info().rss
            
            # Process each image and monitor memory
            max_memory_usage = initial_memory
            
            for size_name, image_path in self.performance_images.items():
                output_path = os.path.join(self.temp_dir, f'memory_{size_name}.jpg')
                
                try:
                    # Process image
                    self.processor.process_for_linkedin(image_path, output_path)
                    
                    # Check memory usage
                    current_memory = process.memory_info().rss
                    max_memory_usage = max(max_memory_usage, current_memory)
                    
                    # Force garbage collection
                    gc.collect()
                    
                except ImageProcessingError:
                    continue
            
            # Calculate memory increase
            memory_increase = max_memory_usage - initial_memory
            
            # Memory increase should be reasonable (less than 200MB)
            max_acceptable_increase = 200 * 1024 * 1024  # 200MB
            self.assertLess(memory_increase, max_acceptable_increase)
            
        except ImportError:
            # Skip test if psutil is not available
            self.skipTest("psutil not available for memory testing")


if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # Run the tests
    import unittest
    unittest.main()