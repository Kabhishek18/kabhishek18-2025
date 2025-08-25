"""
Comprehensive tests for LinkedIn error handling and fallback mechanisms.

Tests the implementation of task 9: error handling and fallback mechanisms
for hashtag generation failures, image posting failures, configuration errors,
and graceful degradation scenarios.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta

from blog.services.linkedin_content_formatter import HashtagGenerator, LinkedInContentFormatter
from blog.services.linkedin_service import LinkedInAPIService, LinkedInAPIError, LinkedInContentError, LinkedInAuthenticationError, LinkedInRateLimitError
from blog.linkedin_models import LinkedInConfig


class HashtagGeneratorErrorHandlingTests(TestCase):
    """Test error handling in hashtag generation."""
    
    def setUp(self):
        self.mock_post = Mock()
        self.mock_post.id = 1
        self.mock_post.title = "Test Blog Post"
        self.mock_post.excerpt = "This is a test excerpt"
        self.mock_post.content = "This is test content"
        
        # Mock tags
        self.mock_tags = Mock()
        self.mock_tags.exists.return_value = True
        self.mock_tags.values_list.return_value = ['python', 'django', 'testing']
        self.mock_post.tags = self.mock_tags
        
        # Mock categories
        self.mock_categories = Mock()
        self.mock_categories.exists.return_value = True
        self.mock_categories.values_list.return_value = ['technology', 'programming']
        self.mock_post.categories = self.mock_categories
    
    def test_hashtag_generator_with_invalid_config(self):
        """Test HashtagGenerator handles invalid configuration gracefully."""
        # Test with None config
        generator = HashtagGenerator(None)
        self.assertIsInstance(generator.config, dict)
        self.assertTrue(generator.config['enable_hashtags'])
        
        # Test with invalid config type
        generator = HashtagGenerator("invalid_config")
        self.assertIsInstance(generator.config, dict)
        self.assertTrue(generator.config['enable_hashtags'])
        
        # Test with malformed config dict
        invalid_config = {
            'enable_hashtags': 'not_a_boolean',
            'max_hashtags': 'not_a_number',
            'custom_hashtag_rules': 'not_a_dict',
            'hashtag_blacklist': 'not_a_list'
        }
        generator = HashtagGenerator(invalid_config)
        self.assertTrue(generator.config['enable_hashtags'])
        self.assertEqual(generator.config['max_hashtags'], 5)
        self.assertEqual(generator.config['custom_hashtag_rules'], {})
        self.assertEqual(generator.config['hashtag_blacklist'], [])
    
    def test_hashtag_generation_with_missing_attributes(self):
        """Test hashtag generation when blog post is missing attributes."""
        generator = HashtagGenerator()
        
        # Test with post missing tags attribute
        post_no_tags = Mock()
        post_no_tags.id = 1
        post_no_tags.title = "Test Post"
        # No tags attribute
        
        hashtags = generator.generate_from_tags(post_no_tags, 5)
        self.assertEqual(hashtags, [])
        
        # Test with post missing categories attribute
        hashtags = generator.generate_from_categories(post_no_tags, 5)
        self.assertEqual(hashtags, [])
    
    def test_hashtag_generation_with_database_errors(self):
        """Test hashtag generation when database queries fail."""
        generator = HashtagGenerator()
        
        # Mock tags.exists() to raise exception
        self.mock_post.tags.exists.side_effect = Exception("Database error")
        
        hashtags = generator.generate_from_tags(self.mock_post, 5)
        self.assertEqual(hashtags, [])
        
        # Reset and test categories
        self.mock_post.tags.exists.side_effect = None
        self.mock_post.categories.exists.side_effect = Exception("Database error")
        
        hashtags = generator.generate_from_categories(self.mock_post, 5)
        self.assertEqual(hashtags, [])
    
    def test_hashtag_generation_with_invalid_tag_data(self):
        """Test hashtag generation with invalid tag data."""
        generator = HashtagGenerator()
        
        # Test with None values in tag list
        self.mock_post.tags.values_list.return_value = ['python', None, '', 'django']
        
        hashtags = generator.generate_from_tags(self.mock_post, 5)
        # Should filter out None and empty values
        self.assertTrue(len(hashtags) >= 2)
        self.assertIn('#python', hashtags)
        self.assertIn('#django', hashtags)
    
    def test_hashtag_generation_fallback_mechanisms(self):
        """Test fallback mechanisms when primary generation fails."""
        generator = HashtagGenerator()
        
        # Test fallback hashtag generation
        fallback_hashtags = generator._generate_fallback_hashtags(self.mock_post, 3)
        self.assertIsInstance(fallback_hashtags, list)
        self.assertTrue(len(fallback_hashtags) > 0)
        
        # Test with post having no title
        post_no_title = Mock()
        post_no_title.id = 1
        # No title attribute
        
        fallback_hashtags = generator._generate_fallback_hashtags(post_no_title, 3)
        self.assertIsInstance(fallback_hashtags, list)
        # Should still return some generic hashtags
        self.assertTrue(len(fallback_hashtags) > 0)
    
    def test_blacklist_filtering_with_errors(self):
        """Test blacklist filtering handles errors gracefully."""
        generator = HashtagGenerator({
            'hashtag_blacklist': ['spam', 'bad', None, 123]  # Mixed types
        })
        
        hashtags = ['#good', '#spam', '#test', '#bad', '#python']
        filtered = generator.filter_blacklisted_hashtags(hashtags)
        
        # Should filter out blacklisted terms and handle invalid blacklist entries
        self.assertNotIn('#spam', filtered)
        self.assertNotIn('#bad', filtered)
        self.assertIn('#good', filtered)
        self.assertIn('#test', filtered)
        self.assertIn('#python', filtered)
    
    def test_hashtag_validation_edge_cases(self):
        """Test hashtag validation with edge cases."""
        generator = HashtagGenerator()
        
        # Test with None input
        self.assertFalse(generator.validate_hashtag(None))
        
        # Test with empty string
        self.assertFalse(generator.validate_hashtag(""))
        
        # Test with non-string input
        self.assertFalse(generator.validate_hashtag(123))
        
        # Test with very long hashtag
        long_hashtag = "#" + "a" * 200
        self.assertFalse(generator.validate_hashtag(long_hashtag))
        
        # Test with hashtag containing only numbers
        self.assertFalse(generator.validate_hashtag("#123"))
        
        # Test with hashtag starting with number
        self.assertFalse(generator.validate_hashtag("#1test"))


class LinkedInContentFormatterErrorHandlingTests(TestCase):
    """Test error handling in LinkedIn content formatting."""
    
    def setUp(self):
        self.formatter = LinkedInContentFormatter()
        self.mock_post = Mock()
        self.mock_post.id = 1
        self.mock_post.title = "Test Blog Post"
        self.mock_post.excerpt = "This is a test excerpt"
        self.mock_post.content = "This is test content"
        self.mock_post.get_absolute_url.return_value = "/blog/test-post/"
    
    def test_format_post_with_none_inputs(self):
        """Test formatting handles None inputs gracefully."""
        # Test with None blog_post
        result = self.formatter.format_post_with_config(None, None)
        self.assertEqual(result, "")
        
        # Test with None config (should use fallback)
        result = self.formatter.format_post_with_config(self.mock_post, None)
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)
    
    def test_hashtag_generation_error_handling(self):
        """Test hashtag generation error handling in formatter."""
        # Mock HashtagGenerator to raise exception
        with patch('blog.services.linkedin_content_formatter.HashtagGenerator') as mock_generator_class:
            mock_generator = Mock()
            mock_generator.generate_hashtags.side_effect = Exception("Hashtag generation failed")
            mock_generator_class.return_value = mock_generator
            
            result = self.formatter._generate_hashtags(self.mock_post)
            # Should return empty string when hashtag generation fails
            self.assertEqual(result, "")
    
    def test_emergency_fallback_content_creation(self):
        """Test emergency fallback content creation."""
        # Test with normal post
        result = self.formatter._create_emergency_fallback_content(self.mock_post)
        self.assertIn("Test Blog Post", result)
        
        # Test with post missing title
        post_no_title = Mock()
        post_no_title.id = 1
        # No title attribute
        
        result = self.formatter._create_emergency_fallback_content(post_no_title)
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)
    
    def test_image_posting_decision_error_handling(self):
        """Test image posting decision handles errors gracefully."""
        mock_config = Mock()
        mock_config.enable_image_posting = True
        mock_config.image_posting_strategy = 'category_based'
        
        # Mock should_include_images to raise exception
        mock_config.should_include_images.side_effect = Exception("Config error")
        
        # Should fallback to text-only when image decision fails
        result = self.formatter._should_include_images_for_post(self.mock_post, mock_config, True)
        self.assertFalse(result)  # Should fallback to False
    
    def test_basic_fallback_hashtag_generation(self):
        """Test basic fallback hashtag generation."""
        # Test with normal post
        result = self.formatter._generate_basic_fallback_hashtags(self.mock_post)
        self.assertIsInstance(result, list)
        self.assertTrue(len(result) > 0)
        
        # Test with post having very short title
        short_title_post = Mock()
        short_title_post.title = "Hi"
        
        result = self.formatter._generate_basic_fallback_hashtags(short_title_post)
        self.assertIsInstance(result, list)
        # Should include generic hashtags
        self.assertIn('#blog', result)


class LinkedInServiceErrorHandlingTests(TestCase):
    """Test error handling in LinkedIn API service."""
    
    def setUp(self):
        self.mock_config = Mock()
        self.mock_config.is_active = True
        self.mock_config.client_id = "test_client_id"
        self.mock_config.get_client_secret.return_value = "test_secret"
        self.mock_config.get_access_token.return_value = "test_token"
        self.mock_config.is_token_expired.return_value = False
        
        self.service = LinkedInAPIService(self.mock_config)
    
    def test_create_post_with_image_failure_fallback(self):
        """Test create_post falls back to text-only when image upload fails."""
        with patch.object(self.service, 'upload_media') as mock_upload:
            with patch.object(self.service, '_create_text_only_post') as mock_text_post:
                # Mock image upload to fail
                mock_upload.side_effect = LinkedInAPIError("Image upload failed")
                
                # Mock text-only post to succeed
                mock_text_post.return_value = {'id': 'test_post_id', 'status': 'success'}
                
                result = self.service.create_post(
                    title="Test Post",
                    content="Test content",
                    url="https://example.com",
                    image_url="https://example.com/image.jpg"
                )
                
                # Should have fallen back to text-only
                self.assertTrue(result['_media_info']['fallback_used'])
                self.assertFalse(result['_media_info']['has_media'])
                mock_text_post.assert_called_once()
    
    def test_create_post_with_all_failures(self):
        """Test create_post when both image and text-only posting fail."""
        with patch.object(self.service, 'upload_media') as mock_upload:
            with patch.object(self.service, '_create_text_only_post') as mock_text_post:
                with patch.object(self.service, '_create_simplified_fallback_post') as mock_simplified:
                    # Mock all methods to fail
                    mock_upload.side_effect = LinkedInAPIError("Image upload failed")
                    mock_text_post.side_effect = LinkedInAPIError("Text post failed")
                    mock_simplified.side_effect = LinkedInAPIError("Simplified post failed")
                    
                    with self.assertRaises(LinkedInAPIError):
                        self.service.create_post(
                            title="Test Post",
                            content="Test content",
                            url="https://example.com",
                            image_url="https://example.com/image.jpg"
                        )
    
    def test_simplified_fallback_post_creation(self):
        """Test simplified fallback post creation."""
        with patch.object(self.service, '_create_text_only_post') as mock_text_post:
            mock_text_post.return_value = {'id': 'fallback_post_id'}
            
            result = self.service._create_simplified_fallback_post(
                "Very Long Title That Should Be Truncated Because It Exceeds The Limit",
                "https://example.com"
            )
            
            self.assertEqual(result['id'], 'fallback_post_id')
            # Should have called _create_text_only_post with truncated title
            mock_text_post.assert_called_once()
            args = mock_text_post.call_args[0]
            self.assertTrue(len(args[0]) <= 103)  # 100 + "..."
    
    def test_text_only_post_error_handling(self):
        """Test error handling in text-only post creation."""
        with patch.object(self.service, 'get_user_profile') as mock_profile:
            with patch.object(self.service, '_make_authenticated_request') as mock_request:
                # Test profile retrieval failure
                mock_profile.side_effect = LinkedInAPIError("Profile fetch failed")
                
                with self.assertRaises(LinkedInAPIError):
                    self.service._create_text_only_post("Test", "Content", "https://example.com")
                
                # Test API request failure
                mock_profile.side_effect = None
                mock_profile.return_value = {'id': 'test_user_id'}
                
                mock_response = Mock()
                mock_response.status_code = 400
                mock_response.json.return_value = {'message': 'Bad request'}
                mock_response.headers = {'content-type': 'application/json'}
                mock_request.return_value = mock_response
                
                with self.assertRaises(LinkedInContentError):
                    self.service._create_text_only_post("Test", "Content", "https://example.com")
    
    def test_authentication_error_handling(self):
        """Test authentication error handling and token clearing."""
        with patch.object(self.service, '_make_authenticated_request') as mock_request:
            # Mock authentication error response
            mock_response = Mock()
            mock_response.status_code = 401
            mock_response.json.return_value = {
                'error': 'invalid_token',
                'error_description': 'Token has expired'
            }
            mock_response.headers = {'content-type': 'application/json'}
            
            self.service._handle_authentication_error(mock_response, "test operation")
            
            # Should have cleared tokens
            self.mock_config.clear_tokens.assert_called_once()
    
    def test_rate_limit_error_handling(self):
        """Test rate limit error handling."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {'Retry-After': '3600', 'content-type': 'application/json'}
        mock_response.json.return_value = {'message': 'Rate limit exceeded'}
        
        with self.assertRaises(LinkedInRateLimitError) as context:
            self.service._handle_rate_limit_error(mock_response)
        
        self.assertEqual(context.exception.retry_after, 3600)
        self.assertEqual(context.exception.quota_type, 'hourly')


