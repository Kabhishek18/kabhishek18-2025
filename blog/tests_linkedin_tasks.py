"""
Tests for LinkedIn Celery tasks.

This module tests the LinkedIn posting tasks including:
- Main posting task functionality
- Retry logic and exponential backoff
- Error handling and status tracking
- Task monitoring and failure handling
"""

from unittest.mock import Mock, patch, MagicMock
from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth.models import User
from celery.exceptions import Retry

from .models import Post, Category
from .linkedin_models import LinkedInPost, LinkedInConfig
from .tasks import post_to_linkedin, retry_failed_linkedin_posts, monitor_linkedin_health
from .services.linkedin_service import LinkedInAPIError


class LinkedInTasksTestCase(TestCase):
    """Test case for LinkedIn Celery tasks."""
    
    def setUp(self):
        """Set up test data."""
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create test category
        self.category = Category.objects.create(
            name='Test Category',
            slug='test-category'
        )
        
        # Create test blog post
        self.blog_post = Post.objects.create(
            title='Test Blog Post',
            slug='test-blog-post',
            content='This is a test blog post content.',
            excerpt='Test excerpt',
            author=self.user,
            status='published'
        )
        self.blog_post.categories.add(self.category)
        
        # Create LinkedIn configuration
        self.linkedin_config = LinkedInConfig.objects.create(
            client_id='test_client_id',
            is_active=True
        )
        self.linkedin_config.set_client_secret('test_client_secret')
        self.linkedin_config.set_access_token('test_access_token')
        self.linkedin_config.token_expires_at = timezone.now() + timedelta(hours=1)
        self.linkedin_config.save()
    
    def test_post_to_linkedin_success(self):
        """Test successful LinkedIn posting."""
        with patch('blog.tasks.LinkedInAPIService') as mock_service_class:
            # Mock the service instance
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            # Mock successful posting
            mock_linkedin_post = Mock()
            mock_linkedin_post.linkedin_post_id = 'test_linkedin_id'
            mock_linkedin_post.linkedin_post_url = 'https://linkedin.com/posts/test'
            mock_linkedin_post.attempt_count = 1
            mock_service.post_blog_article.return_value = mock_linkedin_post
            
            # Create a mock task instance
            mock_task = Mock()
            mock_task.request.retries = 0
            mock_task.max_retries = 3
            
            # Call the task
            result = post_to_linkedin(mock_task, self.blog_post.id)
            
            # Verify result
            self.assertTrue(result['success'])
            self.assertEqual(result['post_id'], self.blog_post.id)
            self.assertEqual(result['linkedin_post_id'], 'test_linkedin_id')
            self.assertIn('task_duration', result)
            
            # Verify service was called correctly
            mock_service.post_blog_article.assert_called_once_with(self.blog_post)
    
    def test_post_to_linkedin_post_not_found(self):
        """Test handling of non-existent blog post."""
        mock_task = Mock()
        mock_task.request.retries = 0
        
        result = post_to_linkedin(mock_task, 99999)  # Non-existent post ID
        
        self.assertFalse(result['success'])
        self.assertIn('not found', result['error'])
        self.assertEqual(result['post_id'], 99999)
    
    def test_post_to_linkedin_no_config(self):
        """Test handling when LinkedIn is not configured."""
        # Deactivate LinkedIn config
        self.linkedin_config.is_active = False
        self.linkedin_config.save()
        
        mock_task = Mock()
        mock_task.request.retries = 0
        
        result = post_to_linkedin(mock_task, self.blog_post.id)
        
        self.assertFalse(result['success'])
        self.assertIn('not configured', result['error'])
        self.assertTrue(result.get('skipped', False))
    
    def test_post_to_linkedin_already_posted(self):
        """Test handling when post is already successfully posted."""
        # Create existing successful LinkedIn post
        linkedin_post = LinkedInPost.objects.create(
            post=self.blog_post,
            status='success',
            linkedin_post_id='existing_id',
            linkedin_post_url='https://linkedin.com/posts/existing'
        )
        
        mock_task = Mock()
        mock_task.request.retries = 0
        
        result = post_to_linkedin(mock_task, self.blog_post.id)
        
        self.assertTrue(result['success'])
        self.assertTrue(result.get('already_posted', False))
        self.assertEqual(result['linkedin_post_id'], 'existing_id')
    
    @patch('blog.tasks._should_retry_linkedin_error')
    @patch('blog.tasks._calculate_retry_delay')
    def test_post_to_linkedin_retry_logic(self, mock_calculate_delay, mock_should_retry):
        """Test retry logic with LinkedIn API errors."""
        mock_calculate_delay.return_value = 120  # 2 minutes
        mock_should_retry.return_value = True
        
        with patch('blog.tasks.LinkedInAPIService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            # Mock LinkedIn API error
            api_error = LinkedInAPIError("Rate limit exceeded", "RATE_LIMIT", 429)
            mock_service.post_blog_article.side_effect = api_error
            
            # Create mock task with retry capability
            mock_task = Mock()
            mock_task.request.retries = 0
            mock_task.max_retries = 3
            mock_task.retry.side_effect = Retry("Retrying task")
            
            # Call the task and expect retry
            with self.assertRaises(Retry):
                post_to_linkedin(mock_task, self.blog_post.id)
            
            # Verify retry was called with correct delay
            mock_task.retry.assert_called_once_with(countdown=120, exc=api_error)
            
            # Verify LinkedIn post status was updated
            linkedin_post = LinkedInPost.objects.get(post=self.blog_post)
            self.assertEqual(linkedin_post.status, 'retrying')
            self.assertIsNotNone(linkedin_post.next_retry_at)
    
    @patch('blog.tasks._should_retry_linkedin_error')
    def test_post_to_linkedin_final_failure(self, mock_should_retry):
        """Test final failure after max retries."""
        mock_should_retry.return_value = False  # Don't retry
        
        with patch('blog.tasks.LinkedInAPIService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            # Mock LinkedIn API error
            api_error = LinkedInAPIError("Invalid credentials", "AUTH_ERROR", 401)
            mock_service.post_blog_article.side_effect = api_error
            
            mock_task = Mock()
            mock_task.request.retries = 3  # Max retries reached
            mock_task.max_retries = 3
            
            result = post_to_linkedin(mock_task, self.blog_post.id)
            
            # Verify final failure
            self.assertFalse(result['success'])
            self.assertEqual(result['error'], "Invalid credentials")
            self.assertEqual(result['error_code'], "AUTH_ERROR")
            self.assertTrue(result.get('final_failure', False))
            
            # Verify LinkedIn post was marked as failed
            linkedin_post = LinkedInPost.objects.get(post=self.blog_post)
            self.assertEqual(linkedin_post.status, 'failed')
    
    def test_retry_failed_linkedin_posts_no_posts(self):
        """Test retry task when no posts are ready for retry."""
        result = retry_failed_linkedin_posts()
        
        self.assertEqual(result['posts_checked'], 0)
        self.assertEqual(result['posts_retried'], 0)
        self.assertIn('No posts ready', result['message'])
    
    @patch('blog.tasks.post_to_linkedin.delay')
    def test_retry_failed_linkedin_posts_with_posts(self, mock_delay):
        """Test retry task with posts ready for retry."""
        # Create LinkedIn post ready for retry
        linkedin_post = LinkedInPost.objects.create(
            post=self.blog_post,
            status='retrying',
            next_retry_at=timezone.now() - timedelta(minutes=5)  # Ready for retry
        )
        
        result = retry_failed_linkedin_posts()
        
        self.assertEqual(result['posts_checked'], 1)
        self.assertEqual(result['posts_retried'], 1)
        self.assertIn('Queued 1 posts', result['message'])
        
        # Verify the main task was queued
        mock_delay.assert_called_once_with(self.blog_post.id)
    
    def test_cleanup_old_linkedin_posts(self):
        """Test cleanup of old LinkedIn post records."""
        from .tasks import cleanup_old_linkedin_posts
        
        # Create old successful post (100 days ago)
        old_successful = LinkedInPost.objects.create(
            post=self.blog_post,
            status='success',
            posted_at=timezone.now() - timedelta(days=100)
        )
        
        # Create recent successful post
        recent_successful = LinkedInPost.objects.create(
            post=self.blog_post,
            status='success',
            posted_at=timezone.now() - timedelta(days=30)
        )
        
        # Create old failed post (40 days ago)
        old_failed = LinkedInPost.objects.create(
            post=self.blog_post,
            status='failed',
            created_at=timezone.now() - timedelta(days=40)
        )
        
        result = cleanup_old_linkedin_posts()
        
        # Verify cleanup results
        self.assertGreaterEqual(result['successful_posts_deleted'], 1)
        self.assertGreaterEqual(result['failed_posts_deleted'], 1)
        self.assertGreater(result['total_deleted'], 0)
    
    @patch('blog.tasks.LinkedInTaskMonitor')
    def test_monitor_linkedin_health(self, mock_monitor_class):
        """Test LinkedIn health monitoring task."""
        # Mock monitor instance
        mock_monitor = Mock()
        mock_monitor_class.return_value = mock_monitor
        
        # Mock health status
        mock_health_status = {
            'overall_health': 'good',
            'health_score': 85,
            'configuration_status': {'issues': []},
            'recent_performance': {'success_rate': 95}
        }
        mock_monitor.get_health_status.return_value = mock_health_status
        
        # Mock no failure alert
        mock_monitor.alert_on_failures.return_value = None
        
        # Mock retry status
        mock_retry_status = {
            'total_retrying': 2,
            'ready_for_retry': 1
        }
        mock_monitor.get_retry_queue_status.return_value = mock_retry_status
        
        result = monitor_linkedin_health()
        
        # Verify monitoring was performed
        self.assertEqual(result['health_status'], mock_health_status)
        self.assertIsNone(result['failure_alert'])
        self.assertEqual(result['retry_status'], mock_retry_status)
        self.assertIn('monitoring_completed_at', result)
        
        # Verify monitor methods were called
        mock_monitor.get_health_status.assert_called_once()
        mock_monitor.alert_on_failures.assert_called_once_with(
            threshold_percentage=50.0, 
            time_window_hours=1
        )
        mock_monitor.get_retry_queue_status.assert_called_once()


class LinkedInTaskUtilsTestCase(TestCase):
    """Test case for LinkedIn task utility functions."""
    
    def test_should_retry_linkedin_error_rate_limit(self):
        """Test retry logic for rate limit errors."""
        from blog.tasks import _should_retry_linkedin_error
        
        error = LinkedInAPIError("Rate limit exceeded", "RATE_LIMIT", 429)
        self.assertTrue(_should_retry_linkedin_error(error))
    
    def test_should_retry_linkedin_error_auth_error(self):
        """Test retry logic for authentication errors."""
        from blog.tasks import _should_retry_linkedin_error
        
        error = LinkedInAPIError("Unauthorized", "AUTH_ERROR", 401)
        self.assertTrue(_should_retry_linkedin_error(error))
    
    def test_should_retry_linkedin_error_client_error(self):
        """Test no retry for client errors."""
        from blog.tasks import _should_retry_linkedin_error
        
        error = LinkedInAPIError("Bad request", "BAD_REQUEST", 400)
        self.assertFalse(_should_retry_linkedin_error(error))
    
    def test_should_retry_linkedin_error_server_error(self):
        """Test retry for server errors."""
        from blog.tasks import _should_retry_linkedin_error
        
        error = LinkedInAPIError("Internal server error", "SERVER_ERROR", 500)
        self.assertTrue(_should_retry_linkedin_error(error))
    
    def test_calculate_retry_delay(self):
        """Test retry delay calculation with exponential backoff."""
        from blog.tasks import _calculate_retry_delay
        
        # Test first retry (retry_count = 0)
        delay_0 = _calculate_retry_delay(0)
        self.assertGreaterEqual(delay_0, 30)  # Minimum delay
        self.assertLessEqual(delay_0, 120)    # Should be around 60s with jitter
        
        # Test second retry (retry_count = 1)
        delay_1 = _calculate_retry_delay(1)
        self.assertGreaterEqual(delay_1, 60)   # Should be higher than first
        self.assertLessEqual(delay_1, 200)     # Should be around 120s with jitter
        
        # Test third retry (retry_count = 2)
        delay_2 = _calculate_retry_delay(2)
        self.assertGreaterEqual(delay_2, 120)  # Should be higher than second
        self.assertLessEqual(delay_2, 400)     # Should be around 240s with jitter
        
        # Test maximum delay cap
        delay_high = _calculate_retry_delay(10)  # Very high retry count
        self.assertLessEqual(delay_high, 600)   # Should be capped at 10 minutes