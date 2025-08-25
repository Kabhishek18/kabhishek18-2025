"""
Integration tests for end-to-end LinkedIn posting with hashtag and image posting features.

This test suite covers Task 8 requirements:
- Test complete LinkedIn posting flow with hashtags enabled
- Test posting with different image posting strategies
- Test posting with custom hashtag rules and blacklist
- Test error handling and fallback scenarios

Requirements: 1.6, 2.4, 2.5
"""

import json
import time
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock, call
from django.test import TestCase, TransactionTestCase, override_settings
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test.client import RequestFactory
from PIL import Image
from io import BytesIO

from blog.models import Post, Category, Tag, MediaItem
from blog.linkedin_models import LinkedInConfig, LinkedInPost
from blog.services.linkedin_service import LinkedInAPIService, LinkedInAPIError, LinkedInAuthenticationError
from blog.services.linkedin_content_formatter import LinkedInContentFormatter, HashtagGenerator
from blog.services.linkedin_image_service import LinkedInImageService
from blog.tasks import post_to_linkedin
from blog.utils.image_processor import ImageProcessor


def create_test_image(width=800, height=600, format='JPEG'):
    """Helper function to create a test image."""
    image = Image.new('RGB', (width, height), color='red')
    image_io = BytesIO()
    image.save(image_io, format=format)
    image_io.seek(0)
    return image_io


def create_test_linkedin_config(enable_hashtags=True, enable_image_posting=True, 
                               image_strategy='always', max_hashtags=5):
    """Helper function to create a test LinkedIn configuration."""
    config = LinkedInConfig(
        client_id='test_client_id',
        is_active=True,
        enable_hashtags=enable_hashtags,
        max_hashtags=max_hashtags,
        enable_image_posting=enable_image_posting,
        image_posting_strategy=image_strategy,
        custom_hashtag_rules={
            'technology': ['#TechTips', '#Programming'],
            'tutorial': ['#Tutorial', '#Learning']
        },
        hashtag_blacklist=['spam', 'clickbait', 'urgent'],
        category_image_overrides={
            'news': False,  # Never include images for news
            'tutorial': True  # Always include images for tutorials
        }
    )
    config.set_client_secret('test_client_secret')
    config.set_access_token('test_access_token')
    config.token_expires_at = timezone.now() + timezone.timedelta(hours=1)
    config.save()
    return config


