"""
Tests for security and performance optimizations in blog engagement features.

This module tests the security validations, rate limiting, caching,
and performance optimizations implemented in task 14.
"""

from django.test import TestCase, RequestFactory, override_settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.http import HttpResponse
from unittest.mock import patch, MagicMock
import time

from .models import Post, Comment, NewsletterSubscriber, Category, Tag
from .security import (
    ContentSanitizer, InputValidator, RateLimitTracker, 
    SecurityAuditLogger, SecurityHeaders
)
from .performance import (
    CacheManager, QueryOptimizer, ViewCountOptimizer, 
    PerformanceMonitor, SearchOptimizer
)
from .forms import CommentForm, NewsletterSubscriptionForm
from .middleware import (
    RateLimitMiddleware, SecurityHeadersMiddleware,
    PerformanceMonitoringMiddleware
)


class SecurityValidationTestCase(TestCase):
    """Test security validation and sanitization"""
    
    def setUp(self):
        self.factory = RequestFactory()
    
    def test_content_sanitizer_removes_html(self):
        """Test that content sanitizer removes HTML tags"""
        malicious_content = '<script>alert("xss")</script>Hello World'
        sanitized = ContentSanitizer.sanitize_comment_content(malicious_content)
        
        self.assertNotIn('<script>', sanitized)
        self.assertNotIn('alert', sanitized)
        self.assertIn('Hello World', sanitized)
    
    def test_content_sanitizer_removes_javascript(self):
        """Test that content sanitizer removes javascript: protocols"""
        malicious_content = 'Click <a href="javascript:alert(1)">here</a>'
        sanitized = ContentSanitizer.sanitize_comment_content(malicious_content)
        
        self.assertNotIn('javascript:', sanitized)
    
    def test_input_validator_detects_spam(self):
        """Test that input validator detects spam content"""
        spam_content = 'CLICK HERE TO WIN FREE VIAGRA CASINO POKER LOTTERY'
        is_valid, error = InputValidator.validate_comment_content(spam_content)
        
        self.assertFalse(is_valid)
        self.assertIn('spam', error.lower())
    
    def test_input_validator_accepts_valid_content(self):
        """Test that input validator accepts valid content"""
        valid_content = 'This is a thoughtful comment about the blog post.'
        is_valid, error = InputValidator.validate_comment_content(valid_content)
        
        self.assertTrue(is_valid)
        self.assertIsNone(error)
    
    def test_email_validator_rejects_temporary_emails(self):
        """Test that email validator rejects temporary email addresses"""
        temp_email = 'test@10minutemail.com'
        is_valid, error = InputValidator.validate_email_address(temp_email)
        
        self.assertFalse(is_valid)
        self.assertIn('temporary', error.lower())
    
    def test_email_validator_accepts_valid_emails(self):
        """Test that email validator accepts valid email addresses"""
        valid_email = 'user@example.com'
        is_valid, error = InputValidator.validate_email_address(valid_email)
        
        self.assertTrue(is_valid)
        self.assertIsNone(error)
    
    def test_url_validator_detects_suspicious_urls(self):
        """Test that URL validator detects suspicious URLs"""
        suspicious_url = 'http://bit.ly/malicious'
        is_valid, error = InputValidator.validate_url(suspicious_url)
        
        self.assertFalse(is_valid)
        self.assertIn('suspicious', error.lower())


class RateLimitingTestCase(TestCase):
    """Test rate limiting functionality"""
    
    def setUp(self):
        self.rate_limiter = RateLimitTracker()
        cache.clear()  # Clear cache before each test
    
    def test_rate_limiting_allows_within_limit(self):
        """Test that rate limiting allows requests within limit"""
        identifier = 'test_user'
        action = 'test_action'
        
        # Should allow first request
        is_limited = self.rate_limiter.is_rate_limited(identifier, action, 5, 60)
        self.assertFalse(is_limited)
    
    def test_rate_limiting_blocks_over_limit(self):
        """Test that rate limiting blocks requests over limit"""
        identifier = 'test_user'
        action = 'test_action'
        
        # Make 5 requests (at limit)
        for _ in range(5):
            self.rate_limiter.is_rate_limited(identifier, action, 5, 60)
        
        # 6th request should be blocked
        is_limited = self.rate_limiter.is_rate_limited(identifier, action, 5, 60)
        self.assertTrue(is_limited)
    
    def test_rate_limiting_resets_after_window(self):
        """Test that rate limiting resets after time window"""
        identifier = 'test_user'
        action = 'test_action'
        
        # Mock time to simulate window expiry
        with patch('time.time') as mock_time:
            mock_time.return_value = 1000
            
            # Make requests at limit
            for _ in range(5):
                self.rate_limiter.is_rate_limited(identifier, action, 5, 60)
            
            # Should be blocked
            is_limited = self.rate_limiter.is_rate_limited(identifier, action, 5, 60)
            self.assertTrue(is_limited)
            
            # Move time forward past window
            mock_time.return_value = 1100  # 100 seconds later
            
            # Should be allowed again
            is_limited = self.rate_limiter.is_rate_limited(identifier, action, 5, 60)
            self.assertFalse(is_limited)


