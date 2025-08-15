"""
Unit tests for LinkedInImageService.

Tests image selection, validation, metadata extraction, and fallback logic
for LinkedIn image integration.
"""

import os
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.models import User
from PIL import Image
from io import BytesIO

from blog.models import Post, MediaItem, Category, Tag
from blog.services.linkedin_image_service import LinkedInImageService
from blog.utils.image_processor import ImageProcessor


class LinkedInImageServiceTest(TestCase):
    """Test cases for LinkedInImageService functionality."""
    
    def setUp(self):
        """Set up test data."""
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create test category and tag
        self.category = Category.objects.create(name='Test Category')
        self.tag = Tag.objects.create(name='Test Tag')
        
        # Create test post
        self.post = Post.objects.create(
            title='Test Post',
            slug='test-post',
            author=self.user,
            content='Test content for the blog post.',
            excerpt='Test excerpt',
            status='published'
        )
        self.post.categories.add(self.category)
        self.post.tags.add(self.tag)
        
        # Create temporary directory for test images
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.temp_dir)
        
        # Create test images
        self.test_images = self._create_test_images()
    
    def _create_test_images(self):
        """Create test image files for testing."""
        images = {}
        
        # Create a valid LinkedIn-compatible image
        valid_img = Image.new('RGB', (1200, 627), color='red')
        valid_path = os.path.join(self.temp_dir, 'valid_image.jpg')
        valid_img.save(valid_path, 'JPEG', quality=85)
        images['valid'] = valid_path
        
        # Create an oversized image
        oversized_img = Image.new('RGB', (8000, 5000), color='blue')
        oversized_path = os.path.join(self.temp_dir, 'oversized_image.jpg')
        oversized_img.save(oversized_path, 'JPEG', quality=85)
        images['oversized'] = oversized_path
        
        # Create an undersized image
        undersized_img = Image.new('RGB', (100, 100), color='green')
        undersized_path = os.path.join(self.temp_dir, 'undersized_image.jpg')
        undersized_img.save(undersized_path, 'JPEG', quality=85)
        images['undersized'] = undersized_path
        
        # Create a PNG image with transparency
        png_img = Image.new('RGBA', (800, 600), color=(255, 0, 0, 128))
        png_path = os.path.join(self.temp_dir, 'transparent_image.png')
        png_img.save(png_path, 'PNG')
        images['png'] = png_path
        
        return images
    
    def _create_uploaded_file(self, image_path, field_name='image.jpg'):
        """Create a Django UploadedFile from an image path."""
        with open(image_path, 'rb') as f:
            return SimpleUploadedFile(
                field_name,
                f.read(),
                content_type='image/jpeg'
            )
    
    def test_get_base_url(self):
        """Test base URL generation."""
        service = LinkedInImageService()
        base_url = service._get_base_url()
        
        # Should return a valid URL format
        self.assertTrue(base_url.startswith('https://'))
        self.assertIn('localhost', base_url)  # Default in test environment
    
    def test_get_post_image_with_social_image(self):
        """Test image selection prioritizes social_image."""
        # Create social image file
        social_image_file = self._create_uploaded_file(self.test_images['valid'], 'social.jpg')
        self.post.social_image = social_image_file
        self.post.save()
        
        # Test image selection
        image_url = LinkedInImageService.get_post_image(self.post)
        
        self.assertIsNotNone(image_url)
        self.assertIn('social.jpg', image_url)
        self.assertTrue(image_url.startswith('https://'))
    
    def test_get_post_image_with_featured_image(self):
        """Test image selection falls back to featured_image."""
        # Create featured image file
        featured_image_file = self._create_uploaded_file(self.test_images['valid'], 'featured.jpg')
        self.post.featured_image = featured_image_file
        self.post.save()
        
        # Test image selection
        image_url = LinkedInImageService.get_post_image(self.post)
        
        self.assertIsNotNone(image_url)
        self.assertIn('featured.jpg', image_url)
        self.assertTrue(image_url.startswith('https://'))
    
    def test_get_post_image_with_media_items(self):
        """Test image selection falls back to media items."""
        # Create media item with image
        media_image_file = self._create_uploaded_file(self.test_images['valid'], 'media.jpg')
        media_item = MediaItem.objects.create(
            post=self.post,
            media_type='image',
            title='Test Media',
            original_image=media_image_file,
            is_featured=True
        )
        
        # Test image selection
        image_url = LinkedInImageService.get_post_image(self.post)
        
        self.assertIsNotNone(image_url)
        self.assertIn('media.jpg', image_url)
        self.assertTrue(image_url.startswith('https://'))
    
    def test_get_post_image_no_images(self):
        """Test image selection returns None when no images available."""
        image_url = LinkedInImageService.get_post_image(self.post)
        self.assertIsNone(image_url)
    
    def test_get_post_image_priority_order(self):
        """Test that image selection follows correct priority order."""
        # Add all types of images
        social_image_file = self._create_uploaded_file(self.test_images['valid'], 'social.jpg')
        featured_image_file = self._create_uploaded_file(self.test_images['oversized'], 'featured.jpg')
        
        self.post.social_image = social_image_file
        self.post.featured_image = featured_image_file
        self.post.save()
        
        # Create media item
        media_image_file = self._create_uploaded_file(self.test_images['png'], 'media.jpg')
        MediaItem.objects.create(
            post=self.post,
            media_type='image',
            title='Test Media',
            original_image=media_image_file
        )
        
        # Should select social_image (highest priority)
        image_url = LinkedInImageService.get_post_image(self.post)
        self.assertIn('social.jpg', image_url)
    
    @patch('blog.services.linkedin_image_service.ImageProcessor.download_and_process_image')
    @patch('blog.services.linkedin_image_service.ImageProcessor.is_linkedin_compatible')
    def test_validate_image_for_linkedin_valid(self, mock_compatible, mock_download):
        """Test image validation for valid LinkedIn image."""
        # Mock successful download and validation
        mock_download.return_value = self.test_images['valid']
        mock_compatible.return_value = (True, [])
        
        is_valid, issues = LinkedInImageService.validate_image_for_linkedin('https://example.com/image.jpg')
        
        self.assertTrue(is_valid)
        self.assertEqual(len(issues), 0)
        mock_download.assert_called_once()
        mock_compatible.assert_called_once()
    
    @patch('blog.services.linkedin_image_service.ImageProcessor.download_and_process_image')
    @patch('blog.services.linkedin_image_service.ImageProcessor.is_linkedin_compatible')
    def test_validate_image_for_linkedin_invalid(self, mock_compatible, mock_download):
        """Test image validation for invalid LinkedIn image."""
        # Mock successful download but failed validation
        mock_download.return_value = self.test_images['undersized']
        mock_compatible.return_value = (False, ['Image too small'])
        
        is_valid, issues = LinkedInImageService.validate_image_for_linkedin('https://example.com/image.jpg')
        
        self.assertFalse(is_valid)
        self.assertIn('Image too small', issues)
    
    def test_validate_image_for_linkedin_invalid_url(self):
        """Test image validation with invalid URL."""
        is_valid, issues = LinkedInImageService.validate_image_for_linkedin('invalid-url')
        
        self.assertFalse(is_valid)
        self.assertIn('Invalid image URL format', issues)
    
    @patch('blog.services.linkedin_image_service.ImageProcessor.download_and_process_image')
    @patch('blog.services.linkedin_image_service.ImageProcessor.get_image_metadata')
    def test_get_image_metadata(self, mock_metadata, mock_download):
        """Test image metadata extraction."""
        # Mock successful download and metadata extraction
        mock_download.return_value = self.test_images['valid']
        mock_metadata.return_value = {
            'width': 1200,
            'height': 627,
            'format': 'JPEG',
            'file_size': 50000,
            'aspect_ratio': 1.91
        }
        
        metadata = LinkedInImageService.get_image_metadata('https://example.com/image.jpg')
        
        self.assertTrue(metadata['accessible'])
        self.assertEqual(metadata['width'], 1200)
        self.assertEqual(metadata['height'], 627)
        self.assertEqual(metadata['format'], 'JPEG')
        self.assertIn('linkedin_analysis', metadata)
    
    def test_get_image_metadata_invalid_url(self):
        """Test metadata extraction with invalid URL."""
        metadata = LinkedInImageService.get_image_metadata('invalid-url')
        
        self.assertFalse(metadata['accessible'])
        self.assertIn('error', metadata)
        self.assertIn('Invalid image URL format', metadata['error'])
    
    def test_get_fallback_images(self):
        """Test fallback image collection."""
        # Add multiple images to post
        social_image_file = self._create_uploaded_file(self.test_images['valid'], 'social.jpg')
        featured_image_file = self._create_uploaded_file(self.test_images['oversized'], 'featured.jpg')
        
        self.post.social_image = social_image_file
        self.post.featured_image = featured_image_file
        self.post.save()
        
        # Create multiple media items
        for i in range(3):
            media_image_file = self._create_uploaded_file(self.test_images['png'], f'media_{i}.jpg')
            MediaItem.objects.create(
                post=self.post,
                media_type='image',
                title=f'Test Media {i}',
                original_image=media_image_file,
                order=i
            )
        
        fallback_images = LinkedInImageService.get_fallback_images(self.post)
        
        # Should have 5 images total (social, featured, 3 media items)
        self.assertEqual(len(fallback_images), 5)
        
        # Should be in priority order (social first)
        self.assertIn('social.jpg', fallback_images[0])
        self.assertIn('featured.jpg', fallback_images[1])
    
    def test_get_fallback_images_no_duplicates(self):
        """Test that fallback images removes duplicates."""
        # Use same image for both social and featured
        image_file = self._create_uploaded_file(self.test_images['valid'], 'same.jpg')
        
        self.post.social_image = image_file
        self.post.featured_image = image_file
        self.post.save()
        
        fallback_images = LinkedInImageService.get_fallback_images(self.post)
        
        # Should only have unique URLs
        self.assertEqual(len(set(fallback_images)), len(fallback_images))
    
    @patch('blog.services.linkedin_image_service.LinkedInImageService.validate_image_for_linkedin')
    def test_select_best_compatible_image(self, mock_validate):
        """Test selection of best compatible image."""
        # Add images to post
        social_image_file = self._create_uploaded_file(self.test_images['undersized'], 'social.jpg')
        featured_image_file = self._create_uploaded_file(self.test_images['valid'], 'featured.jpg')
        
        self.post.social_image = social_image_file
        self.post.featured_image = featured_image_file
        self.post.save()
        
        # Mock validation: social image invalid, featured image valid
        def mock_validation(url):
            if 'social.jpg' in url:
                return False, ['Too small']
            elif 'featured.jpg' in url:
                return True, []
            return False, ['Unknown error']
        
        mock_validate.side_effect = mock_validation
        
        best_image = LinkedInImageService.select_best_compatible_image(self.post)
        
        self.assertIsNotNone(best_image)
        self.assertIn('featured.jpg', best_image)
    
    @patch('blog.services.linkedin_image_service.LinkedInImageService.validate_image_for_linkedin')
    def test_select_best_compatible_image_none_compatible(self, mock_validate):
        """Test selection when no images are compatible."""
        # Add image to post
        social_image_file = self._create_uploaded_file(self.test_images['undersized'], 'social.jpg')
        self.post.social_image = social_image_file
        self.post.save()
        
        # Mock validation: all images invalid
        mock_validate.return_value = (False, ['Not compatible'])
        
        best_image = LinkedInImageService.select_best_compatible_image(self.post)
        
        self.assertIsNone(best_image)
    
    @patch('blog.services.linkedin_image_service.ImageProcessor.download_and_process_image')
    @patch('blog.services.linkedin_image_service.ImageProcessor.process_for_linkedin')
    def test_process_image_for_linkedin(self, mock_process, mock_download):
        """Test image processing for LinkedIn."""
        # Mock successful processing
        mock_download.return_value = self.test_images['oversized']
        mock_process.return_value = self.test_images['valid']
        
        processed_path = LinkedInImageService.process_image_for_linkedin('https://example.com/image.jpg')
        
        self.assertIsNotNone(processed_path)
        self.assertEqual(processed_path, self.test_images['valid'])
        mock_download.assert_called_once()
        mock_process.assert_called_once()
    
    def test_process_image_for_linkedin_invalid_url(self):
        """Test image processing with invalid URL."""
        processed_path = LinkedInImageService.process_image_for_linkedin('invalid-url')
        
        self.assertIsNone(processed_path)
    
    @patch('blog.services.linkedin_image_service.LinkedInImageService.select_best_compatible_image')
    @patch('blog.services.linkedin_image_service.LinkedInImageService.get_image_metadata')
    def test_get_image_for_linkedin_post(self, mock_metadata, mock_select):
        """Test comprehensive image information for LinkedIn post."""
        # Mock successful image selection and metadata
        test_url = 'https://example.com/image.jpg'
        mock_select.return_value = test_url
        mock_metadata.return_value = {
            'width': 1200,
            'height': 627,
            'linkedin_compatible': True,
            'compatibility_issues': []
        }
        
        result = LinkedInImageService.get_image_for_linkedin_post(self.post)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['url'], test_url)
        self.assertTrue(result['linkedin_compatible'])
        self.assertEqual(result['post_id'], self.post.id)
        self.assertEqual(result['post_title'], self.post.title)
        self.assertIn('metadata', result)
        self.assertIn('fallback_images_available', result)
    
    @patch('blog.services.linkedin_image_service.LinkedInImageService.select_best_compatible_image')
    def test_get_image_for_linkedin_post_no_image(self, mock_select):
        """Test LinkedIn post image when no suitable image found."""
        mock_select.return_value = None
        
        result = LinkedInImageService.get_image_for_linkedin_post(self.post)
        
        self.assertIsNone(result)
    
    @patch('blog.services.linkedin_image_service.LinkedInImageService.get_post_image')
    @patch('blog.services.linkedin_image_service.LinkedInImageService.get_image_metadata')
    def test_get_image_for_linkedin_post_no_validation(self, mock_metadata, mock_get_image):
        """Test LinkedIn post image without validation."""
        # Mock image selection without validation
        test_url = 'https://example.com/image.jpg'
        mock_get_image.return_value = test_url
        mock_metadata.return_value = {
            'width': 100,  # Too small
            'height': 100,
            'linkedin_compatible': False,
            'compatibility_issues': ['Too small']
        }
        
        result = LinkedInImageService.get_image_for_linkedin_post(self.post, validate=False)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['url'], test_url)
        self.assertFalse(result['linkedin_compatible'])  # Based on metadata
        mock_get_image.assert_called_once()  # Should use get_post_image, not select_best_compatible_image
    
    def test_service_initialization_with_custom_base_url(self):
        """Test service initialization with custom base URL."""
        custom_url = 'https://custom.example.com'
        service = LinkedInImageService(base_url=custom_url)
        
        self.assertEqual(service.base_url, custom_url)
    
    def test_service_initialization_default_base_url(self):
        """Test service initialization with default base URL."""
        service = LinkedInImageService()
        
        self.assertIsNotNone(service.base_url)
        self.assertTrue(service.base_url.startswith('https://'))