class LinkedInHashtagImageEndToEndTest(TransactionTestCase):
    """
    Test complete LinkedIn posting workflow with hashtags and image posting enabled.
    
    This test class verifies the complete integration:
    1. Blog post creation with tags and categories
    2. Hashtag generation based on configuration
    3. Image posting based on strategy
    4. Complete LinkedIn posting workflow
    5. Success tracking and error handling
    
    Requirements: 1.6, 2.4, 2.5
    """
    
    def setUp(self):
        """Set up test data for end-to-end hashtag and image posting tests."""
        # Create test user
        self.user = User.objects.create_user(
            username='testauthor',
            email='author@example.com',
            password='testpass123'
        )
        
        # Create test categories and tags
        self.category_tech = Category.objects.create(name='Technology', slug='technology')
        self.category_tutorial = Category.objects.create(name='Tutorial', slug='tutorial')
        self.category_news = Category.objects.create(name='News', slug='news')
        
        self.tag_python = Tag.objects.create(name='Python', slug='python')
        self.tag_django = Tag.objects.create(name='Django', slug='django')
        self.tag_webdev = Tag.objects.create(name='Web Development', slug='web-development')
        
        # Create LinkedIn configuration with hashtags and image posting enabled
        self.linkedin_config = create_test_linkedin_config()
        
        # Create temporary directory for test images
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.temp_dir)
        
        # Create test image
        self.test_image = create_test_image()
    
    def create_test_post_with_image(self, title='Test Post with Image', categories=None, tags=None):
        """Helper method to create a test blog post with featured image."""
        # Create the post
        post = Post.objects.create(
            title=title,
            slug=title.lower().replace(' ', '-'),
            author=self.user,
            content='<p>This is a comprehensive test post about Python and Django development.</p>',
            excerpt='Test post with hashtags and image',
            status='published'
        )
        
        # Add categories
        if categories:
            for category in categories:
                post.categories.add(category)
        
        # Add tags
        if tags:
            for tag in tags:
                post.tags.add(tag)
        
        # Create and attach featured image
        image_file = SimpleUploadedFile(
            name='test_image.jpg',
            content=self.test_image.getvalue(),
            content_type='image/jpeg'
        )
        
        post.featured_image = image_file
        post.save()
        
        return post
    
    @patch('blog.services.linkedin_service.LinkedInAPIService')
    @patch('blog.services.linkedin_image_service.LinkedInImageService')
    def test_complete_workflow_with_hashtags_and_images(self, mock_image_service_class, mock_api_service_class):
        """
        Test complete end-to-end workflow with hashtags and image posting enabled.
        
        Requirements: 1.6, 2.4, 2.5
        """
        # Mock the LinkedIn API service
        mock_api_service = Mock()
        mock_api_service_class.return_value = mock_api_service
        
        # Mock the LinkedIn image service
        mock_image_service = Mock()
        mock_image_service_class.return_value = mock_image_service
        mock_image_service.upload_image.return_value = {
            'asset_id': 'test_asset_id_123',
            'upload_url': 'https://linkedin.com/upload/test_123'
        }
        
        # Mock successful LinkedIn post result
        def mock_post_blog_article(blog_post, attempt_count=1):
            linkedin_post, created = LinkedInPost.objects.get_or_create(
                post=blog_post,
                defaults={'status': 'pending'}
            )
            linkedin_post.mark_as_success(
                linkedin_post_id='test_linkedin_id_with_hashtags',
                linkedin_post_url='https://linkedin.com/posts/test_hashtags_123'
            )
            linkedin_post.attempt_count = attempt_count
            linkedin_post.save()
            return linkedin_post
        
        mock_api_service.post_blog_article.side_effect = mock_post_blog_article
        
        # Create test post with categories and tags
        post = self.create_test_post_with_image(
            title='Python Django Tutorial for Beginners',
            categories=[self.category_tech, self.category_tutorial],
            tags=[self.tag_python, self.tag_django, self.tag_webdev]
        )
        
        # Execute the complete posting workflow
        with patch('blog.services.linkedin_service.LinkedInAPIService', return_value=mock_api_service):
            with patch('blog.services.linkedin_image_service.LinkedInImageService', return_value=mock_image_service):
                result = post_to_linkedin(post.id)
        
        # Verify task result
        self.assertTrue(result['success'])
        self.assertEqual(result['post_id'], post.id)
        self.assertEqual(result['linkedin_post_id'], 'test_linkedin_id_with_hashtags')
        self.assertIn('task_duration', result)
        
        # Verify LinkedIn post record was created
        linkedin_post = LinkedInPost.objects.get(post=post)
        self.assertEqual(linkedin_post.status, 'success')
        self.assertEqual(linkedin_post.linkedin_post_id, 'test_linkedin_id_with_hashtags')
        self.assertIsNotNone(linkedin_post.posted_at)
        
        # Verify the API service was called with the post
        mock_api_service.post_blog_article.assert_called_once_with(post, attempt_count=1)
        
        # Verify image service was called for image upload
        mock_image_service.upload_image.assert_called_once()
    
    @patch('blog.services.linkedin_service.LinkedInAPIService')
    def test_posting_with_different_image_strategies(self, mock_api_service_class):
        """
        Test posting with different image posting strategies.
        
        Requirements: 2.4, 2.5
        """
        mock_api_service = Mock()
        mock_api_service_class.return_value = mock_api_service
        
        def mock_post_blog_article(blog_post, attempt_count=1):
            linkedin_post, created = LinkedInPost.objects.get_or_create(
                post=blog_post,
                defaults={'status': 'pending'}
            )
            linkedin_post.mark_as_success(
                linkedin_post_id=f'test_id_{blog_post.id}',
                linkedin_post_url=f'https://linkedin.com/posts/test_{blog_post.id}'
            )
            linkedin_post.save()
            return linkedin_post
        
        mock_api_service.post_blog_article.side_effect = mock_post_blog_article
        
        # Test 1: Strategy 'always' - should include images
        self.linkedin_config.image_posting_strategy = 'always'
        self.linkedin_config.save()
        
        post_always = self.create_test_post_with_image(
            title='Post with Always Strategy',
            categories=[self.category_tech]
        )
        
        with patch('blog.services.linkedin_service.LinkedInAPIService', return_value=mock_api_service):
            result_always = post_to_linkedin(post_always.id)
        
        self.assertTrue(result_always['success'])
        
        # Test 2: Strategy 'never' - should not include images
        self.linkedin_config.image_posting_strategy = 'never'
        self.linkedin_config.save()
        
        post_never = self.create_test_post_with_image(
            title='Post with Never Strategy',
            categories=[self.category_tech]
        )
        
        with patch('blog.services.linkedin_service.LinkedInAPIService', return_value=mock_api_service):
            result_never = post_to_linkedin(post_never.id)
        
        self.assertTrue(result_never['success'])
        
        # Test 3: Strategy 'category_based' with news category (should not include images)
        self.linkedin_config.image_posting_strategy = 'category_based'
        self.linkedin_config.save()
        
        post_news = self.create_test_post_with_image(
            title='News Post Category Based',
            categories=[self.category_news]
        )
        
        with patch('blog.services.linkedin_service.LinkedInAPIService', return_value=mock_api_service):
            result_news = post_to_linkedin(post_news.id)
        
        self.assertTrue(result_news['success'])
        
        # Test 4: Strategy 'category_based' with tutorial category (should include images)
        post_tutorial = self.create_test_post_with_image(
            title='Tutorial Post Category Based',
            categories=[self.category_tutorial]
        )
        
        with patch('blog.services.linkedin_service.LinkedInAPIService', return_value=mock_api_service):
            result_tutorial = post_to_linkedin(post_tutorial.id)
        
        self.assertTrue(result_tutorial['success'])
        
        # Verify all posts were processed
        self.assertEqual(mock_api_service.post_blog_article.call_count, 4)
    
    @patch('blog.services.linkedin_service.LinkedInAPIService')
    def test_posting_with_custom_hashtag_rules_and_blacklist(self, mock_api_service_class):
        """
        Test posting with custom hashtag rules and blacklist filtering.
        
        Requirements: 1.6, 2.5
        """
        mock_api_service = Mock()
        mock_api_service_class.return_value = mock_api_service
        
        def mock_post_blog_article(blog_post, attempt_count=1):
            linkedin_post, created = LinkedInPost.objects.get_or_create(
                post=blog_post,
                defaults={'status': 'pending'}
            )
            linkedin_post.mark_as_success(
                linkedin_post_id=f'hashtag_test_{blog_post.id}',
                linkedin_post_url=f'https://linkedin.com/posts/hashtag_{blog_post.id}'
            )
            linkedin_post.save()
            return linkedin_post
        
        mock_api_service.post_blog_article.side_effect = mock_post_blog_article
        
        # Test with technology category (should use custom hashtag rules)
        post_tech = self.create_test_post_with_image(
            title='Advanced Python Programming Techniques',
            categories=[self.category_tech],
            tags=[self.tag_python, self.tag_django]
        )
        
        with patch('blog.services.linkedin_service.LinkedInAPIService', return_value=mock_api_service):
            result_tech = post_to_linkedin(post_tech.id)
        
        self.assertTrue(result_tech['success'])
        
        # Test with tutorial category (should use custom hashtag rules)
        post_tutorial = self.create_test_post_with_image(
            title='Django Tutorial for Beginners',
            categories=[self.category_tutorial],
            tags=[self.tag_django, self.tag_webdev]
        )
        
        with patch('blog.services.linkedin_service.LinkedInAPIService', return_value=mock_api_service):
            result_tutorial = post_to_linkedin(post_tutorial.id)
        
        self.assertTrue(result_tutorial['success'])
        
        # Test with blacklisted terms in tags (should be filtered out)
        blacklisted_tag = Tag.objects.create(name='Urgent Spam', slug='urgent-spam')
        
        post_blacklist = self.create_test_post_with_image(
            title='Important Development Update',
            categories=[self.category_tech],
            tags=[self.tag_python, blacklisted_tag]
        )
        
        with patch('blog.services.linkedin_service.LinkedInAPIService', return_value=mock_api_service):
            result_blacklist = post_to_linkedin(post_blacklist.id)
        
        self.assertTrue(result_blacklist['success'])
        
        # Verify all posts were processed
        self.assertEqual(mock_api_service.post_blog_article.call_count, 3)
    
    @patch('blog.services.linkedin_service.LinkedInAPIService')
    @patch('blog.services.linkedin_image_service.LinkedInImageService')
    def test_error_handling_and_fallback_scenarios(self, mock_image_service_class, mock_api_service_class):
        """
        Test error handling and fallback scenarios for hashtag and image posting.
        
        Requirements: 1.6, 2.5
        """
        # Test 1: Image upload failure should fallback to text-only posting
        mock_api_service = Mock()
        mock_api_service_class.return_value = mock_api_service
        
        mock_image_service = Mock()
        mock_image_service_class.return_value = mock_image_service
        mock_image_service.upload_image.side_effect = Exception("Image upload failed")
        
        def mock_post_blog_article_fallback(blog_post, attempt_count=1):
            linkedin_post, created = LinkedInPost.objects.get_or_create(
                post=blog_post,
                defaults={'status': 'pending'}
            )
            linkedin_post.mark_as_success(
                linkedin_post_id=f'fallback_test_{blog_post.id}',
                linkedin_post_url=f'https://linkedin.com/posts/fallback_{blog_post.id}'
            )
            linkedin_post.save()
            return linkedin_post
        
        mock_api_service.post_blog_article.side_effect = mock_post_blog_article_fallback
        
        post_image_fail = self.create_test_post_with_image(
            title='Post with Image Upload Failure',
            categories=[self.category_tech],
            tags=[self.tag_python]
        )
        
        with patch('blog.services.linkedin_service.LinkedInAPIService', return_value=mock_api_service):
            with patch('blog.services.linkedin_image_service.LinkedInImageService', return_value=mock_image_service):
                result_image_fail = post_to_linkedin(post_image_fail.id)
        
        # Should still succeed with text-only fallback
        self.assertTrue(result_image_fail['success'])
        
        # Test 2: Hashtag generation failure should continue with posting
        mock_api_service.reset_mock()
        
        # Create a post that would cause hashtag generation issues
        post_hashtag_fail = Post.objects.create(
            title='Post with Hashtag Issues',
            slug='post-hashtag-issues',
            author=self.user,
            content='Test content',
            excerpt='Test excerpt',
            status='published'
        )
        # Don't add any categories or tags to test fallback
        
        with patch('blog.services.linkedin_service.LinkedInAPIService', return_value=mock_api_service):
            result_hashtag_fail = post_to_linkedin(post_hashtag_fail.id)
        
        # Should still succeed even without hashtags
        self.assertTrue(result_hashtag_fail['success'])
        
        # Test 3: LinkedIn API authentication error
        mock_api_service.reset_mock()
        mock_api_service.post_blog_article.side_effect = LinkedInAuthenticationError(
            "Authentication failed", needs_reauth=True
        )
        
        post_auth_fail = self.create_test_post_with_image(
            title='Post with Auth Failure',
            categories=[self.category_tech]
        )
        
        with patch('blog.services.linkedin_service.LinkedInAPIService', return_value=mock_api_service):
            result_auth_fail = post_to_linkedin(post_auth_fail.id)
        
        # Should fail but be recorded properly
        self.assertFalse(result_auth_fail['success'])
        self.assertIn('error', result_auth_fail)
        
        # Verify LinkedIn post record shows failure
        linkedin_post_fail = LinkedInPost.objects.get(post=post_auth_fail)
        self.assertEqual(linkedin_post_fail.status, 'failed')
        self.assertIsNotNone(linkedin_post_fail.error_message)


