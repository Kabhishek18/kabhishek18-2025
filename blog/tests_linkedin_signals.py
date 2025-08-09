"""
Tests for LinkedIn auto-posting signal handlers.

This module tests the signal handler that automatically triggers LinkedIn posting
when a blog post is published.
"""

import logging
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone

from .models import Post, Category, Tag
from .linkedin_models import LinkedInPost, LinkedInConfig
from .signals import post_to_linkedin_on_publish


class LinkedInSignalHandlerTest(TestCase):
    """Test cases for LinkedIn auto-posting signal handler."""
    
    def setUp(self):
        """Set up test data."""
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create test category and tag
        self.category = Category.objects.create(
            name='Test Category',
            slug='test-category'
        )
        
        self.tag = Tag.objects.create(
            name='Test Tag',
            slug='test-tag'
        )
        
        # Create LinkedIn configuration
        self.linkedin_config = LinkedInConfig.objects.create(
            client_id='test_client_id',
            is_active=True
        )
        self.linkedin_config.set_client_secret('test_secret')
        self.linkedin_config.set_access_token('test_token')
        self.linkedin_config.token_expires_at = timezone.now() + timezone.timedelta(hours=1)
        self.linkedin_config.save()
        
        # Disable logging during tests to reduce noise
        logging.disable(logging.CRITICAL)
    
    def tearDown(self):
        """Clean up after tests."""
        logging.disable(logging.NOTSET)
    
    def create_test_post(self, status='draft', title='Test Post'):
        """Helper method to create a test post."""
        post = Post.objects.create(
            title=title,
            slug=f'{title.lower().replace(" ", "-")}-{timezone.now().timestamp()}',
            author=self.user,
            content='Test content for the blog post.',
            excerpt='Test excerpt',
            status=status
        )
        post.categories.add(self.category)
        post.tags.add(self.tag)
        return post
    
    @patch('blog.signals.post_to_linkedin.delay')
    def test_signal_triggers_linkedin_posting_on_publish(self, mock_task):
        """Test that signal triggers LinkedIn posting when post is published."""
        # Create a draft post
        post = self.create_test_post(status='draft')
        
        # Verify task not called for draft
        mock_task.assert_not_called()
        
        # Change status to published
        post.status = 'published'
        post.save()
        
        # Verify task was called
        mock_task.assert_called_once_with(post.id)
    
    @patch('blog.signals.post_to_linkedin.delay')
    def test_signal_skips_non_published_posts(self, mock_task):
        """Test that signal doesn't trigger for non-published posts."""
        # Test different statuses
        statuses = ['draft', 'scheduled', 'archived']
        
        for status in statuses:
            with self.subTest(status=status):
                post = self.create_test_post(status=status, title=f'Test Post {status}')
                mock_task.assert_not_called()
    
    @patch('blog.signals.post_to_linkedin.delay')
    def test_signal_skips_when_linkedin_not_configured(self, mock_task):
        """Test that signal skips posting when LinkedIn is not configured."""
        # Deactivate LinkedIn config
        self.linkedin_config.is_active = False
        self.linkedin_config.save()
        
        # Create published post
        post = self.create_test_post(status='published')
        
        # Verify task was not called
        mock_task.assert_not_called()
    
    @patch('blog.signals.post_to_linkedin.delay')
    def test_signal_skips_when_no_linkedin_config(self, mock_task):
        """Test that signal skips posting when no LinkedIn config exists."""
        # Delete LinkedIn config
        LinkedInConfig.objects.all().delete()
        
        # Create published post
        post = self.create_test_post(status='published')
        
        # Verify task was not called
        mock_task.assert_not_called()
    
    @patch('blog.signals.post_to_linkedin.delay')
    def test_duplicate_posting_prevention_successful_post(self, mock_task):
        """Test that signal prevents duplicate posting for already successful posts."""
        # Create published post
        post = self.create_test_post(status='published')
        
        # Create successful LinkedIn post record
        LinkedInPost.objects.create(
            post=post,
            status='success',
            linkedin_post_id='test_linkedin_id',
            posted_at=timezone.now()
        )
        
        # Save post again (simulating another publish trigger)
        post.save()
        
        # Verify task was not called due to duplicate prevention
        mock_task.assert_not_called()
    
    @patch('blog.signals.post_to_linkedin.delay')
    def test_duplicate_posting_prevention_pending_post(self, mock_task):
        """Test that signal prevents duplicate posting for pending posts."""
        # Create published post
        post = self.create_test_post(status='published')
        
        # Create pending LinkedIn post record
        LinkedInPost.objects.create(
            post=post,
            status='pending'
        )
        
        # Save post again (simulating another publish trigger)
        post.save()
        
        # Verify task was not called due to duplicate prevention
        mock_task.assert_not_called()
    
    @patch('blog.signals.post_to_linkedin.delay')
    def test_allows_retry_for_failed_posts(self, mock_task):
        """Test that signal allows retry for failed posts that can be retried."""
        # Create published post
        post = self.create_test_post(status='published')
        
        # Create failed LinkedIn post record that can be retried
        linkedin_post = LinkedInPost.objects.create(
            post=post,
            status='failed',
            attempt_count=1,  # Less than max_attempts (3)
            error_message='Test error'
        )
        
        # Save post again (simulating retry trigger)
        post.save()
        
        # Verify task was called for retry
        mock_task.assert_called_once_with(post.id)
    
    @patch('blog.signals.post_to_linkedin.delay')
    def test_prevents_retry_for_max_failed_posts(self, mock_task):
        """Test that signal prevents retry for posts that exceeded max attempts."""
        # Create published post
        post = self.create_test_post(status='published')
        
        # Create failed LinkedIn post record that exceeded max attempts
        linkedin_post = LinkedInPost.objects.create(
            post=post,
            status='failed',
            attempt_count=3,  # Equal to max_attempts
            error_message='Test error'
        )
        
        # Save post again (simulating retry trigger)
        post.save()
        
        # Verify task was not called
        mock_task.assert_not_called()
    
    @patch('blog.signals.post_to_linkedin.delay')
    def test_signal_handles_exceptions_gracefully(self, mock_task):
        """Test that signal handles exceptions without breaking post save."""
        # Mock the task to raise an exception
        mock_task.side_effect = Exception('Task queue error')
        
        # Create published post - this should not raise an exception
        try:
            post = self.create_test_post(status='published')
            # If we get here, the exception was handled gracefully
            self.assertTrue(True)
        except Exception:
            self.fail("Signal handler should handle exceptions gracefully")
    
    @patch('blog.signals.post_to_linkedin.delay')
    def test_prevents_recursive_signal_triggering(self, mock_task):
        """Test that signal prevents recursive triggering."""
        # Create published post
        post = self.create_test_post(status='published')
        
        # Simulate the flag being set (as would happen in real scenario)
        post._linkedin_posting_triggered = True
        
        # Save post again
        post.save()
        
        # Verify task was not called due to recursive prevention
        mock_task.assert_not_called()
    
    def test_signal_handler_direct_call(self):
        """Test calling the signal handler directly."""
        # Create published post
        post = self.create_test_post(status='published')
        
        with patch('blog.signals.post_to_linkedin.delay') as mock_task:
            # Call signal handler directly
            post_to_linkedin_on_publish(
                sender=Post,
                instance=post,
                created=False
            )
            
            # Verify task was called
            mock_task.assert_called_once_with(post.id)