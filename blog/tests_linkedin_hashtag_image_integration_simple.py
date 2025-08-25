"""
Simple integration tests for LinkedIn hashtag and image posting features.
Testing basic functionality first.
"""

from django.test import TestCase
from django.contrib.auth.models import User
from blog.models import Post, Category, Tag
from blog.linkedin_models import LinkedInConfig


class SimpleLinkedInIntegrationTest(TestCase):
    """Simple test to verify basic functionality."""
    
    def setUp(self):
        """Set up basic test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.category = Category.objects.create(name='Technology', slug='technology')
        self.tag = Tag.objects.create(name='Python', slug='python')
    
    def test_linkedin_config_creation(self):
        """Test creating LinkedIn configuration with hashtag settings."""
        config = LinkedInConfig(
            client_id='test_client_id',
            is_active=True,
            enable_hashtags=True,
            max_hashtags=5,
            enable_image_posting=True,
            image_posting_strategy='always'
        )
        config.set_client_secret('test_client_secret')
        config.save()
        
        self.assertTrue(config.enable_hashtags)
        self.assertEqual(config.max_hashtags, 5)
        self.assertTrue(config.enable_image_posting)
        self.assertEqual(config.image_posting_strategy, 'always')
    
    def test_post_creation_with_categories_and_tags(self):
        """Test creating a blog post with categories and tags."""
        post = Post.objects.create(
            title='Test Post',
            slug='test-post',
            author=self.user,
            content='Test content',
            excerpt='Test excerpt',
            status='published'
        )
        
        post.categories.add(self.category)
        post.tags.add(self.tag)
        
        self.assertEqual(post.categories.count(), 1)
        self.assertEqual(post.tags.count(), 1)
        self.assertEqual(post.status, 'published')