"""
Unit tests for LinkedIn image posting configuration functionality.

Tests the LinkedInConfig image posting methods, decision logic with different strategies,
configuration-aware content formatting, and fallback behavior when image posting is disabled.

Requirements: 2.1, 2.2, 2.3
"""

from django.test import TestCase
from django.core.exceptions import ValidationError
from unittest.mock import Mock, patch, MagicMock
from blog.linkedin_models import LinkedInConfig
from blog.models import Post, Category, Tag
from blog.services.linkedin_content_formatter import LinkedInContentFormatter


class LinkedInConfigImagePostingTests(TestCase):
    """Test LinkedInConfig image posting methods and configuration."""
    
    def setUp(self):
        """Set up test data."""
        self.config = LinkedInConfig(
            client_id="test_client_id",
            is_active=True,
            enable_image_posting=True,
            image_posting_strategy='always'
        )
        # Set required client_secret to pass validation
        self.config.set_client_secret("test_client_secret")
        self.config.save()
        
        # Create test user for blog post author
        from django.contrib.auth.models import User
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create test blog post
        self.blog_post = Post.objects.create(
            title="Test Blog Post",
            content="This is test content for the blog post.",
            excerpt="Test excerpt",
            status='published',
            author=self.user
        )
        
        # Create test categories
        self.tech_category = Category.objects.create(
            name="Technology",
            slug="technology"
        )
        self.news_category = Category.objects.create(
            name="News",
            slug="news"
        )
    
    def test_get_image_posting_config_default(self):
        """Test get_image_posting_config returns correct default configuration."""
        config = self.config.get_image_posting_config()
        
        expected_config = {
            'enable_image_posting': True,
            'image_posting_strategy': 'always'
        }
        
        self.assertEqual(config, expected_config)
    
    def test_get_image_posting_config_disabled(self):
        """Test get_image_posting_config when image posting is disabled."""
        self.config.enable_image_posting = False
        self.config.image_posting_strategy = 'never'
        self.config.save()
        
        config = self.config.get_image_posting_config()
        
        expected_config = {
            'enable_image_posting': False,
            'image_posting_strategy': 'never'
        }
        
        self.assertEqual(config, expected_config)
    
    def test_should_include_images_always_strategy(self):
        """Test should_include_images with 'always' strategy."""
        self.config.image_posting_strategy = 'always'
        self.config.enable_image_posting = True
        self.config.save()
        
        result = self.config.should_include_images(self.blog_post)
        self.assertTrue(result)
    
    def test_should_include_images_never_strategy(self):
        """Test should_include_images with 'never' strategy."""
        self.config.image_posting_strategy = 'never'
        self.config.enable_image_posting = True  # Should be overridden by strategy
        self.config.save()
        
        result = self.config.should_include_images(self.blog_post)
        self.assertFalse(result)
    
    def test_should_include_images_disabled_globally(self):
        """Test should_include_images when globally disabled."""
        self.config.enable_image_posting = False
        self.config.image_posting_strategy = 'always'  # Should be overridden
        self.config.save()
        
        result = self.config.should_include_images(self.blog_post)
        self.assertFalse(result)
    
    def test_should_include_images_category_based_strategy(self):
        """Test should_include_images with 'category_based' strategy."""
        self.config.image_posting_strategy = 'category_based'
        self.config.enable_image_posting = True
        self.config.save()
        
        # Add category to blog post
        self.blog_post.categories.add(self.tech_category)
        
        result = self.config.should_include_images(self.blog_post)
        self.assertTrue(result)  # Default behavior for category-based
    
    def test_should_include_images_category_based_no_categories(self):
        """Test should_include_images with 'category_based' strategy and no categories."""
        self.config.image_posting_strategy = 'category_based'
        self.config.enable_image_posting = True
        self.config.save()
        
        # Blog post has no categories
        result = self.config.should_include_images(self.blog_post)
        self.assertTrue(result)  # Default behavior when no categories
    
    def test_should_include_images_without_blog_post(self):
        """Test should_include_images without providing blog_post parameter."""
        self.config.image_posting_strategy = 'always'
        self.config.enable_image_posting = True
        self.config.save()
        
        result = self.config.should_include_images()
        self.assertTrue(result)
        
        # Test with 'never' strategy
        self.config.image_posting_strategy = 'never'
        self.config.save()
        
        result = self.config.should_include_images()
        self.assertFalse(result)
    
    def test_image_posting_strategy_validation(self):
        """Test validation of image_posting_strategy field."""
        # Valid strategies should pass
        valid_strategies = ['always', 'never', 'category_based']
        
        for strategy in valid_strategies:
            self.config.image_posting_strategy = strategy
            try:
                self.config.full_clean()
            except ValidationError:
                self.fail(f"Valid strategy '{strategy}' should not raise ValidationError")
        
        # Invalid strategy should fail
        self.config.image_posting_strategy = 'invalid_strategy'
        with self.assertRaises(ValidationError) as context:
            self.config.full_clean()
        
        self.assertIn('Image posting strategy must be one of', str(context.exception))