class LinkedInConfigErrorHandlingTests(TestCase):
    """Test error handling in LinkedIn configuration."""
    
    def test_should_include_images_with_invalid_strategy(self):
        """Test image inclusion decision with invalid strategy."""
        config = LinkedInConfig(
            client_id="test",
            enable_image_posting=True,
            image_posting_strategy="invalid_strategy"
        )
        
        # Should default to True for unknown strategy
        result = config.should_include_images()
        self.assertTrue(result)
    
    def test_should_include_images_with_database_errors(self):
        """Test image inclusion decision when database queries fail."""
        config = LinkedInConfig(
            client_id="test",
            enable_image_posting=True,
            image_posting_strategy="category_based"
        )
        
        mock_post = Mock()
        mock_post.categories.exists.side_effect = Exception("Database error")
        
        # Should default to True when database queries fail
        result = config.should_include_images(mock_post)
        self.assertTrue(result)
    
    def test_category_based_image_decision_error_handling(self):
        """Test category-based image decision error handling."""
        config = LinkedInConfig(
            client_id="test",
            enable_image_posting=True,
            image_posting_strategy="category_based",
            category_image_overrides={'tech': False}
        )
        
        # Test with post missing categories attribute
        post_no_categories = Mock()
        # No categories attribute
        
        result = config.should_include_images(post_no_categories)
        self.assertTrue(result)  # Should default to True
    
    def test_config_validation_with_invalid_data(self):
        """Test configuration validation with invalid data."""
        config = LinkedInConfig(
            client_id="test",
            max_hashtags=-5,  # Invalid
            custom_hashtag_rules="not_a_dict",  # Invalid
            hashtag_blacklist="not_a_list"  # Invalid
        )
        
        # Should raise validation errors
        with self.assertRaises(Exception):
            config.full_clean()