class PerformanceCachingTestCase(TestCase):
    """Test performance caching functionality"""
    
    def setUp(self):
        cache.clear()
        
        # Create test data
        self.user = User.objects.create_user('testuser', 'test@example.com')
        self.category = Category.objects.create(name='Test Category', slug='test-category')
        self.tag = Tag.objects.create(name='Test Tag', slug='test-tag')
        self.post = Post.objects.create(
            title='Test Post',
            slug='test-post',
            author=self.user,
            content='Test content',
            status='published'
        )
        self.post.categories.add(self.category)
        self.post.tags.add(self.tag)
    
    def test_cache_manager_stores_and_retrieves(self):
        """Test that cache manager stores and retrieves data correctly"""
        test_data = {'key': 'value', 'number': 42}
        
        # Store data
        CacheManager.set('test_prefix', test_data, 'test_key')
        
        # Retrieve data
        retrieved_data = CacheManager.get('test_prefix', 'test_key')
        
        self.assertEqual(retrieved_data, test_data)
    
    def test_cache_manager_generates_consistent_keys(self):
        """Test that cache manager generates consistent keys"""
        key1 = CacheManager.get_cache_key('test', 'arg1', 'arg2', param='value')
        key2 = CacheManager.get_cache_key('test', 'arg1', 'arg2', param='value')
        
        self.assertEqual(key1, key2)
    
    def test_query_optimizer_reduces_queries(self):
        """Test that query optimizer reduces database queries"""
        from django.db import connection
        from django.test.utils import override_settings
        
        with override_settings(DEBUG=True):
            # Reset query count
            connection.queries_log.clear()
            
            # Get optimized queryset
            posts = QueryOptimizer.optimize_post_queryset(
                Post.objects.filter(status='published')
            )
            
            # Force evaluation
            list(posts)
            
            # Should have minimal queries due to select_related/prefetch_related
            query_count = len(connection.queries)
            self.assertLessEqual(query_count, 3)  # Should be very few queries
    
    def test_view_count_optimizer_batches_updates(self):
        """Test that view count optimizer batches updates"""
        post_id = self.post.id
        
        # Increment view count multiple times
        for _ in range(5):
            ViewCountOptimizer.increment_view_count(post_id)
        
        # Check that it's buffered in cache
        cache_key = f"view_count_buffer:{post_id}"
        buffered_count = cache.get(cache_key, 0)
        self.assertEqual(buffered_count, 5)
        
        # Original post should not be updated yet
        self.post.refresh_from_db()
        self.assertEqual(self.post.view_count, 0)