class LinkedInImagePostingDecisionLogicTests(TestCase):
    """Test image posting decision logic with different strategies."""
    
    def setUp(self):
        """Set up test data."""
        from django.contrib.auth.models import User
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create test categories
        self.tech_category = Category.objects.create(
            name="Technology",
            slug="technology"
        )
        self.news_category = Category.objects.create(
            name="News",
            slug="news"
        )
        
        # Create test blog post
        self.blog_post = Post.objects.create(
            title="Test Blog Post",
            content="This is test content for the blog post.",
            excerpt="Test excerpt",
            status='published',
            author=self.user
        )
    
    def test_image_posting_decision_always_strategy(self):
        """Test image posting decision logic with 'always' strategy."""
        config = LinkedInConfig(
            client_id="test_client_id",
            enable_image_posting=True,
            image_posting_strategy='always'
        )
        config.set_client_secret("test_secret")
        config.save()
        
        result = config.should_include_images(self.blog_post)
        self.assertTrue(result)
    
    def test_image_posting_decision_never_strategy(self):
        """Test image posting decision logic with 'never' strategy."""
        config = LinkedInConfig(
            client_id="test_client_id",
            enable_image_posting=True,
            image_posting_strategy='never'
        )
        config.set_client_secret("test_secret")
        config.save()
        
        result = config.should_include_images(self.blog_post)
        self.assertFalse(result)
    
    def test_image_posting_decision_globally_disabled(self):
        """Test image posting decision logic when globally disabled."""
        config = LinkedInConfig(
            client_id="test_client_id",
            enable_image_posting=False,
            image_posting_strategy='always'  # Should be overridden
        )
        config.set_client_secret("test_secret")
        config.save()
        
        result = config.should_include_images(self.blog_post)
        self.assertFalse(result)
    
    def test_image_posting_decision_category_based_strategy(self):
        """Test image posting decision logic with 'category_based' strategy."""
        config = LinkedInConfig(
            client_id="test_client_id",
            enable_image_posting=True,
            image_posting_strategy='category_based'
        )
        config.set_client_secret("test_secret")
        config.save()
        
        # Add category to blog post
        self.blog_post.categories.add(self.tech_category)
        
        result = config.should_include_images(self.blog_post)
        self.assertTrue(result)  # Default behavior for category-based
    
    def test_image_posting_decision_category_based_no_categories(self):
        """Test image posting decision logic with 'category_based' strategy and no categories."""
        config = LinkedInConfig(
            client_id="test_client_id",
            enable_image_posting=True,
            image_posting_strategy='category_based'
        )
        config.set_client_secret("test_secret")
        config.save()
        
        # Blog post has no categories
        result = config.should_include_images(self.blog_post)
        self.assertTrue(result)  # Default behavior when no categories
    
    def test_image_posting_decision_without_blog_post(self):
        """Test image posting decision logic without providing blog_post parameter."""
        config = LinkedInConfig(
            client_id="test_client_id",
            enable_image_posting=True,
            image_posting_strategy='always'
        )
        config.set_client_secret("test_secret")
        config.save()
        
        result = config.should_include_images()
        self.assertTrue(result)
        
        # Test with 'never' strategy
        config.image_posting_strategy = 'never'
        config.save()
        
        result = config.should_include_images()
        self.assertFalse(result)