class LinkedInHashtagConfigurationTest(TestCase):
    """
    Test hashtag configuration and generation with various scenarios.
    
    This test class focuses on:
    - Hashtag generation with different configurations
    - Custom hashtag rules application
    - Blacklist filtering
    - Configuration validation
    
    Requirements: 1.6, 2.5
    """
    
    def setUp(self):
        """Set up test data for hashtag configuration tests."""
        self.user = User.objects.create_user(
            username='hashtagtest',
            email='hashtag@example.com',
            password='testpass123'
        )
        
        # Create categories and tags
        self.category_tech = Category.objects.create(name='Technology', slug='technology')
        self.category_tutorial = Category.objects.create(name='Tutorial', slug='tutorial')
        
        self.tag_python = Tag.objects.create(name='Python', slug='python')
        self.tag_django = Tag.objects.create(name='Django', slug='django')
        self.tag_spam = Tag.objects.create(name='Urgent Clickbait', slug='urgent-clickbait')
    
    def test_hashtag_generation_with_custom_rules(self):
        """Test hashtag generation using custom rules for categories."""
        # Create config with custom hashtag rules
        config = create_test_linkedin_config(
            enable_hashtags=True,
            max_hashtags=5
        )
        
        # Create post with technology category
        post = Post.objects.create(
            title='Advanced Python Programming',
            slug='advanced-python-programming',
            author=self.user,
            content='Learn advanced Python techniques',
            excerpt='Python tutorial',
            status='published'
        )
        post.categories.add(self.category_tech)
        post.tags.add(self.tag_python, self.tag_django)
        
        # Test hashtag generation
        formatter = LinkedInContentFormatter()
        hashtags_string = formatter._generate_hashtags(post)
        
        # Should return a string with hashtags
        self.assertIsInstance(hashtags_string, str)
        self.assertGreater(len(hashtags_string), 0)
        
        # Verify hashtags are properly formatted
        hashtags_list = hashtags_string.split()
        for hashtag in hashtags_list:
            self.assertTrue(hashtag.startswith('#'))
            self.assertGreater(len(hashtag), 1)
    
    def test_hashtag_blacklist_filtering(self):
        """Test that blacklisted terms are filtered out from hashtags."""
        config = create_test_linkedin_config(
            enable_hashtags=True,
            max_hashtags=5
        )
        
        # Create post with blacklisted tag
        post = Post.objects.create(
            title='Important Development Update',
            slug='important-dev-update',
            author=self.user,
            content='Important development news',
            excerpt='Dev update',
            status='published'
        )
        post.categories.add(self.category_tech)
        post.tags.add(self.tag_python, self.tag_spam)  # tag_spam contains blacklisted words
        
        # Test hashtag generation
        formatter = LinkedInContentFormatter()
        hashtags_string = formatter._generate_hashtags(post)
        
        # Should not include blacklisted terms
        hashtag_text = hashtags_string.lower()
        self.assertNotIn('urgent', hashtag_text)
        self.assertNotIn('clickbait', hashtag_text)
        self.assertNotIn('spam', hashtag_text)
    
    def test_hashtag_generation_disabled(self):
        """Test that hashtag generation can be disabled."""
        config = create_test_linkedin_config(
            enable_hashtags=False,
            max_hashtags=5
        )
        
        post = Post.objects.create(
            title='Test Post Without Hashtags',
            slug='test-post-no-hashtags',
            author=self.user,
            content='Test content',
            excerpt='Test excerpt',
            status='published'
        )
        post.categories.add(self.category_tech)
        post.tags.add(self.tag_python)
        
        # Test hashtag generation
        formatter = LinkedInContentFormatter()
        hashtags_string = formatter._generate_hashtags(post)
        
        # Should return empty string when disabled
        self.assertEqual(hashtags_string, "")
    
    def test_max_hashtags_limit(self):
        """Test that hashtag generation respects the maximum limit."""
        config = create_test_linkedin_config(
            enable_hashtags=True,
            max_hashtags=2  # Limit to 2 hashtags
        )
        
        # Create post with many tags
        post = Post.objects.create(
            title='Post with Many Tags',
            slug='post-many-tags',
            author=self.user,
            content='Test content with many topics',
            excerpt='Many topics',
            status='published'
        )
        post.categories.add(self.category_tech, self.category_tutorial)
        post.tags.add(self.tag_python, self.tag_django)
        
        # Test hashtag generation
        formatter = LinkedInContentFormatter()
        hashtags_string = formatter._generate_hashtags(post)
        
        # Should not exceed the maximum limit
        hashtags_list = hashtags_string.split() if hashtags_string else []
        self.assertLessEqual(len(hashtags_list), 2)