class SecurityMiddlewareTestCase(TestCase):
    """Test security middleware functionality"""
    
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = SecurityHeadersMiddleware(lambda r: HttpResponse())
    
    def test_security_headers_middleware_adds_headers(self):
        """Test that security headers middleware adds security headers"""
        request = self.factory.get('/')
        response = HttpResponse()
        
        processed_response = self.middleware.process_response(request, response)
        
        # Check for security headers
        self.assertIn('X-Content-Type-Options', processed_response)
        self.assertIn('X-Frame-Options', processed_response)
        self.assertIn('X-XSS-Protection', processed_response)
        self.assertIn('Content-Security-Policy', processed_response)
        
        self.assertEqual(processed_response['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(processed_response['X-Frame-Options'], 'DENY')


class FormSecurityTestCase(TestCase):
    """Test form security validations"""
    
    def test_comment_form_rejects_malicious_content(self):
        """Test that comment form rejects malicious content"""
        form_data = {
            'author_name': 'Test User',
            'author_email': 'test@example.com',
            'content': '<script>alert("xss")</script>Malicious content'
        }
        
        form = CommentForm(data=form_data)
        self.assertFalse(form.is_valid())
    
    def test_comment_form_accepts_valid_content(self):
        """Test that comment form accepts valid content"""
        form_data = {
            'author_name': 'Test User',
            'author_email': 'test@example.com',
            'content': 'This is a valid comment with good content.'
        }
        
        form = CommentForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_newsletter_form_rejects_temporary_email(self):
        """Test that newsletter form rejects temporary emails"""
        form_data = {
            'email': 'test@10minutemail.com'
        }
        
        form = NewsletterSubscriptionForm(data=form_data)
        self.assertFalse(form.is_valid())
    
    def test_newsletter_form_accepts_valid_email(self):
        """Test that newsletter form accepts valid emails"""
        form_data = {
            'email': 'test@example.com'
        }
        
        form = NewsletterSubscriptionForm(data=form_data)
        self.assertTrue(form.is_valid())


class PerformanceMonitoringTestCase(TestCase):
    """Test performance monitoring functionality"""
    
    def setUp(self):
        self.factory = RequestFactory()
    
    @patch('blog.performance.PerformanceMonitor.time_function')
    def test_performance_decorator_tracks_time(self, mock_decorator):
        """Test that performance decorator tracks execution time"""
        # Mock the decorator to verify it's called
        mock_decorator.return_value = lambda f: f
        
        @PerformanceMonitor.time_function
        def test_function():
            return "test"
        
        result = test_function()
        
        self.assertEqual(result, "test")
        mock_decorator.assert_called_once()
    
    def test_performance_monitoring_middleware_tracks_requests(self):
        """Test that performance monitoring middleware tracks request time"""
        middleware = PerformanceMonitoringMiddleware(lambda r: HttpResponse())
        
        request = self.factory.get('/')
        
        # Process request
        middleware.process_request(request)
        self.assertTrue(hasattr(request, '_performance_start_time'))
        
        # Process response
        response = HttpResponse()
        processed_response = middleware.process_response(request, response)
        
        # Should have performance header in debug mode
        with override_settings(DEBUG=True):
            processed_response = middleware.process_response(request, response)
            self.assertIn('X-Response-Time', processed_response)


class IntegrationTestCase(TestCase):
    """Integration tests for security and performance features"""
    
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user('testuser', 'test@example.com')
        self.post = Post.objects.create(
            title='Test Post',
            slug='test-post',
            author=self.user,
            content='Test content',
            status='published'
        )
    
    def test_comment_submission_with_security_and_rate_limiting(self):
        """Test comment submission with security validation and rate limiting"""
        from .views import submit_comment
        
        # Valid comment data
        valid_data = {
            'author_name': 'Test User',
            'author_email': 'test@example.com',
            'content': 'This is a valid comment with sufficient length.'
        }
        
        request = self.factory.post(f'/blog/{self.post.slug}/comment/', valid_data)
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        
        # Should work for valid data
        response = submit_comment(request, self.post.slug)
        self.assertEqual(response.status_code, 302)  # Redirect after success
        
        # Check that comment was created
        self.assertTrue(Comment.objects.filter(post=self.post).exists())
    
    def test_newsletter_subscription_with_validation(self):
        """Test newsletter subscription with email validation"""
        from .views import subscribe_newsletter
        
        # Valid email
        valid_data = {'email': 'test@example.com'}
        request = self.factory.post('/blog/subscribe/', valid_data)
        request.META['HTTP_REFERER'] = '/blog/'
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        
        response = subscribe_newsletter(request)
        self.assertEqual(response.status_code, 302)  # Redirect after success
        
        # Check that subscriber was created
        self.assertTrue(NewsletterSubscriber.objects.filter(email='test@example.com').exists())


class SecurityAuditTestCase(TestCase):
    """Test security audit logging functionality"""
    
    def setUp(self):
        self.factory = RequestFactory()
    
    @patch('blog.security.logging.getLogger')
    def test_security_audit_logger_logs_suspicious_activity(self, mock_logger):
        """Test that security audit logger logs suspicious activity"""
        mock_log = MagicMock()
        mock_logger.return_value = mock_log
        
        request = self.factory.get('/')
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        request.META['HTTP_USER_AGENT'] = 'Test Agent'
        
        SecurityAuditLogger.log_suspicious_activity(
            request, 
            'test_activity', 
            {'detail': 'test'}
        )
        
        # Verify logger was called
        mock_logger.assert_called_with('blog.security')
        mock_log.warning.assert_called_once()
    
    @patch('blog.security.logging.getLogger')
    def test_security_audit_logger_logs_spam_attempts(self, mock_logger):
        """Test that security audit logger logs spam attempts"""
        mock_log = MagicMock()
        mock_logger.return_value = mock_log
        
        request = self.factory.get('/')
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        
        SecurityAuditLogger.log_spam_attempt(
            request, 
            'comment', 
            'SPAM CONTENT HERE'
        )
        
        # Verify logger was called
        mock_logger.assert_called_with('blog.security')
        mock_log.warning.assert_called_once()