class LinkedInImagePostingFallbackTests(TestCase):
    """Test fallback behavior when image posting is disabled or fails."""
    
    def setUp(self):
        """Set up test data."""
        from django.contrib.auth.models import User
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.blog_post = Post.objects.create(
            title="Test Blog Post",
            content="This is test content for the blog post.",
            excerpt="Test excerpt",
            status='published',
            author=self.user
        )
    
    def test_fallback_behavior_when_images_disabled(self):
        """Test fallback behavior when image posting is disabled."""
        config = LinkedInConfig(
            client_id="test_client_id",
            enable_image_posting=False,
            image_posting_strategy='always'
        )
        config.set_client_secret("test_secret")
        config.save()
        
        # The configuration should indicate that images should not be included
        result = config.should_include_images(self.blog_post)
        self.assertFalse(result)
    
    def test_fallback_behavior_with_invalid_strategy(self):
        """Test fallback behavior when configuration has invalid strategy."""
        config = LinkedInConfig(
            client_id="test_client_id",
            enable_image_posting=True,
            image_posting_strategy='always'  # Valid strategy initially
        )
        config.set_client_secret("test_secret")
        config.save()
        
        # Manually set invalid strategy to test fallback
        config.image_posting_strategy = 'invalid_strategy'
        
        # The method should handle invalid strategy gracefully
        result = config.should_include_images(self.blog_post)
        # Should default to enabled when strategy is unknown
        self.assertTrue(result)
    
    def test_graceful_degradation_with_missing_categories(self):
        """Test graceful degradation when blog post has no categories attribute."""
        config = LinkedInConfig(
            client_id="test_client_id",
            enable_image_posting=True,
            image_posting_strategy='category_based'
        )
        config.set_client_secret("test_secret")
        config.save()
        
        # Create a mock object without categories attribute
        mock_post = Mock()
        mock_post.categories = Mock()
        mock_post.categories.exists.return_value = False
        
        result = config.should_include_images(mock_post)
        self.assertTrue(result)  # Should default to enabled
    
    def test_configuration_aware_content_formatting_fallback(self):
        """Test that configuration-aware formatting falls back gracefully."""
        config = LinkedInConfig(
            client_id="test_client_id",
            enable_image_posting=False,
            image_posting_strategy='never'
        )
        config.set_client_secret("test_secret")
        config.save()
        
        # Test that the configuration correctly indicates no images should be used
        image_config = config.get_image_posting_config()
        self.assertFalse(image_config['enable_image_posting'])
        self.assertEqual(image_config['image_posting_strategy'], 'never')
        
        # Test that should_include_images respects the configuration
        result = config.should_include_images(self.blog_post)
        self.assertFalse(result)