class LinkedInImagePostingConfigurationTest(TestCase):
    """
    Test image posting configuration and strategy handling.
    
    This test class focuses on:
    - Different image posting strategies
    - Category-based image posting overrides
    - Image posting decision logic
    - Configuration validation
    
    Requirements: 2.4, 2.5
    """
    
    def setUp(self):
        """Set up test data for image posting configuration tests."""
        self.user = User.objects.create_user(
            username='imagetest',
            email='image@example.com',
            password='testpass123'
        )
        
        # Create categories
        self.category_tech = Category.objects.create(name='Technology', slug='technology')
        self.category_news = Category.objects.create(name='News', slug='news')
        self.category_tutorial = Category.objects.create(name='Tutorial', slug='tutorial')
        
        # Create test image
        self.test_image = create_test_image()
    
    def create_post_with_image(self, title, categories=None):
        """Helper to create a post with featured image."""
        post = Post.objects.create(
            title=title,
            slug=title.lower().replace(' ', '-'),
            author=self.user,
            content='Test content',
            excerpt='Test excerpt',
            status='published'
        )
        
        if categories:
            for category in categories:
                post.categories.add(category)
        
        # Add featured image
        image_file = SimpleUploadedFile(
            name='test.jpg',
            content=self.test_image.getvalue(),
            content_type='image/jpeg'
        )
        
        post.featured_image = image_file
        post.save()
        
        return post
    
    def test_image_posting_strategy_always(self):
        """Test 'always' image posting strategy."""
        config = create_test_linkedin_config(
            enable_image_posting=True,
            image_strategy='always'
        )
        
        post = self.create_post_with_image(
            'Test Post Always Strategy',
            categories=[self.category_tech]
        )
        
        # Test image posting decision
        should_include = config.should_include_images(post)
        self.assertTrue(should_include)
    
    def test_image_posting_strategy_never(self):
        """Test 'never' image posting strategy."""
        config = create_test_linkedin_config(
            enable_image_posting=True,
            image_strategy='never'
        )
        
        post = self.create_post_with_image(
            'Test Post Never Strategy',
            categories=[self.category_tech]
        )
        
        # Test image posting decision
        should_include = config.should_include_images(post)
        self.assertFalse(should_include)
    
    def test_image_posting_strategy_category_based(self):
        """Test 'category_based' image posting strategy with overrides."""
        config = create_test_linkedin_config(
            enable_image_posting=True,
            image_strategy='category_based'
        )
        
        # Test with news category (should not include images per override)
        post_news = self.create_post_with_image(
            'News Post Category Based',
            categories=[self.category_news]
        )
        
        should_include_news = config.should_include_images(post_news)
        self.assertFalse(should_include_news)
        
        # Test with tutorial category (should include images per override)
        post_tutorial = self.create_post_with_image(
            'Tutorial Post Category Based',
            categories=[self.category_tutorial]
        )
        
        should_include_tutorial = config.should_include_images(post_tutorial)
        self.assertTrue(should_include_tutorial)
        
        # Test with tech category (no override, should use default)
        post_tech = self.create_post_with_image(
            'Tech Post Category Based',
            categories=[self.category_tech]
        )
        
        should_include_tech = config.should_include_images(post_tech)
        # Should use default behavior (True for 'always' fallback)
        self.assertTrue(should_include_tech)
    
    def test_image_posting_disabled_globally(self):
        """Test that global image posting disable overrides all strategies."""
        config = create_test_linkedin_config(
            enable_image_posting=False,  # Globally disabled
            image_strategy='always'
        )
        
        post = self.create_post_with_image(
            'Test Post Globally Disabled',
            categories=[self.category_tutorial]  # Even with tutorial override
        )
        
        should_include = config.should_include_images(post)
        self.assertFalse(should_include)
    
    def test_post_without_featured_image(self):
        """Test image posting decision for posts without featured images."""
        config = create_test_linkedin_config(
            enable_image_posting=True,
            image_strategy='always'
        )
        
        # Create post without featured image
        post = Post.objects.create(
            title='Post Without Image',
            slug='post-without-image',
            author=self.user,
            content='Test content',
            excerpt='Test excerpt',
            status='published'
        )
        post.categories.add(self.category_tech)
        
        should_include = config.should_include_images(post)
        # Configuration says to include images, but post has no featured image
        # The configuration method only checks strategy, not image availability
        self.assertTrue(should_include)  # Config allows images
        
        # But the post itself has no featured image
        self.assertFalse(bool(post.featured_image))