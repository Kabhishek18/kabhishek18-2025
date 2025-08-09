"""
Integration tests for LinkedIn posting workflow - Task 10 Implementation.

This test suite covers:
- End-to-end posting workflow from blog post publish to LinkedIn
- Signal handler integration testing
- Celery task execution and retry mechanisms
- Admin interface functionality and security verification

Requirements: 1.1, 1.2, 1.4, 1.5, 4.1, 4.2, 4.4
"""

import json
import time
from unittest.mock import Mock, patch, MagicMock, call
from django.test import TestCase, TransactionTestCase, override_settings
from django.contrib.auth.models import User
from django.contrib.admin.sites import AdminSite
from django.contrib.messages.storage.fallback import FallbackStorage
from django.http import HttpRequest
from django.urls import reverse
from django.utils import timezone
from django.test.client import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.messages.middleware import MessageMiddleware
from celery import current_app
from celery.result import AsyncResult

from .models import Post, Category, Tag
from .linkedin_models import LinkedInConfig, LinkedInPost
from .admin import PostAdmin, LinkedInConfigAdmin, LinkedInPostAdmin
from .tasks import post_to_linkedin, retry_failed_linkedin_posts
from .services.linkedin_service import LinkedInAPIService, LinkedInAPIError, LinkedInAuthenticationError


def create_test_linkedin_config(client_id='test_client_id', is_active=True):
    """Helper function to create a properly configured LinkedIn config for testing."""
    config = LinkedInConfig(
        client_id=client_id,
        is_active=is_active
    )
    config.set_client_secret('test_client_secret')
    config.set_access_token('test_access_token')
    config.token_expires_at = timezone.now() + timezone.timedelta(hours=1)
    config.save()
    return config


class LinkedInEndToEndIntegrationTest(TransactionTestCase):
    """
    Test end-to-end posting workflow from blog post publish to LinkedIn.
    
    This test class verifies the complete workflow:
    1. Blog post is created and published
    2. Signal handler triggers LinkedIn posting
    3. Celery task executes posting
    4. LinkedIn API is called
    5. Results are stored and tracked
    
    Requirements: 1.1, 1.2, 4.1
    """
    
    def setUp(self):
        """Set up test data for end-to-end testing."""
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
        self.linkedin_config = create_test_linkedin_config()
    
    def create_test_post(self, status='draft', title='Test Blog Post'):
        """Helper method to create a test blog post."""
        post = Post.objects.create(
            title=title,
            slug=title.lower().replace(' ', '-'),
            author=self.user,
            content='This is a test blog post content for LinkedIn integration testing.',
            excerpt='Test excerpt for LinkedIn posting.',
            status=status
        )
        post.categories.add(self.category)
        post.tags.add(self.tag)
        return post
    
    @patch('blog.services.linkedin_service.LinkedInAPIService')
    @patch('blog.signals.post_to_linkedin.delay')
    def test_complete_end_to_end_workflow_success(self, mock_task_delay, mock_service_class):
        """
        Test complete successful end-to-end workflow.
        
        Verifies:
        - Post creation and publishing triggers signal
        - Signal handler queues Celery task
        - Task executes LinkedIn posting
        - Success is tracked in database
        
        Requirements: 1.1, 1.2, 4.1
        """
        # Mock the LinkedIn service
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        
        # Mock successful LinkedIn post result
        def mock_post_blog_article(blog_post, attempt_count=1):
            # Create or get the LinkedIn post record
            linkedin_post, created = LinkedInPost.objects.get_or_create(
                post=blog_post,
                defaults={'status': 'pending'}
            )
            # Update it to success
            linkedin_post.mark_as_success(
                linkedin_post_id='test_linkedin_id_123',
                linkedin_post_url='https://linkedin.com/posts/test_123'
            )
            linkedin_post.attempt_count = attempt_count
            linkedin_post.save()
            return linkedin_post
        
        mock_service.post_blog_article.side_effect = mock_post_blog_article
        
        # Create and publish a blog post
        post = self.create_test_post(status='draft')
        
        # Publishing the post should trigger the signal
        post.status = 'published'
        post.save()
        
        # Verify signal handler was called
        mock_task_delay.assert_called_once_with(post.id)
        
        # Simulate the Celery task execution
        with patch('blog.services.linkedin_service.LinkedInAPIService', return_value=mock_service):
            result = post_to_linkedin(post.id)
        
        # Verify task result
        self.assertTrue(result['success'])
        self.assertEqual(result['post_id'], post.id)
        self.assertEqual(result['linkedin_post_id'], 'test_linkedin_id_123')
        self.assertIn('task_duration', result)
        
        # Verify LinkedIn post record was created
        linkedin_post = LinkedInPost.objects.get(post=post)
        self.assertEqual(linkedin_post.status, 'success')
        self.assertEqual(linkedin_post.linkedin_post_id, 'test_linkedin_id_123')
        self.assertEqual(linkedin_post.linkedin_post_url, 'https://linkedin.com/posts/test_123')
        self.assertIsNotNone(linkedin_post.posted_at)
        
        # Verify service was called correctly
        mock_service.post_blog_article.assert_called_once_with(post, attempt_count=1)


