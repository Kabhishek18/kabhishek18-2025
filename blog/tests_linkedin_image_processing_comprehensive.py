"""
Comprehensive unit tests for LinkedIn image processing functionality.

This test suite covers Task 8 requirements:
- Test image selection logic with various blog post configurations
- Test image validation and processing methods
- Test LinkedIn API integration with mock responses
- Test error handling and fallback scenarios
- Test image metadata extraction and processing

Requirements covered: 1.4, 3.3, 4.1, 4.5
"""

import os
import tempfile
import shutil
import json
from unittest.mock import Mock, patch, MagicMock, mock_open
from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
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
except ImportError as e:
    # Handle import errors gracefully for validation
    print(f"Import warning: {e}")
    pass


class LinkedInImageSelectionTest(TestCase):
    """Test image selection logic with various blog post configurations."""
    
    def setUp(self):
        """Set up test data for image selection tests."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.category = Category.objects.create(name='Test Category')
        self.tag = Tag.objects.create(name='Test Tag')
        
        # Create temporary directory for test images
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.temp_dir)
        
        # Create test images with different characteristics
        self.test_images = self._create_test_images()
    
    def _create_test_images(self):
        """Create test image files with different characteristics."""
        images = {}
        
        # LinkedIn-compatible image
        compatible_img = Image.new('RGB', (1200, 627), color='red')
        compatible_path = os.path.join(self.temp_dir, 'compatible.jpg')
        compatible_img.save(compatible_path, 'JPEG', quality=85)
        images['compatible'] = compatible_path
        
        # Oversized image
        oversized_img = Image.new('RGB', (8000, 5000), color='blue')
        oversized_path = os.path.join(self.temp_dir, 'oversized.jpg')
        oversized_img.save(oversized_path, 'JPEG', quality=85)
        images['oversized'] = oversized_path
        
        # Undersized image
        undersized_img = Image.new('RGB', (100, 100), color='green')
        undersized_path = os.path.join(self.temp_dir, 'undersized.jpg')
        undersized_img.save(undersized_path, 'JPEG', quality=85)
        images['undersized'] = undersized_path
        
        # PNG with transparency
        png_img = Image.new('RGBA', (800, 600), color=(255, 0, 0, 128))
        png_path = os.path.join(self.temp_dir, 'transparent.png')
        png_img.save(png_path, 'PNG')
        images['png'] = png_path
        
        # GIF image
        gif_img = Image.new('P', (600, 400), color=0)
        gif_path = os.path.join(self.temp_dir, 'animated.gif')
        gif_img.save(gif_path, 'GIF')
        images['gif'] = gif_path
        
        return images
    
    def _create_uploaded_file(self, image_path, field_name='image.jpg'):
        """Create a Django UploadedFile from an image path."""
        with open(image_path, 'rb') as f:
            return SimpleUploadedFile(
                field_name,
                f.read(),
                content_type='image/jpeg'
            )
    
    def _create_post_with_images(self, social_image=None, featured_image=None, media_images=None):
        """Create a post with specified image configurations."""
        post = Post.objects.create(
            title='Test Post with Images',
            slug='test-post-images',
            author=self.user,
            content='Test content with various image configurations.',
            excerpt='Test excerpt',
            status='published'
        )
        post.categories.add(self.category)
        post.tags.add(self.tag)
        
        # Add social image if specified
        if social_image:
            social_file = self._create_uploaded_file(social_image, 'social.jpg')
            post.social_image = social_file
        
        # Add featured image if specified
        if featured_image:
            featured_file = self._create_uploaded_file(featured_image, 'featured.jpg')
            post.featured_image = featured_file
        
        post.save()
        
        # Add media items if specified
        if media_images:
            for i, (image_path, is_featured) in enumerate(media_images):
                media_file = self._create_uploaded_file(image_path, f'media_{i}.jpg')
                MediaItem.objects.create(
                    post=post,
                    media_type='image',
                    title=f'Media Item {i}',
                    original_image=media_file,
                    is_featured=is_featured,
                    order=i
                )
        
        return post
    
    def test_image_selection_social_image_priority(self):
        """Test that social_image has highest priority in selection."""
        post = self._create_post_with_images(
            social_image=self.test_images['compatible'],
            featured_image=self.test_images['oversized'],
            media_images=[(self.test_images['png'], True)]
        )
        
        selected_image = LinkedInImageService.get_post_image(post)
        
        self.assertIsNotNone(selected_image)
        self.assertIn('social.jpg', selected_image)
    
    def test_image_selection_featured_image_fallback(self):
        """Test that featured_image is selected when no social_image."""
        post = self._create_post_with_images(
            featured_image=self.test_images['compatible'],
            media_images=[(self.test_images['png'], True)]
        )
        
        selected_image = LinkedInImageService.get_post_image(post)
        
        self.assertIsNotNone(selected_image)
        self.assertIn('featured.jpg', selected_image)
    
    def test_image_selection_media_item_fallback(self):
        """Test that featured media item is selected when no other images."""
        post = self._create_post_with_images(
            media_images=[
                (self.test_images['undersized'], False),
                (self.test_images['compatible'], True),  # Featured
                (self.test_images['png'], False)
            ]
        )
        
        selected_image = LinkedInImageService.get_post_image(post)
        
        self.assertIsNotNone(selected_image)
        self.assertIn('media_1.jpg', selected_image)  # The featured one
    
    def test_image_selection_first_media_item_fallback(self):
        """Test that first media item is selected when no featured media."""
        post = self._create_post_with_images(
            media_images=[
                (self.test_images['compatible'], False),  # First, not featured
                (self.test_images['png'], False),
                (self.test_images['gif'], False)
            ]
        )
        
        selected_image = LinkedInImageService.get_post_image(post)
        
        self.assertIsNotNone(selected_image)
        self.assertIn('media_0.jpg', selected_image)  # First one
    
    def test_image_selection_no_images(self):
        """Test that None is returned when no images are available."""
        post = Post.objects.create(
            title='Post Without Images',
            slug='post-no-images',
            author=self.user,
            content='Content without any images.',
            status='published'
        )
        
        selected_image = LinkedInImageService.get_post_image(post)
        
        self.assertIsNone(selected_image)
    
    def test_image_selection_broken_image_fields(self):
        """Test image selection handles broken image fields gracefully."""
        post = Post.objects.create(
            title='Post with Broken Images',
            slug='post-broken-images',
            author=self.user,
            content='Content with broken image references.',
            status='published'
        )
        
        # Simulate broken image field by setting to non-existent file
        post.social_image.name = 'non_existent_image.jpg'
        post.featured_image.name = 'another_non_existent.jpg'
        post.save()
        
        # Should handle gracefully and return None
        selected_image = LinkedInImageService.get_post_image(post)
        
        self.assertIsNone(selected_image)
    
    def test_fallback_images_collection(self):
        """Test comprehensive fallback image collection."""
        post = self._create_post_with_images(
            social_image=self.test_images['compatible'],
            featured_image=self.test_images['oversized'],
            media_images=[
                (self.test_images['png'], True),
                (self.test_images['gif'], False),
                (self.test_images['undersized'], False)
            ]
        )
        
        fallback_images = LinkedInImageService.get_fallback_images(post)
        
        # Should have 5 images total
        self.assertEqual(len(fallback_images), 5)
        
        # Should be in priority order
        self.assertIn('social.jpg', fallback_images[0])
        self.assertIn('featured.jpg', fallback_images[1])
        self.assertIn('media_', fallback_images[2])  # First media item
    
    def test_fallback_images_deduplication(self):
        """Test that fallback images removes duplicates while preserving order."""
        # Create post where social and featured point to same image
        post = self._create_post_with_images(
            social_image=self.test_images['compatible'],
            featured_image=self.test_images['compatible'],  # Same image
            media_images=[(self.test_images['png'], False)]
        )
        
        fallback_images = LinkedInImageService.get_fallback_images(post)
        
        # Should have unique URLs only
        unique_images = set(fallback_images)
        self.assertEqual(len(unique_images), len(fallback_images))
        
        # Should still maintain reasonable count (not duplicated)
        self.assertLessEqual(len(fallback_images), 3)


class LinkedInImageValidationTest(TestCase):
    """Test image validation and processing methods."""
    
    def setUp(self):
        """Set up test data for validation tests."""
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.temp_dir)
        
        # Create test images with known characteristics
        self.test_images = self._create_validation_test_images()
    
    def _create_validation_test_images(self):
        """Create images with specific characteristics for validation testing."""
        images = {}
        
        # Perfect LinkedIn image
        perfect_img = Image.new('RGB', (1200, 627), color='red')
        perfect_path = os.path.join(self.temp_dir, 'perfect.jpg')
        perfect_img.save(perfect_path, 'JPEG', quality=85, optimize=True)
        images['perfect'] = perfect_path
        
        # Minimum size image
        min_img = Image.new('RGB', (200, 200), color='blue')
        min_path = os.path.join(self.temp_dir, 'minimum.jpg')
        min_img.save(min_path, 'JPEG', quality=85)
        images['minimum'] = min_path
        
        # Maximum size image (within limits)
        max_img = Image.new('RGB', (7680, 4320), color='green')
        max_path = os.path.join(self.temp_dir, 'maximum.jpg')
        max_img.save(max_path, 'JPEG', quality=50)  # Lower quality to manage file size
        images['maximum'] = max_path
        
        # Too small image
        tiny_img = Image.new('RGB', (100, 100), color='yellow')
        tiny_path = os.path.join(self.temp_dir, 'tiny.jpg')
        tiny_img.save(tiny_path, 'JPEG', quality=85)
        images['tiny'] = tiny_path
        
        # Wrong aspect ratio (too wide)
        wide_img = Image.new('RGB', (2000, 500), color='purple')
        wide_path = os.path.join(self.temp_dir, 'wide.jpg')
        wide_img.save(wide_path, 'JPEG', quality=85)
        images['wide'] = wide_path
        
        # Wrong aspect ratio (too tall)
        tall_img = Image.new('RGB', (500, 2000), color='orange')
        tall_path = os.path.join(self.temp_dir, 'tall.jpg')
        tall_img.save(tall_path, 'JPEG', quality=85)
        images['tall'] = tall_path
        
        # PNG with transparency
        png_img = Image.new('RGBA', (800, 600), color=(255, 0, 0, 128))
        png_path = os.path.join(self.temp_dir, 'transparent.png')
        png_img.save(png_path, 'PNG')
        images['png'] = png_path
        
        # Unsupported format (BMP)
        bmp_img = Image.new('RGB', (800, 600), color='cyan')
        bmp_path = os.path.join(self.temp_dir, 'unsupported.bmp')
        bmp_img.save(bmp_path, 'BMP')
        images['bmp'] = bmp_path
        
        return images
    
    def test_validate_perfect_image(self):
        """Test validation of perfect LinkedIn-compatible image."""
        is_valid, validation_info = ImageProcessor.validate_image_dimensions(self.test_images['perfect'])
        
        self.assertTrue(is_valid)
        self.assertEqual(len(validation_info['errors']), 0)
        self.assertEqual(validation_info['width'], 1200)
        self.assertEqual(validation_info['height'], 627)
        self.assertEqual(validation_info['format'], 'JPEG')
    
    def test_validate_minimum_size_image(self):
        """Test validation of minimum size image."""
        is_valid, validation_info = ImageProcessor.validate_image_dimensions(self.test_images['minimum'])
        
        self.assertTrue(is_valid)
        self.assertEqual(len(validation_info['errors']), 0)
        self.assertEqual(validation_info['width'], 200)
        self.assertEqual(validation_info['height'], 200)
    
    def test_validate_maximum_size_image(self):
        """Test validation of maximum size image."""
        is_valid, validation_info = ImageProcessor.validate_image_dimensions(self.test_images['maximum'])
        
        self.assertTrue(is_valid)
        self.assertEqual(len(validation_info['errors']), 0)
        self.assertEqual(validation_info['width'], 7680)
        self.assertEqual(validation_info['height'], 4320)
    
    def test_validate_too_small_image(self):
        """Test validation of image that's too small."""
        is_valid, validation_info = ImageProcessor.validate_image_dimensions(self.test_images['tiny'])
        
        self.assertFalse(is_valid)
        self.assertGreater(len(validation_info['errors']), 0)
        self.assertIn('below minimum', validation_info['errors'][0])
    
    def test_validate_wrong_aspect_ratio_wide(self):
        """Test validation of image with wrong aspect ratio (too wide)."""
        is_valid, validation_info = ImageProcessor.validate_image_dimensions(self.test_images['wide'])
        
        # Should be valid (no errors) but have warnings about aspect ratio
        self.assertTrue(is_valid)
        self.assertEqual(len(validation_info['errors']), 0)
        self.assertGreater(len(validation_info['warnings']), 0)
        self.assertIn('aspect ratio', validation_info['warnings'][0].lower())
    
    def test_validate_wrong_aspect_ratio_tall(self):
        """Test validation of image with wrong aspect ratio (too tall)."""
        is_valid, validation_info = ImageProcessor.validate_image_dimensions(self.test_images['tall'])
        
        # Should be valid (no errors) but have warnings about aspect ratio
        self.assertTrue(is_valid)
        self.assertEqual(len(validation_info['errors']), 0)
        self.assertGreater(len(validation_info['warnings']), 0)
        self.assertIn('aspect ratio', validation_info['warnings'][0].lower())
    
    def test_validate_png_format(self):
        """Test validation of PNG format image."""
        is_valid, validation_info = ImageProcessor.validate_image_dimensions(self.test_images['png'])
        
        self.assertTrue(is_valid)
        self.assertEqual(validation_info['format'], 'PNG')
        self.assertEqual(validation_info['mode'], 'RGBA')
    
    def test_validate_unsupported_format(self):
        """Test validation of unsupported format image."""
        is_valid, validation_info = ImageProcessor.validate_image_dimensions(self.test_images['bmp'])
        
        self.assertFalse(is_valid)
        self.assertGreater(len(validation_info['errors']), 0)
        self.assertIn('not supported', validation_info['errors'][0])
    
    def test_file_size_validation_valid(self):
        """Test file size validation for valid file."""
        is_valid, file_size = ImageProcessor.validate_image_file_size(self.test_images['perfect'])
        
        self.assertTrue(is_valid)
        self.assertGreater(file_size, 0)
        self.assertLessEqual(file_size, ImageProcessor.MAX_FILE_SIZE)
    
    def test_linkedin_compatibility_check_valid(self):
        """Test LinkedIn compatibility check for valid image."""
        is_compatible, issues = ImageProcessor.is_linkedin_compatible(self.test_images['perfect'])
        
        self.assertTrue(is_compatible)
        self.assertEqual(len(issues), 0)
    
    def test_linkedin_compatibility_check_invalid(self):
        """Test LinkedIn compatibility check for invalid image."""
        is_compatible, issues = ImageProcessor.is_linkedin_compatible(self.test_images['tiny'])
        
        self.assertFalse(is_compatible)
        self.assertGreater(len(issues), 0)
    
    def test_image_metadata_extraction(self):
        """Test comprehensive image metadata extraction."""
        metadata = ImageProcessor.get_image_metadata(self.test_images['perfect'])
        
        self.assertEqual(metadata['width'], 1200)
        self.assertEqual(metadata['height'], 627)
        self.assertEqual(metadata['format'], 'JPEG')
        self.assertEqual(metadata['mode'], 'RGB')
        self.assertAlmostEqual(metadata['aspect_ratio'], 1.91, places=2)
        self.assertGreater(metadata['file_size'], 0)
        self.assertFalse(metadata['has_transparency'])
    
    def test_image_metadata_extraction_png(self):
        """Test metadata extraction for PNG with transparency."""
        metadata = ImageProcessor.get_image_metadata(self.test_images['png'])
        
        self.assertEqual(metadata['format'], 'PNG')
        self.assertEqual(metadata['mode'], 'RGBA')
        self.assertTrue(metadata['has_transparency'])
    
    @patch('blog.utils.image_processor.ImageProcessor.validate_image_file_size')
    def test_image_processing_error_handling(self, mock_file_size):
        """Test error handling in image processing."""
        # Mock file size validation to raise an exception
        mock_file_size.side_effect = OSError("File not found")
        
        # Should handle the error gracefully
        is_valid, file_size = ImageProcessor.validate_image_file_size('nonexistent.jpg')
        
        self.assertFalse(is_valid)
        self.assertEqual(file_size, 0)


