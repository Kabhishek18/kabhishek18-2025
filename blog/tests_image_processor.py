"""
Tests for the ImageProcessor utility class.
"""

import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from PIL import Image
from django.test import TestCase
from blog.utils.image_processor import ImageProcessor, ImageProcessingError


class ImageProcessorTestCase(TestCase):
    """Test cases for ImageProcessor utility."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        
        # Create test images
        self.valid_image_path = os.path.join(self.temp_dir, 'valid_test.jpg')
        self.create_test_image(self.valid_image_path, (1200, 627), 'JPEG')
        
        self.large_image_path = os.path.join(self.temp_dir, 'large_test.jpg')
        self.create_test_image(self.large_image_path, (8000, 6000), 'JPEG')
        
        self.small_image_path = os.path.join(self.temp_dir, 'small_test.jpg')
        self.create_test_image(self.small_image_path, (100, 100), 'JPEG')
        
        self.png_image_path = os.path.join(self.temp_dir, 'test.png')
        self.create_test_image(self.png_image_path, (800, 600), 'PNG')
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_test_image(self, path, size, format_type):
        """Create a test image file."""
        img = Image.new('RGB', size, color='red')
        img.save(path, format_type)
    
    def test_validate_image_dimensions_valid(self):
        """Test validation of valid image dimensions."""
        is_valid, info = ImageProcessor.validate_image_dimensions(self.valid_image_path)
        
        self.assertTrue(is_valid)
        self.assertEqual(info['width'], 1200)
        self.assertEqual(info['height'], 627)
        self.assertEqual(info['format'], 'JPEG')
        self.assertEqual(len(info['errors']), 0)
    
    def test_validate_image_dimensions_too_large(self):
        """Test validation of oversized image."""
        is_valid, info = ImageProcessor.validate_image_dimensions(self.large_image_path)
        
        self.assertTrue(is_valid)  # Should be valid but with warnings
        self.assertEqual(info['width'], 8000)
        self.assertEqual(info['height'], 6000)
        self.assertGreater(len(info['warnings']), 0)
        self.assertIn('exceed maximum', info['warnings'][0])
    
    def test_validate_image_dimensions_too_small(self):
        """Test validation of undersized image."""
        is_valid, info = ImageProcessor.validate_image_dimensions(self.small_image_path)
        
        self.assertFalse(is_valid)
        self.assertEqual(info['width'], 100)
        self.assertEqual(info['height'], 100)
        self.assertGreater(len(info['errors']), 0)
        self.assertIn('below minimum', info['errors'][0])
    
    def test_validate_image_file_size(self):
        """Test file size validation."""
        is_valid, file_size = ImageProcessor.validate_image_file_size(self.valid_image_path)
        
        self.assertTrue(is_valid)
        self.assertGreater(file_size, 0)
        self.assertLessEqual(file_size, ImageProcessor.MAX_FILE_SIZE)
    
    def test_resize_image_for_linkedin(self):
        """Test image resizing functionality."""
        output_path = os.path.join(self.temp_dir, 'resized_test.jpg')
        
        result_path = ImageProcessor.resize_image_for_linkedin(
            self.large_image_path, output_path
        )
        
        self.assertEqual(result_path, output_path)
        self.assertTrue(os.path.exists(output_path))
        
        # Check resized dimensions
        with Image.open(output_path) as img:
            self.assertLessEqual(img.size[0], ImageProcessor.RECOMMENDED_DIMENSIONS[0])
            self.assertLessEqual(img.size[1], ImageProcessor.RECOMMENDED_DIMENSIONS[1])
    
    def test_convert_image_format(self):
        """Test image format conversion."""
        output_path = os.path.join(self.temp_dir, 'converted_test.jpg')
        
        result_path = ImageProcessor.convert_image_format(
            self.png_image_path, 'JPEG', output_path
        )
        
        self.assertEqual(result_path, output_path)
        self.assertTrue(os.path.exists(output_path))
        
        # Check converted format
        with Image.open(output_path) as img:
            self.assertEqual(img.format, 'JPEG')
    
    def test_optimize_image_for_web(self):
        """Test image optimization."""
        output_path = os.path.join(self.temp_dir, 'optimized_test.jpg')
        
        result_path = ImageProcessor.optimize_image_for_web(
            self.valid_image_path, output_path, quality=80
        )
        
        self.assertEqual(result_path, output_path)
        self.assertTrue(os.path.exists(output_path))
        
        # Check that optimized file exists and has reasonable size
        original_size = os.path.getsize(self.valid_image_path)
        optimized_size = os.path.getsize(output_path)
        self.assertGreater(optimized_size, 0)
    
    def test_get_image_metadata(self):
        """Test image metadata extraction."""
        metadata = ImageProcessor.get_image_metadata(self.valid_image_path)
        
        self.assertEqual(metadata['width'], 1200)
        self.assertEqual(metadata['height'], 627)
        self.assertEqual(metadata['format'], 'JPEG')
        self.assertIn('aspect_ratio', metadata)
        self.assertIn('file_size', metadata)
    
    def test_is_linkedin_compatible(self):
        """Test LinkedIn compatibility check."""
        # Valid image should be compatible
        is_compatible, issues = ImageProcessor.is_linkedin_compatible(self.valid_image_path)
        self.assertTrue(is_compatible)
        self.assertEqual(len(issues), 0)
        
        # Small image should not be compatible
        is_compatible, issues = ImageProcessor.is_linkedin_compatible(self.small_image_path)
        self.assertFalse(is_compatible)
        self.assertGreater(len(issues), 0)
    
    def test_process_for_linkedin(self):
        """Test complete LinkedIn processing pipeline."""
        output_path = os.path.join(self.temp_dir, 'linkedin_processed.jpg')
        
        result_path = ImageProcessor.process_for_linkedin(
            self.large_image_path, output_path
        )
        
        self.assertEqual(result_path, output_path)
        self.assertTrue(os.path.exists(output_path))
        
        # Check that processed image is LinkedIn compatible
        is_compatible, issues = ImageProcessor.is_linkedin_compatible(output_path)
        self.assertTrue(is_compatible or len(issues) == 0)
    
    @patch('requests.get')
    def test_download_and_process_image(self, mock_get):
        """Test image download and processing."""
        # Mock successful HTTP response
        mock_response = MagicMock()
        mock_response.headers = {'content-type': 'image/jpeg'}
        mock_response.iter_content.return_value = [b'fake_image_data']
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Create a real image file to replace the fake data
        test_url = 'https://example.com/test.jpg'
        
        with patch('builtins.open', unittest.mock.mock_open()) as mock_file:
            # Mock the file writing, but we need to actually create a test image
            with patch.object(ImageProcessor, 'validate_image_file_size', return_value=(True, 1000)):
                with patch.object(ImageProcessor, 'validate_image_dimensions', 
                                return_value=(True, {'width': 800, 'height': 600, 'errors': [], 'warnings': []})):
                    with patch.object(ImageProcessor, 'optimize_image_for_web', 
                                    return_value='/fake/path/linkedin_test.jpg'):
                        result = ImageProcessor.download_and_process_image(test_url, self.temp_dir)
                        self.assertIsNotNone(result)
    
    def test_error_handling(self):
        """Test error handling for invalid inputs."""
        # Test with non-existent file
        with self.assertRaises(Exception):
            ImageProcessor.validate_image_dimensions('/non/existent/file.jpg')
        
        # Test with invalid format conversion
        with self.assertRaises(ImageProcessingError):
            ImageProcessor.convert_image_format(
                self.valid_image_path, 'INVALID_FORMAT', '/tmp/test.jpg'
            )


if __name__ == '__main__':
    unittest.main()