class LinkedInConfigurationAwareContentFormattingTests(TestCase):
    """Test configuration-aware content formatting functionality."""
    
    def setUp(self):
        """Set up test data."""
        from django.contrib.auth.models import User
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create test categories
        self.tech_category = Category.objects.create(
            name="Technology",
            slug="technology"
        )
        self.news_category = Category.objects.create(
            name="News",
            slug="news"
        )
        
        # Create test tags
        self.python_tag = Tag.objects.create(name="Python", slug="python")
        self.django_tag = Tag.objects.create(name="Django", slug="django")
        
        # Create test blog post
        self.blog_post = Post.objects.create(
            title="Test Blog Post About Django Development",
            content="<p>This is a comprehensive test blog post about Django development. It covers various aspects of web development using Django framework.</p>",
            excerpt="This is a test excerpt about Django development.",
            status='published',
            author=self.user
        )
        self.blog_post.categories.add(self.tech_category)
        self.blog_post.tags.add(self.python_tag, self.django_tag)
        
        # Create LinkedIn configuration
        self.config = LinkedInConfig(
            client_id="test_client_id",
            is_active=True,
            enable_hashtags=True,
            max_hashtags=5,
            enable_image_posting=True,
            image_posting_strategy='always'
        )
        self.config.set_client_secret("test_client_secret")
        self.config.save()
    
    @patch('blog.services.linkedin_content_formatter.LinkedInContentFormatter.get_post_images')
    def test_format_post_with_config_images_enabled(self, mock_get_images):
        """Test format_post_with_config with images enabled."""
        from blog.services.linkedin_content_formatter import LinkedInContentFormatter
        
        # Mock available images
        mock_get_images.return_value = ['https://example.com/image1.jpg']
        
        formatter = LinkedInContentFormatter()
        formatted_content = formatter.format_post_with_config(
            self.blog_post, 
            self.config, 
            include_excerpt=True, 
            optimize_for_images=True
        )
        
        # Verify content is formatted correctly
        self.assertIsInstance(formatted_content, str)
        self.assertIn(self.blog_post.title, formatted_content)
        self.assertIn(self.blog_post.excerpt, formatted_content)
        self.assertGreater(len(formatted_content), 0)
        
        # Verify character limit is respected
        self.assertLessEqual(len(formatted_content), LinkedInContentFormatter.MAX_POST_LENGTH)
    
    @patch('blog.services.linkedin_content_formatter.LinkedInContentFormatter.get_post_images')
    def test_format_post_with_config_images_disabled(self, mock_get_images):
        """Test format_post_with_config with images disabled."""
        from blog.services.linkedin_content_formatter import LinkedInContentFormatter
        
        # Configure to disable images
        self.config.enable_image_posting = False
        self.config.save()
        
        # Mock available images (should be ignored)
        mock_get_images.return_value = ['https://example.com/image1.jpg']
        
        formatter = LinkedInContentFormatter()
        formatted_content = formatter.format_post_with_config(
            self.blog_post, 
            self.config, 
            include_excerpt=True, 
            optimize_for_images=True
        )
        
        # Verify content is formatted correctly without image optimization
        self.assertIsInstance(formatted_content, str)
        self.assertIn(self.blog_post.title, formatted_content)
        self.assertIn(self.blog_post.excerpt, formatted_content)
        
        # get_post_images should not be called when images are disabled
        mock_get_images.assert_not_called()
    
    @patch('blog.services.linkedin_content_formatter.LinkedInContentFormatter.get_post_images')
    def test_format_post_with_config_never_strategy(self, mock_get_images):
        """Test format_post_with_config with 'never' image strategy."""
        from blog.services.linkedin_content_formatter import LinkedInContentFormatter
        
        # Configure 'never' strategy
        self.config.image_posting_strategy = 'never'
        self.config.save()
        
        # Mock available images (should be ignored)
        mock_get_images.return_value = ['https://example.com/image1.jpg']
        
        formatter = LinkedInContentFormatter()
        formatted_content = formatter.format_post_with_config(
            self.blog_post, 
            self.config, 
            include_excerpt=True, 
            optimize_for_images=True
        )
        
        # Verify content is formatted correctly
        self.assertIsInstance(formatted_content, str)
        self.assertIn(self.blog_post.title, formatted_content)
        
        # get_post_images should not be called with 'never' strategy
        mock_get_images.assert_not_called()
    
    @patch('blog.services.linkedin_content_formatter.LinkedInContentFormatter.get_post_images')
    def test_format_post_with_config_category_based_strategy(self, mock_get_images):
        """Test format_post_with_config with 'category_based' image strategy."""
        from blog.services.linkedin_content_formatter import LinkedInContentFormatter
        
        # Configure 'category_based' strategy
        self.config.image_posting_strategy = 'category_based'
        self.config.save()
        
        # Mock available images
        mock_get_images.return_value = ['https://example.com/image1.jpg']
        
        formatter = LinkedInContentFormatter()
        formatted_content = formatter.format_post_with_config(
            self.blog_post, 
            self.config, 
            include_excerpt=True, 
            optimize_for_images=True
        )
        
        # Verify content is formatted correctly
        self.assertIsInstance(formatted_content, str)
        self.assertIn(self.blog_post.title, formatted_content)
        
        # get_post_images should be called for category-based strategy
        mock_get_images.assert_called_once()
    
    @patch('blog.services.linkedin_content_formatter.LinkedInContentFormatter.get_post_images')
    def test_format_post_with_config_no_images_available(self, mock_get_images):
        """Test format_post_with_config when no images are available."""
        from blog.services.linkedin_content_formatter import LinkedInContentFormatter
        
        # Mock no available images
        mock_get_images.return_value = []
        
        formatter = LinkedInContentFormatter()
        formatted_content = formatter.format_post_with_config(
            self.blog_post, 
            self.config, 
            include_excerpt=True, 
            optimize_for_images=True
        )
        
        # Verify content is formatted correctly as text-only
        self.assertIsInstance(formatted_content, str)
        self.assertIn(self.blog_post.title, formatted_content)
        self.assertIn(self.blog_post.excerpt, formatted_content)
    
    @patch('blog.services.linkedin_content_formatter.LinkedInContentFormatter.get_post_images')
    def test_format_post_with_config_image_optimization(self, mock_get_images):
        """Test that content is optimized when images are present."""
        from blog.services.linkedin_content_formatter import LinkedInContentFormatter
        
        # Create post with long excerpt
        long_excerpt = "A" * 400  # Longer than MAX_EXCERPT_LENGTH
        self.blog_post.excerpt = long_excerpt
        self.blog_post.save()
        
        # Mock available images
        mock_get_images.return_value = ['https://example.com/image1.jpg']
        
        formatter = LinkedInContentFormatter()
        formatted_content = formatter.format_post_with_config(
            self.blog_post, 
            self.config, 
            include_excerpt=True, 
            optimize_for_images=True
        )
        
        # Verify content is optimized (shortened) for image posts
        self.assertIsInstance(formatted_content, str)
        self.assertIn(self.blog_post.title, formatted_content)
        # Content should be shorter than original excerpt due to optimization
        self.assertLess(len(formatted_content), len(long_excerpt) + len(self.blog_post.title) + 100)
    
    def test_format_post_with_config_no_config_provided(self):
        """Test format_post_with_config with no configuration provided."""
        from blog.services.linkedin_content_formatter import LinkedInContentFormatter
        
        formatter = LinkedInContentFormatter()
        
        # Should fall back to default formatting
        with patch.object(formatter, 'format_post_content') as mock_format:
            mock_format.return_value = "Formatted content"
            
            result = formatter.format_post_with_config(
                self.blog_post, 
                None,  # No config
                include_excerpt=True, 
                optimize_for_images=True
            )
            
            # Should call the fallback method
            mock_format.assert_called_once_with(self.blog_post, True, True)
            self.assertEqual(result, "Formatted content")
    
    @patch('blog.services.linkedin_content_formatter.LinkedInContentFormatter.get_post_images')
    def test_format_post_with_config_hashtags_integration(self, mock_get_images):
        """Test that hashtags are properly integrated in configuration-aware formatting."""
        from blog.services.linkedin_content_formatter import LinkedInContentFormatter
        
        # Mock available images
        mock_get_images.return_value = ['https://example.com/image1.jpg']
        
        formatter = LinkedInContentFormatter()
        formatted_content = formatter.format_post_with_config(
            self.blog_post, 
            self.config, 
            include_excerpt=True, 
            optimize_for_images=True
        )
        
        # Verify hashtags are included (based on tags)
        self.assertIsInstance(formatted_content, str)
        # Should contain hashtags generated from tags
        self.assertIn('#', formatted_content)  # At least one hashtag should be present
    
    @patch('blog.services.linkedin_content_formatter.LinkedInContentFormatter.get_post_images')
    def test_format_post_with_config_hashtags_disabled(self, mock_get_images):
        """Test format_post_with_config with hashtags disabled."""
        from blog.services.linkedin_content_formatter import LinkedInContentFormatter
        
        # Disable hashtags
        self.config.enable_hashtags = False
        self.config.save()
        
        # Mock available images
        mock_get_images.return_value = ['https://example.com/image1.jpg']
        
        formatter = LinkedInContentFormatter()
        formatted_content = formatter.format_post_with_config(
            self.blog_post, 
            self.config, 
            include_excerpt=True, 
            optimize_for_images=True
        )
        
        # Verify no hashtags are included
        self.assertIsInstance(formatted_content, str)
        self.assertIn(self.blog_post.title, formatted_content)
        # Should not contain hashtags when disabled
        lines = formatted_content.split('\n')
        hashtag_lines = [line for line in lines if line.strip().startswith('#')]
        self.assertEqual(len(hashtag_lines), 0)
    
    @patch('blog.services.linkedin_content_formatter.LinkedInContentFormatter.get_post_images')
    def test_format_post_with_config_without_excerpt(self, mock_get_images):
        """Test format_post_with_config without including excerpt."""
        from blog.services.linkedin_content_formatter import LinkedInContentFormatter
        
        # Mock available images
        mock_get_images.return_value = ['https://example.com/image1.jpg']
        
        formatter = LinkedInContentFormatter()
        formatted_content = formatter.format_post_with_config(
            self.blog_post, 
            self.config, 
            include_excerpt=False,  # Don't include excerpt
            optimize_for_images=True
        )
        
        # Verify content doesn't include excerpt
        self.assertIsInstance(formatted_content, str)
        self.assertIn(self.blog_post.title, formatted_content)
        self.assertNotIn(self.blog_post.excerpt, formatted_content)
    
    @patch('blog.services.linkedin_content_formatter.LinkedInContentFormatter.get_post_images')
    def test_format_post_with_config_error_handling(self, mock_get_images):
        """Test error handling in format_post_with_config."""
        from blog.services.linkedin_content_formatter import LinkedInContentFormatter
        
        # Mock get_post_images to raise an exception
        mock_get_images.side_effect = Exception("Image processing error")
        
        formatter = LinkedInContentFormatter()
        
        # Should handle the exception gracefully
        formatted_content = formatter.format_post_with_config(
            self.blog_post, 
            self.config, 
            include_excerpt=True, 
            optimize_for_images=True
        )
        
        # Should still return formatted content despite image error
        self.assertIsInstance(formatted_content, str)
        self.assertIn(self.blog_post.title, formatted_content)
        self.assertGreater(len(formatted_content), 0)