class LinkedInImageProcessingTest(TestCase):
    """Test image processing methods including resizing and format conversion."""
    
    def setUp(self):
        """Set up test data for processing tests."""
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.temp_dir)
        
        # Create test images for processing
        self.test_images = self._create_processing_test_images()
    
    def _create_processing_test_images(self):
        """Create images for processing tests."""
        images = {}
        
        # Large image that needs resizing
        large_img = Image.new('RGB', (3000, 2000), color='red')
        large_path = os.path.join(self.temp_dir, 'large.jpg')
        large_img.save(large_path, 'JPEG', quality=85)
        images['large'] = large_path
        
        # PNG with transparency
        png_img = Image.new('RGBA', (1000, 800), color=(255, 0, 0, 128))
        png_path = os.path.join(self.temp_dir, 'transparent.png')
        png_img.save(png_path, 'PNG')
        images['png'] = png_path
        
        # GIF image
        gif_img = Image.new('P', (800, 600), color=0)
        gif_path = os.path.join(self.temp_dir, 'animated.gif')
        gif_img.save(gif_path, 'GIF')
        images['gif'] = gif_path
        
        return images
    
    def test_resize_image_for_linkedin(self):
        """Test image resizing for LinkedIn requirements."""
        output_path = os.path.join(self.temp_dir, 'resized.jpg')
        
        result_path = ImageProcessor.resize_image_for_linkedin(
            self.test_images['large'],
            output_path,
            target_dimensions=(1200, 627)
        )
        
        self.assertEqual(result_path, output_path)
        self.assertTrue(os.path.exists(output_path))
        
        # Check resized image dimensions
        with Image.open(output_path) as img:
            # Should maintain aspect ratio and fit within target
            self.assertLessEqual(img.width, 1200)
            self.assertLessEqual(img.height, 627)
    
    def test_convert_image_format_to_jpeg(self):
        """Test converting PNG to JPEG format."""
        output_path = os.path.join(self.temp_dir, 'converted.jpg')
        
        result_path = ImageProcessor.convert_image_format(
            self.test_images['png'],
            'JPEG',
            output_path
        )
        
        self.assertEqual(result_path, output_path)
        self.assertTrue(os.path.exists(output_path))
        
        # Check converted image
        with Image.open(output_path) as img:
            self.assertEqual(img.format, 'JPEG')
            self.assertEqual(img.mode, 'RGB')  # Should convert from RGBA
    
    def test_convert_image_format_to_png(self):
        """Test converting JPEG to PNG format."""
        output_path = os.path.join(self.temp_dir, 'converted.png')
        
        result_path = ImageProcessor.convert_image_format(
            self.test_images['large'],
            'PNG',
            output_path
        )
        
        self.assertEqual(result_path, output_path)
        self.assertTrue(os.path.exists(output_path))
        
        # Check converted image
        with Image.open(output_path) as img:
            self.assertEqual(img.format, 'PNG')
            self.assertEqual(img.mode, 'RGBA')  # Should convert to RGBA
    
    def test_optimize_image_for_web(self):
        """Test image optimization for web usage."""
        output_path = os.path.join(self.temp_dir, 'optimized.jpg')
        
        result_path = ImageProcessor.optimize_image_for_web(
            self.test_images['large'],
            output_path,
            quality=75
        )
        
        self.assertEqual(result_path, output_path)
        self.assertTrue(os.path.exists(output_path))
        
        # Optimized file should be smaller than original
        original_size = os.path.getsize(self.test_images['large'])
        optimized_size = os.path.getsize(output_path)
        self.assertLess(optimized_size, original_size)
    
    def test_process_for_linkedin_oversized_image(self):
        """Test complete LinkedIn processing for oversized image."""
        output_path = os.path.join(self.temp_dir, 'linkedin_processed.jpg')
        
        result_path = ImageProcessor.process_for_linkedin(
            self.test_images['large'],
            output_path
        )
        
        self.assertEqual(result_path, output_path)
        self.assertTrue(os.path.exists(output_path))
        
        # Check that processed image is LinkedIn compatible
        is_compatible, issues = ImageProcessor.is_linkedin_compatible(output_path)
        self.assertTrue(is_compatible)
        self.assertEqual(len(issues), 0)
    
    def test_process_for_linkedin_unsupported_format(self):
        """Test LinkedIn processing for unsupported format."""
        # Create BMP image
        bmp_img = Image.new('RGB', (800, 600), color='blue')
        bmp_path = os.path.join(self.temp_dir, 'test.bmp')
        bmp_img.save(bmp_path, 'BMP')
        
        output_path = os.path.join(self.temp_dir, 'linkedin_from_bmp.jpg')
        
        result_path = ImageProcessor.process_for_linkedin(bmp_path, output_path)
        
        self.assertEqual(result_path, output_path)
        self.assertTrue(os.path.exists(output_path))
        
        # Should be converted to JPEG
        with Image.open(output_path) as img:
            self.assertEqual(img.format, 'JPEG')
    
    @patch('blog.utils.image_processor.requests.get')
    def test_download_and_process_image_success(self, mock_get):
        """Test successful image download and processing."""
        # Mock successful HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'content-type': 'image/jpeg'}
        
        # Read actual image data
        with open(self.test_images['large'], 'rb') as f:
            image_data = f.read()
        
        mock_response.iter_content.return_value = [image_data[i:i+8192] for i in range(0, len(image_data), 8192)]
        mock_get.return_value = mock_response
        
        result_path = ImageProcessor.download_and_process_image(
            'https://example.com/image.jpg',
            self.temp_dir
        )
        
        self.assertIsNotNone(result_path)
        self.assertTrue(os.path.exists(result_path))
        self.assertIn('linkedin_', os.path.basename(result_path))
    
    @patch('blog.utils.image_processor.requests.get')
    def test_download_and_process_image_network_error(self, mock_get):
        """Test image download with network error."""
        # Mock network error
        mock_get.side_effect = requests.RequestException("Network error")
        
        with self.assertRaises(ImageProcessingError):
            ImageProcessor.download_and_process_image(
                'https://example.com/image.jpg',
                self.temp_dir
            )
    
    @patch('blog.utils.image_processor.requests.get')
    def test_download_and_process_image_invalid_content_type(self, mock_get):
        """Test image download with invalid content type."""
        # Mock response with non-image content type
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'content-type': 'text/html'}
        mock_get.return_value = mock_response
        
        with self.assertRaises(ImageProcessingError):
            ImageProcessor.download_and_process_image(
                'https://example.com/image.jpg',
                self.temp_dir
            )
    
    def test_image_processing_error_exception(self):
        """Test ImageProcessingError exception handling."""
        error = ImageProcessingError("Test error message")
        
        self.assertEqual(str(error), "Test error message")
        self.assertIsInstance(error, Exception)
    
    def test_format_conversion_jpeg_to_png(self):
        """Test format conversion from JPEG to PNG."""
        output_path = os.path.join(self.temp_dir, 'converted_to_png.png')
        
        result_path = ImageProcessor.convert_image_format(
            self.test_images['large'],
            'PNG',
            output_path
        )
        
        self.assertEqual(result_path, output_path)
        self.assertTrue(os.path.exists(output_path))
        
        # Verify format conversion
        with Image.open(output_path) as img:
            self.assertEqual(img.format, 'PNG')
    
    def test_format_conversion_png_to_gif(self):
        """Test format conversion from PNG to GIF."""
        output_path = os.path.join(self.temp_dir, 'converted_to_gif.gif')
        
        result_path = ImageProcessor.convert_image_format(
            self.test_images['png'],
            'GIF',
            output_path
        )
        
        self.assertEqual(result_path, output_path)
        self.assertTrue(os.path.exists(output_path))
        
        # Verify format conversion
        with Image.open(output_path) as img:
            self.assertEqual(img.format, 'GIF')