class IntegrationErrorHandlingTests(TestCase):
    """Integration tests for error handling across components."""
    
    def test_end_to_end_error_handling_flow(self):
        """Test complete error handling flow from formatting to posting."""
        # Create mock objects
        mock_post = Mock()
        mock_post.id = 1
        mock_post.title = "Test Post"
        mock_post.excerpt = "Test excerpt"
        mock_post.get_absolute_url.return_value = "/test/"
        
        mock_config = Mock()
        mock_config.enable_hashtags = True
        mock_config.enable_image_posting = True
        mock_config.image_posting_strategy = 'always'
        mock_config.get_hashtag_config.return_value = {
            'enable_hashtags': True,
            'max_hashtags': 5,
            'custom_hashtag_rules': {},
            'hashtag_blacklist': []
        }
        
        # Test with various failure scenarios
        formatter = LinkedInContentFormatter()
        
        # Test hashtag generation failure
        with patch('blog.services.linkedin_content_formatter.HashtagGenerator') as mock_gen:
            mock_gen.side_effect = Exception("Hashtag generation failed")
            
            result = formatter.format_post_with_config(mock_post, mock_config)
            # Should still produce formatted content without hashtags
            self.assertIsInstance(result, str)
            self.assertTrue(len(result) > 0)
    
    def test_graceful_degradation_scenarios(self):
        """Test graceful degradation in various failure scenarios."""
        formatter = LinkedInContentFormatter()
        
        # Test with completely broken post object
        broken_post = Mock()
        broken_post.id = None
        broken_post.title = None
        broken_post.excerpt = None
        broken_post.content = None
        broken_post.get_absolute_url.side_effect = Exception("URL generation failed")
        
        result = formatter.format_post_with_config(broken_post, None)
        # Should still return some content
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)


if __name__ == '__main__':
    unittest.main()