class LinkedInImagePostingConfigurationIntegrationTests(TestCase):
    """Integration tests for image posting configuration with content formatting."""
    
    def setUp(self):
        """Set up test data."""
        from django.contrib.auth.models import User
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create test blog post
        self.blog_post = Post.objects.create(
            title="Integration Test Blog Post",
            content="<p>This is integration test content.</p>",
            excerpt="Integration test excerpt.",
            status='published',
            author=self.user
        )
        
        # Create test category
        self.category = Category.objects.create(name="Integration", slug="integration")
        self.blog_post.categories.add(self.category)
    
    def test_end_to_end_image_posting_always_strategy(self):
        """Test end-to-end image posting with 'always' strategy."""
        config = LinkedInConfig(
            client_id="test_client_id",
            enable_image_posting=True,
            image_posting_strategy='always'
        )
        config.set_client_secret("test_secret")
        config.save()
        
        # Test the complete flow
        image_config = config.get_image_posting_config()
        should_include = config.should_include_images(self.blog_post)
        
        self.assertTrue(image_config['enable_image_posting'])
        self.assertEqual(image_config['image_posting_strategy'], 'always')
        self.assertTrue(should_include)
    
    def test_end_to_end_image_posting_never_strategy(self):
        """Test end-to-end image posting with 'never' strategy."""
        config = LinkedInConfig(
            client_id="test_client_id",
            enable_image_posting=True,
            image_posting_strategy='never'
        )
        config.set_client_secret("test_secret")
        config.save()
        
        # Test the complete flow
        image_config = config.get_image_posting_config()
        should_include = config.should_include_images(self.blog_post)
        
        self.assertTrue(image_config['enable_image_posting'])
        self.assertEqual(image_config['image_posting_strategy'], 'never')
        self.assertFalse(should_include)  # Strategy overrides global setting
    
    def test_end_to_end_image_posting_disabled_globally(self):
        """Test end-to-end image posting when disabled globally."""
        config = LinkedInConfig(
            client_id="test_client_id",
            enable_image_posting=False,
            image_posting_strategy='always'
        )
        config.set_client_secret("test_secret")
        config.save()
        
        # Test the complete flow
        image_config = config.get_image_posting_config()
        should_include = config.should_include_images(self.blog_post)
        
        self.assertFalse(image_config['enable_image_posting'])
        self.assertEqual(image_config['image_posting_strategy'], 'always')
        self.assertFalse(should_include)  # Global setting takes precedence
    
    @patch('blog.services.linkedin_content_formatter.LinkedInContentFormatter.get_post_images')
    def test_integration_with_content_formatter(self, mock_get_images):
        """Test integration between configuration and content formatter."""
        from blog.services.linkedin_content_formatter import LinkedInContentFormatter
        
        # Mock available images
        mock_get_images.return_value = ['https://example.com/test-image.jpg']
        
        # Test with images enabled
        config_enabled = LinkedInConfig(
            client_id="test_client_id",
            enable_image_posting=True,
            image_posting_strategy='always'
        )
        config_enabled.set_client_secret("test_secret")
        config_enabled.save()
        
        formatter = LinkedInContentFormatter()
        content_with_images = formatter.format_post_with_config(
            self.blog_post, 
            config_enabled, 
            include_excerpt=True, 
            optimize_for_images=True
        )
        
        # Test with images disabled
        config_disabled = LinkedInConfig(
            client_id="test_client_id_2",
            enable_image_posting=False,
            image_posting_strategy='never'
        )
        config_disabled.set_client_secret("test_secret")
        config_disabled.save()
        
        content_without_images = formatter.format_post_with_config(
            self.blog_post, 
            config_disabled, 
            include_excerpt=True, 
            optimize_for_images=True
        )
        
        # Both should produce valid content
        self.assertIsInstance(content_with_images, str)
        self.assertIsInstance(content_without_images, str)
        self.assertGreater(len(content_with_images), 0)
        self.assertGreater(len(content_without_images), 0)
        
        # Content should contain the blog post title in both cases
        self.assertIn(self.blog_post.title, content_with_images)
        self.assertIn(self.blog_post.title, content_without_images)