class LinkedInAPIImageIntegrationTest(TestCase):
    """Test LinkedIn API integration with mock responses for image functionality."""
    
    def setUp(self):
        """Set up test data for API integration tests."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create LinkedIn configuration
        self.config = LinkedInConfig.objects.create(
            client_id='test_client_id',
            is_active=True
        )
        self.config.set_client_secret('test_secret')
        self.config.set_access_token('test_token')
        self.config.save()
        
        self.service = LinkedInAPIService(self.config)
        
        # Create test post
        self.post = Post.objects.create(
            title='Test Post for API',
            slug='test-post-api',
            author=self.user,
            content='Test content for API integration.',
            status='published'
        )
    
    @patch('blog.services.linkedin_service.requests.Session.post')
    def test_upload_media_success(self, mock_post):
        """Test successful media upload to LinkedIn."""
        # Mock successful media upload response
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            'value': {
                'asset': 'urn:li:digitalmediaAsset:test_media_id_12345'
            }
        }
        mock_post.return_value = mock_response
        
        # Test media upload
        media_id = self.service.upload_media('https://example.com/image.jpg')
        
        self.assertEqual(media_id, 'urn:li:digitalmediaAsset:test_media_id_12345')
        mock_post.assert_called_once()
    
    @patch('blog.services.linkedin_service.requests.Session.post')
    def test_upload_media_failure(self, mock_post):
        """Test media upload failure handling."""
        # Mock failed media upload response
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            'message': 'Invalid media format',
            'serviceErrorCode': 'INVALID_MEDIA'
        }
        mock_post.return_value = mock_response
        
        # Test that appropriate exception is raised
        with self.assertRaises(LinkedInAPIError):
            self.service.upload_media('https://example.com/invalid.txt')
    
    @patch('blog.services.linkedin_service.requests.Session.post')
    def test_create_post_with_media_success(self, mock_post):
        """Test successful post creation with media."""
        # Mock successful post creation response
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            'id': 'urn:li:ugcPost:test_post_id_67890',
            'lifecycleState': 'PUBLISHED'
        }
        mock_post.return_value = mock_response
        
        # Test post creation with media
        result = self.service.create_post_with_media(
            title='Test Post',
            content='Test content',
            url='https://example.com/post',
            media_id='urn:li:digitalmediaAsset:test_media_id'
        )
        
        self.assertEqual(result['id'], 'urn:li:ugcPost:test_post_id_67890')
        mock_post.assert_called_once()
        
        # Check that request included media
        call_args = mock_post.call_args
        request_data = json.loads(call_args[1]['data'])
        self.assertIn('media', request_data['specificContent']['com.linkedin.ugc.ShareContent'])
    
    @patch('blog.services.linkedin_service.LinkedInAPIService.upload_media')
    @patch('blog.services.linkedin_service.LinkedInAPIService.create_post_with_media')
    def test_end_to_end_image_posting(self, mock_create_post, mock_upload):
        """Test end-to-end image posting workflow."""
        # Mock successful media upload
        mock_upload.return_value = 'urn:li:digitalmediaAsset:test_media_id'
        
        # Mock successful post creation
        mock_create_post.return_value = {
            'id': 'urn:li:ugcPost:test_post_id',
            'lifecycleState': 'PUBLISHED'
        }
        
        # Test complete workflow
        result = self.service.create_post(
            title='Test Post with Image',
            content='Test content',
            url='https://example.com/post',
            image_url='https://example.com/image.jpg'
        )
        
        # Verify both upload and post creation were called
        mock_upload.assert_called_once_with('https://example.com/image.jpg')
        mock_create_post.assert_called_once()
        
        self.assertEqual(result['id'], 'urn:li:ugcPost:test_post_id')
    
    @patch('blog.services.linkedin_service.LinkedInAPIService.upload_media')
    @patch('blog.services.linkedin_service.LinkedInAPIService.create_post')
    def test_image_upload_failure_fallback(self, mock_create_post, mock_upload):
        """Test fallback to text-only post when image upload fails."""
        # Mock failed media upload
        mock_upload.side_effect = LinkedInAPIError("Media upload failed")
        
        # Mock successful text-only post creation
        mock_create_post.return_value = {
            'id': 'urn:li:ugcPost:text_only_post',
            'lifecycleState': 'PUBLISHED'
        }
        
        # Test that fallback mechanism works
        result = self.service.create_post(
            title='Test Post',
            content='Test content',
            url='https://example.com/post',
            image_url='https://example.com/image.jpg'
        )
        
        # Should have attempted upload and fallen back to text-only
        mock_upload.assert_called_once()
        mock_create_post.assert_called_once()
        
        # Verify text-only post was created
        self.assertEqual(result['id'], 'urn:li:ugcPost:text_only_post')
    
    @patch('blog.services.linkedin_service.requests.Session.get')
    def test_api_integration_authentication_error(self, mock_get):
        """Test API integration handles authentication errors properly."""
        # Mock authentication error response
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {
            'error': 'invalid_token',
            'error_description': 'The access token is invalid'
        }
        mock_get.return_value = mock_response
        
        # Test that authentication error is handled
        with self.assertRaises(LinkedInAPIError):
            self.service._make_authenticated_request('GET', 'https://api.linkedin.com/v2/people/~')
    
    @patch('blog.services.linkedin_service.requests.Session.post')
    def test_api_integration_rate_limit_handling(self, mock_post):
        """Test API integration handles rate limiting properly."""
        # Mock rate limit response
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {'Retry-After': '3600'}
        mock_response.json.return_value = {
            'message': 'Rate limit exceeded'
        }
        mock_post.return_value = mock_response
        
        # Test that rate limit is handled
        with self.assertRaises(LinkedInAPIError):
            self.service.upload_media('https://example.com/image.jpg')


class LinkedInImageErrorHandlingTest(TestCase):
    """Test error handling and fallback scenarios for image processing."""
    
    def setUp(self):
        """Set up test data for error handling tests."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.post = Post.objects.create(
            title='Test Post for Error Handling',
            slug='test-post-errors',
            author=self.user,
            content='Test content for error scenarios.',
            status='published'
        )
        
        # Create temporary directory
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.temp_dir)
    
    def test_image_selection_with_corrupted_files(self):
        """Test image selection handles corrupted image files."""
        # Create a corrupted "image" file
        corrupted_path = os.path.join(self.temp_dir, 'corrupted.jpg')
        with open(corrupted_path, 'w') as f:
            f.write("This is not an image file")
        
        # Create uploaded file from corrupted data
        with open(corrupted_path, 'rb') as f:
            corrupted_file = SimpleUploadedFile(
                'corrupted.jpg',
                f.read(),
                content_type='image/jpeg'
            )
        
        self.post.featured_image = corrupted_file
        self.post.save()
        
        # Should handle gracefully and return None
        selected_image = LinkedInImageService.get_post_image(self.post)
        
        # Might return the URL but validation should catch the corruption
        if selected_image:
            is_valid, issues = LinkedInImageService.validate_image_for_linkedin(selected_image)
            self.assertFalse(is_valid)
            self.assertGreater(len(issues), 0)
    
    @patch('blog.services.linkedin_image_service.ImageProcessor.download_and_process_image')
    def test_image_validation_download_failure(self, mock_download):
        """Test image validation handles download failures."""
        # Mock download failure
        mock_download.side_effect = ImageProcessingError("Download failed")
        
        is_valid, issues = LinkedInImageService.validate_image_for_linkedin('https://example.com/image.jpg')
        
        self.assertFalse(is_valid)
        self.assertIn('Failed to download/process image', issues[0])
    
    @patch('blog.services.linkedin_image_service.ImageProcessor.get_image_metadata')
    def test_metadata_extraction_error_handling(self, mock_metadata):
        """Test metadata extraction handles processing errors."""
        # Mock metadata extraction failure
        mock_metadata.side_effect = Exception("Metadata extraction failed")
        
        metadata = LinkedInImageService.get_image_metadata('https://example.com/image.jpg')
        
        self.assertFalse(metadata['accessible'])
        self.assertIn('error', metadata)
        self.assertIn('Metadata extraction failed', metadata['error'])
    
    def test_fallback_image_selection_with_all_invalid(self):
        """Test fallback selection when all images are invalid."""
        # Create multiple invalid images
        tiny_img = Image.new('RGB', (50, 50), color='red')
        tiny_path = os.path.join(self.temp_dir, 'tiny.jpg')
        tiny_img.save(tiny_path, 'JPEG')
        
        # Add invalid images to post
        with open(tiny_path, 'rb') as f:
            tiny_file = SimpleUploadedFile('tiny.jpg', f.read(), content_type='image/jpeg')
        
        self.post.featured_image = tiny_file
        self.post.save()
        
        # Should return None when no compatible images found
        best_image = LinkedInImageService.select_best_compatible_image(self.post)
        
        self.assertIsNone(best_image)
    
    @patch('blog.utils.image_processor.ImageProcessor.process_for_linkedin')
    def test_image_processing_failure_handling(self, mock_process):
        """Test handling of image processing failures."""
        # Mock processing failure
        mock_process.side_effect = ImageProcessingError("Processing failed")
        
        result = LinkedInImageService.process_image_for_linkedin('https://example.com/image.jpg')
        
        self.assertIsNone(result)
    
    def test_service_initialization_error_handling(self):
        """Test service initialization with invalid configuration."""
        # Test with None config
        service = LinkedInImageService(base_url=None)
        
        # Should still initialize with fallback base URL
        self.assertIsNotNone(service.base_url)
        self.assertTrue(service.base_url.startswith('https://'))
    
    @patch('blog.services.linkedin_image_service.LinkedInImageService.get_fallback_images')
    def test_comprehensive_image_info_error_handling(self, mock_fallback):
        """Test comprehensive image info handles various error scenarios."""
        # Mock fallback images failure
        mock_fallback.side_effect = Exception("Fallback images failed")
        
        result = LinkedInImageService.get_image_for_linkedin_post(self.post)
        
        # Should handle error gracefully and return None
        self.assertIsNone(result)
    
    def test_url_validation_edge_cases(self):
        """Test URL validation with various edge cases."""
        invalid_urls = [
            '',
            None,
            'not-a-url',
            'ftp://example.com/image.jpg',
            'javascript:alert("xss")',
            'data:image/jpeg;base64,invalid',
            'https://',
            'https://example.com/',  # No image extension
        ]
        
        for invalid_url in invalid_urls:
            is_valid, issues = LinkedInImageService.validate_image_for_linkedin(invalid_url)
            self.assertFalse(is_valid, f"URL should be invalid: {invalid_url}")
            self.assertGreater(len(issues), 0, f"Should have issues for: {invalid_url}")