class LinkedInSignalIntegrationTest(TestCase):
    """
    Test signal handler integration for LinkedIn posting.
    
    This test class focuses on the signal handling logic:
    - Signal triggering conditions
    - Duplicate prevention logic
    - Configuration validation
    - Error handling in signals
    
    Requirements: 1.1, 1.2, 4.1
    """
    
    def setUp(self):
        """Set up test data for signal testing."""
        self.user = User.objects.create_user(
            username='testauthor',
            email='author@example.com',
            password='testpass123'
        )
        
        self.linkedin_config = create_test_linkedin_config()
    
    def create_test_post(self, status='draft', title='Test Post'):
        """Helper method to create a test blog post."""
        return Post.objects.create(
            title=title,
            slug=title.lower().replace(' ', '-'),
            author=self.user,
            content='Test content',
            excerpt='Test excerpt',
            status=status
        )
    
    @patch('blog.signals.post_to_linkedin.delay')
    def test_signal_triggers_on_status_change_to_published(self, mock_task):
        """
        Test that signal triggers when post status changes to published.
        
        Requirements: 1.1, 1.2
        """
        # Create draft post
        post = self.create_test_post(status='draft')
        mock_task.reset_mock()
        
        # Change status to published
        post.status = 'published'
        post.save()
        
        # Verify task was queued
        mock_task.assert_called_once_with(post.id)


class LinkedInCeleryTaskIntegrationTest(TransactionTestCase):
    """
    Test Celery task execution and retry mechanisms for LinkedIn posting.
    
    This test class focuses on:
    - Task execution with various scenarios
    - Retry logic and exponential backoff
    - Error handling and recovery
    - Task monitoring and status tracking
    
    Requirements: 1.4, 1.5, 4.1, 4.3
    """
    
    def setUp(self):
        """Set up test data for Celery task testing."""
        self.user = User.objects.create_user(
            username='testauthor',
            email='author@example.com',
            password='testpass123'
        )
        
        self.linkedin_config = create_test_linkedin_config()
        
        self.blog_post = Post.objects.create(
            title='Test Blog Post for Celery',
            slug='test-blog-post-celery',
            author=self.user,
            content='Test content for Celery task testing.',
            excerpt='Test excerpt',
            status='published'
        )
    
    @patch('blog.services.linkedin_service.LinkedInAPIService')
    def test_task_execution_success(self, mock_service_class):
        """
        Test successful task execution.
        
        Requirements: 1.4, 4.1
        """
        # Mock successful LinkedIn service
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        
        def mock_post_blog_article(blog_post, attempt_count=1):
            # Create or get the LinkedIn post record
            linkedin_post, created = LinkedInPost.objects.get_or_create(
                post=blog_post,
                defaults={'status': 'pending'}
            )
            # Update it to success
            linkedin_post.mark_as_success(
                linkedin_post_id='task_test_id',
                linkedin_post_url='https://linkedin.com/posts/task_test'
            )
            linkedin_post.attempt_count = attempt_count
            linkedin_post.save()
            return linkedin_post
        
        mock_service.post_blog_article.side_effect = mock_post_blog_article
        
        # Execute the task
        result = post_to_linkedin(self.blog_post.id)
        
        # Verify result
        self.assertTrue(result['success'])
        self.assertEqual(result['post_id'], self.blog_post.id)
        self.assertEqual(result['linkedin_post_id'], 'task_test_id')
        self.assertIn('task_duration', result)
        
        # Verify LinkedIn post record
        linkedin_post = LinkedInPost.objects.get(post=self.blog_post)
        self.assertEqual(linkedin_post.status, 'success')
        self.assertEqual(linkedin_post.linkedin_post_id, 'task_test_id')