class LinkedInImageServiceIntegrationTest(TestCase):
    """Integration tests for LinkedInImageService with real image processing."""
    
    def setUp(self):
        """Set up test data for integration tests."""
        # Create test user and post
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.post = Post.objects.create(
            title='Integration Test Post',
            slug='integration-test-post',
            author=self.user,
            content='Test content for integration testing.',
            status='published'
        )
        
        # Create temporary directory
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.temp_dir)
        
        # Create a real test image
        self.test_image_path = self._create_real_test_image()
    
    def _create_real_test_image(self):
        """Create a real test image file."""
        # Create a LinkedIn-compatible image
        img = Image.new('RGB', (1200, 627), color=(255, 0, 0))
        image_path = os.path.join(self.temp_dir, 'test_image.jpg')
        img.save(image_path, 'JPEG', quality=85)
        return image_path
    
    def test_real_image_validation(self):
        """Test image validation with real image file."""
        # Create a file URL (simulating a downloaded image)
        file_url = f"file://{self.test_image_path}"
        
        # This would normally fail because we can't download file:// URLs
        # But we can test the validation logic with a real file
        is_compatible, issues = ImageProcessor.is_linkedin_compatible(self.test_image_path)
        
        self.assertTrue(is_compatible)
        self.assertEqual(len(issues), 0)
    
    def test_real_image_metadata_extraction(self):
        """Test metadata extraction with real image file."""
        metadata = ImageProcessor.get_image_metadata(self.test_image_path)
        
        self.assertEqual(metadata['width'], 1200)
        self.assertEqual(metadata['height'], 627)
        self.assertEqual(metadata['format'], 'JPEG')
        self.assertGreater(metadata['file_size'], 0)
        self.assertAlmostEqual(metadata['aspect_ratio'], 1.91, places=2)
    
    @override_settings(MEDIA_ROOT=None)
    def test_service_with_no_media_root(self):
        """Test service behavior when MEDIA_ROOT is not set."""
        # Should fall back to /tmp
        service = LinkedInImageService()
        
        # Test that methods don't crash
        result = service.get_post_image(self.post)
        self.assertIsNone(result)  # No images in post
    
    def tearDown(self):
        """Clean up after integration tests."""
        # Clean up any created files
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)