class LinkedInContentFormatterImageTest(TestCase):
    """Test LinkedIn content formatter integration with image functionality."""
    
    def setUp(self):
        """Set up test data for content formatter tests."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.post = Post.objects.create(
            title='Test Post for Content Formatting',
            slug='test-post-formatting',
            author=self.user,
            content='Test content for content formatting with images.',
            excerpt='Test excerpt for formatting',
            status='published'
        )
        
        self.formatter = LinkedInContentFormatter()
    
    @patch('blog.services.linkedin_content_formatter.LinkedInImageService.get_fallback_images')
    def test_format_post_content_with_images(self, mock_images):
        """Test content formatting optimization for posts with images."""
        # Mock that post has images available
        mock_images.return_value = ['https://example.com/image1.jpg', 'https://example.com/image2.jpg']
        
        formatted_content = self.formatter.format_post_content(
            self.post,
            include_excerpt=True,
            optimize_for_images=True
        )
        
        # Content should be formatted and potentially shortened for image posts
        self.assertIsNotNone(formatted_content)
        self.assertIn(self.post.title, formatted_content)
        self.assertLessEqual(len(formatted_content), LinkedInContentFormatter.MAX_POST_LENGTH)
    
    @patch('blog.services.linkedin_content_formatter.LinkedInImageService.get_fallback_images')
    def test_format_post_content_without_images(self, mock_images):
        """Test content formatting for posts without images."""
        # Mock that post has no images
        mock_images.return_value = []
        
        formatted_content = self.formatter.format_post_content(
            self.post,
            include_excerpt=True,
            optimize_for_images=True
        )
        
        # Content should be formatted normally
        self.assertIsNotNone(formatted_content)
        self.assertIn(self.post.title, formatted_content)
    
    @patch('blog.services.linkedin_content_formatter.LinkedInImageService.select_best_compatible_image')
    def test_select_best_image_for_linkedin(self, mock_select):
        """Test best image selection through content formatter."""
        # Mock successful image selection
        mock_select.return_value = 'https://example.com/best_image.jpg'
        
        best_image = self.formatter.select_best_image_for_linkedin(self.post)
        
        self.assertEqual(best_image, 'https://example.com/best_image.jpg')
        mock_select.assert_called_once_with(self.post)
    
    @patch('blog.services.linkedin_content_formatter.LinkedInImageService.validate_image_for_linkedin')
    def test_validate_image_compatibility(self, mock_validate):
        """Test image compatibility validation through content formatter."""
        # Mock successful validation
        mock_validate.return_value = (True, [])
        
        is_compatible = self.formatter.validate_image_compatibility('https://example.com/image.jpg')
        
        self.assertTrue(is_compatible)
        mock_validate.assert_called_once_with('https://example.com/image.jpg')
    
    @patch('blog.services.linkedin_content_formatter.LinkedInImageService.validate_image_for_linkedin')
    def test_validate_image_compatibility_invalid(self, mock_validate):
        """Test image compatibility validation for invalid image."""
        # Mock failed validation
        mock_validate.return_value = (False, ['Image too small'])
        
        is_compatible = self.formatter.validate_image_compatibility('https://example.com/image.jpg')
        
        self.assertFalse(is_compatible)
    
    @patch('blog.services.linkedin_content_formatter.LinkedInImageService.get_image_for_linkedin_post')
    def test_format_post_with_image_info(self, mock_image_info):
        """Test comprehensive post formatting with image information."""
        # Mock comprehensive image info
        mock_image_info.return_value = {
            'url': 'https://example.com/image.jpg',
            'linkedin_compatible': True,
            'compatibility_issues': [],
            'metadata': {'width': 1200, 'height': 627},
            'fallback_images_available': 2
        }
        
        result = self.formatter.format_post_with_image_info(self.post)
        
        self.assertTrue(result['has_image'])
        self.assertTrue(result['ready_for_posting'])
        self.assertEqual(result['posting_strategy'], 'image_post')
        self.assertIn('content', result)
        self.assertIn('image_info', result)
    
    @patch('blog.services.linkedin_content_formatter.LinkedInImageService.get_image_for_linkedin_post')
    def test_format_post_with_image_info_no_image(self, mock_image_info):
        """Test post formatting when no suitable image is found."""
        # Mock no image available
        mock_image_info.return_value = None
        
        result = self.formatter.format_post_with_image_info(self.post)
        
        self.assertFalse(result['has_image'])
        self.assertEqual(result['posting_strategy'], 'text_only_post')
        self.assertIsNone(result['image_info'])
    
    def test_content_validation_with_image_considerations(self):
        """Test content validation includes image-related checks."""
        test_content = f"{self.post.title}\n\nTest content\n\nhttps://example.com/post #test"
        
        is_valid, errors = self.formatter.validate_content(
            test_content,
            self.post,
            include_image_validation=True
        )
        
        # Should be valid even without images (text-only is acceptable)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
    
    def test_preview_formatting_with_image_analysis(self):
        """Test preview formatting includes comprehensive image analysis."""
        with patch('blog.services.linkedin_content_formatter.LinkedInImageService.get_fallback_images') as mock_images, \
             patch('blog.services.linkedin_content_formatter.LinkedInImageService.select_best_compatible_image') as mock_best, \
             patch.object(self.formatter, 'validate_image_compatibility') as mock_validate:
            
            # Mock image analysis data
            mock_images.return_value = ['https://example.com/img1.jpg', 'https://example.com/img2.jpg']
            mock_best.return_value = 'https://example.com/img1.jpg'
            mock_validate.side_effect = [True, False]  # First compatible, second not
            
            result = self.formatter.format_for_preview(
                self.post,
                include_image_analysis=True
            )
            
            self.assertIn('available_images', result)
            self.assertIn('best_linkedin_image', result)
            self.assertIn('image_analysis', result)
            self.assertEqual(result['total_images_count'], 2)
            self.assertEqual(result['compatible_images_count'], 1)
            self.assertEqual(result['image_compatibility_rate'], 50.0)