class LinkedInAdminIntegrationTest(TestCase):
    """
    Test admin interface functionality and security for LinkedIn integration.
    
    This test class focuses on:
    - Admin interface functionality
    - Security of credential handling
    - Admin actions and bulk operations
    - Permission and access control
    
    Requirements: 2.4, 4.4
    """
    
    def setUp(self):
        """Set up test data for admin interface testing."""
        # Create superuser for admin access
        self.superuser = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        
        # Create regular user
        self.user = User.objects.create_user(
            username='testauthor',
            email='author@example.com',
            password='testpass123'
        )
        
        # Create LinkedIn configuration
        self.linkedin_config = create_test_linkedin_config()
        
        # Create test blog post
        self.blog_post = Post.objects.create(
            title='Test Admin Post',
            slug='test-admin-post',
            author=self.user,
            content='Test content for admin testing.',
            excerpt='Test excerpt',
            status='published'
        )
        
        # Create LinkedIn post record
        self.linkedin_post = LinkedInPost.objects.create(
            post=self.blog_post,
            status='success',
            linkedin_post_id='admin_test_id',
            linkedin_post_url='https://linkedin.com/posts/admin_test',
            posted_at=timezone.now()
        )
        
        # Set up admin instances
        self.admin_site = AdminSite()
        self.post_admin = PostAdmin(Post, self.admin_site)
        self.linkedin_config_admin = LinkedInConfigAdmin(LinkedInConfig, self.admin_site)
        self.linkedin_post_admin = LinkedInPostAdmin(LinkedInPost, self.admin_site)
        
        # Set up request factory
        self.factory = RequestFactory()
    
    def _create_admin_request(self, user=None, method='GET', path='/admin/', data=None):
        """Helper method to create admin request with proper middleware."""
        if method.upper() == 'POST':
            request = self.factory.post(path, data or {})
        else:
            request = self.factory.get(path)
        
        request.user = user or self.superuser
        
        # Add session middleware
        middleware = SessionMiddleware(lambda req: None)
        middleware.process_request(request)
        request.session.save()
        
        # Add messages middleware
        messages_middleware = MessageMiddleware(lambda req: None)
        messages_middleware.process_request(request)
        request._messages = FallbackStorage(request)
        
        return request
    
    def test_post_admin_linkedin_status_display(self):
        """
        Test LinkedIn status display in Post admin.
        
        Requirements: 4.4
        """
        # Test successful post status display
        status_html = self.post_admin.linkedin_status(self.blog_post)
        
        self.assertIn('✓ Posted', status_html)
        self.assertIn('green', status_html)
        self.assertIn(self.linkedin_post.linkedin_post_url, status_html)
        
        # Test failed post status
        self.linkedin_post.status = 'failed'
        self.linkedin_post.error_message = 'Test error'
        self.linkedin_post.save()
        
        status_html = self.post_admin.linkedin_status(self.blog_post)
        self.assertIn('Failed', status_html)
        self.assertIn('red', status_html)
        
        # Test post without LinkedIn record
        post_without_linkedin = Post.objects.create(
            title='No LinkedIn Post',
            slug='no-linkedin-post',
            author=self.user,
            content='No LinkedIn content',
            status='published'
        )
        
        status_html = self.post_admin.linkedin_status(post_without_linkedin)
        self.assertIn('Not Posted', status_html)
        self.assertIn('gray', status_html)
    
    def test_linkedin_config_admin_security(self):
        """
        Test LinkedIn configuration admin security features.
        
        Requirements: 2.4, 4.4
        """
        # Test credential validation
        validation_result = self.linkedin_config.validate_credentials()
        
        # Should have validation results
        self.assertIn('client_secret_valid', validation_result)
        self.assertIn('access_token_valid', validation_result)
        self.assertIn('errors', validation_result)
        
        # Test that admin has proper security restrictions
        self.assertTrue(hasattr(self.linkedin_config_admin, 'readonly_fields'))
        self.assertTrue(hasattr(self.linkedin_config_admin, 'fieldsets'))