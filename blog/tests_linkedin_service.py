"""
Tests for LinkedIn API Service.

Tests cover authentication, token management, post creation,
error handling, and retry logic.
"""

import json
import requests
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth.models import User
# from django.contrib.sites.models import Site  # Not needed for tests

from .models import Post, Category
from .linkedin_models import LinkedInConfig, LinkedInPost
from .services.linkedin_service import LinkedInAPIService, LinkedInAPIError


class LinkedInAPIServiceTestCase(TestCase):
    """Test cases for LinkedInAPIService"""
    
    def setUp(self):
        """Set up test data"""
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create test blog post
        self.category = Category.objects.create(name='Test Category')
        self.blog_post = Post.objects.create(
            title='Test Blog Post',
            slug='test-blog-post',
            author=self.user,
            content='This is a test blog post content.',
            excerpt='This is a test excerpt.',
            status='published'
        )
        
        # Create LinkedIn configuration
        self.config = LinkedInConfig.objects.create(
            client_id='test_client_id',
            is_active=True
        )
        self.config.set_client_secret('test_client_secret')
        self.config.set_access_token('test_access_token')
        self.config.token_expires_at = timezone.now() + timedelta(hours=1)
        self.config.save()
        
        # Initialize service
        self.service = LinkedInAPIService(self.config)
    
    def test_is_configured_with_valid_config(self):
        """Test is_configured returns True with valid configuration"""
        self.assertTrue(self.service.is_configured())
    
    def test_is_configured_with_no_config(self):
        """Test is_configured returns False with no configuration"""
        service = LinkedInAPIService(None)
        self.assertFalse(service.is_configured())
    
    def test_is_configured_with_inactive_config(self):
        """Test is_configured returns False with inactive configuration"""
        self.config.is_active = False
        self.config.save()
        self.assertFalse(self.service.is_configured())
    
    def test_has_valid_token_with_valid_token(self):
        """Test has_valid_token returns True with valid token"""
        self.assertTrue(self.service.has_valid_token())
    
    def test_has_valid_token_with_expired_token(self):
        """Test has_valid_token returns False with expired token"""
        self.config.token_expires_at = timezone.now() - timedelta(hours=1)
        self.config.save()
        self.assertFalse(self.service.has_valid_token())
    
    def test_has_valid_token_with_no_token(self):
        """Test has_valid_token returns False with no token"""
        self.config.set_access_token('')
        self.config.save()
        self.assertFalse(self.service.has_valid_token())
    
    def test_get_authorization_url(self):
        """Test authorization URL generation"""
        redirect_uri = 'https://example.com/callback'
        state = 'test_state'
        
        url = self.service.get_authorization_url(redirect_uri, state)
        
        self.assertIn('https://www.linkedin.com/oauth/v2/authorization', url)
        self.assertIn('client_id=test_client_id', url)
        self.assertIn('redirect_uri=https%3A//example.com/callback', url)
        self.assertIn('state=test_state', url)
        self.assertIn('scope=r_liteprofile%20w_member_social', url)
    
    def test_get_authorization_url_without_config(self):
        """Test authorization URL generation without configuration"""
        service = LinkedInAPIService(None)
        
        with self.assertRaises(LinkedInAPIError) as context:
            service.get_authorization_url('https://example.com/callback')
        
        self.assertIn('not configured', str(context.exception))
    
    @patch('blog.services.linkedin_service.requests.Session.post')
    def test_exchange_code_for_token_success(self, mock_post):
        """Test successful token exchange"""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'access_token': 'new_access_token',
            'expires_in': 3600,
            'refresh_token': 'new_refresh_token'
        }
        mock_post.return_value = mock_response
        
        result = self.service.exchange_code_for_token('test_code', 'https://example.com/callback')
        
        # Verify API call
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        self.assertEqual(call_args[0][0], 'https://www.linkedin.com/oauth/v2/accessToken')
        self.assertIn('authorization_code', call_args[1]['data']['grant_type'])
        
        # Verify token storage
        self.config.refresh_from_db()
        self.assertEqual(self.config.get_access_token(), 'new_access_token')
        self.assertEqual(self.config.get_refresh_token(), 'new_refresh_token')
        self.assertIsNotNone(self.config.token_expires_at)
        
        # Verify return value
        self.assertEqual(result['access_token'], 'new_access_token')
    
    @patch('blog.services.linkedin_service.requests.Session.post')
    def test_exchange_code_for_token_failure(self, mock_post):
        """Test failed token exchange"""
        # Mock error response
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.headers = {'content-type': 'application/json'}
        mock_response.json.return_value = {
            'error': 'invalid_grant',
            'error_description': 'Invalid authorization code'
        }
        mock_post.return_value = mock_response
        
        with self.assertRaises(LinkedInAPIError) as context:
            self.service.exchange_code_for_token('invalid_code', 'https://example.com/callback')
        
        self.assertIn('Invalid authorization code', str(context.exception))
        self.assertEqual(context.exception.error_code, 'invalid_grant')
        self.assertEqual(context.exception.status_code, 400)
    
    @patch('blog.services.linkedin_service.requests.Session.post')
    def test_refresh_access_token_success(self, mock_post):
        """Test successful token refresh"""
        # Set up refresh token
        self.config.set_refresh_token('test_refresh_token')
        self.config.save()
        
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'access_token': 'refreshed_access_token',
            'expires_in': 3600
        }
        mock_post.return_value = mock_response
        
        result = self.service.refresh_access_token()
        
        # Verify success
        self.assertTrue(result)
        
        # Verify token update
        self.config.refresh_from_db()
        self.assertEqual(self.config.get_access_token(), 'refreshed_access_token')
    
    @patch('blog.services.linkedin_service.requests.Session.post')
    def test_refresh_access_token_failure(self, mock_post):
        """Test failed token refresh"""
        # Set up refresh token
        self.config.set_refresh_token('invalid_refresh_token')
        self.config.save()
        
        # Mock error response
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.headers = {'content-type': 'application/json'}
        mock_response.json.return_value = {
            'error': 'invalid_grant',
            'error_description': 'Invalid refresh token'
        }
        mock_post.return_value = mock_response
        
        with self.assertRaises(LinkedInAPIError) as context:
            self.service.refresh_access_token()
        
        self.assertIn('Invalid refresh token', str(context.exception))
    
    def test_refresh_access_token_no_refresh_token(self):
        """Test token refresh without refresh token"""
        # Clear refresh token
        self.config.set_refresh_token('')
        self.config.save()
        
        with self.assertRaises(LinkedInAPIError) as context:
            self.service.refresh_access_token()
        
        self.assertIn('No refresh token available', str(context.exception))
    
    @patch('blog.services.linkedin_service.LinkedInAPIService.has_valid_token')
    def test_authenticate_with_valid_token(self, mock_has_valid_token):
        """Test authentication with valid token"""
        mock_has_valid_token.return_value = True
        
        result = self.service.authenticate()
        
        self.assertTrue(result)
    
    @patch('blog.services.linkedin_service.LinkedInAPIService.has_valid_token')
    @patch('blog.services.linkedin_service.LinkedInAPIService.refresh_access_token')
    def test_authenticate_with_expired_token_successful_refresh(self, mock_refresh, mock_has_valid_token):
        """Test authentication with expired token but successful refresh"""
        mock_has_valid_token.return_value = False
        mock_refresh.return_value = True
        
        result = self.service.authenticate()
        
        self.assertTrue(result)
        mock_refresh.assert_called_once()
    
    @patch('blog.services.linkedin_service.LinkedInAPIService.has_valid_token')
    @patch('blog.services.linkedin_service.LinkedInAPIService.refresh_access_token')
    def test_authenticate_with_failed_refresh(self, mock_refresh, mock_has_valid_token):
        """Test authentication with failed token refresh"""
        mock_has_valid_token.return_value = False
        mock_refresh.side_effect = LinkedInAPIError("Refresh failed")
        
        result = self.service.authenticate()
        
        self.assertFalse(result)
    
    @patch('blog.services.linkedin_service.LinkedInAPIService._make_authenticated_request')
    def test_get_user_profile_success(self, mock_request):
        """Test successful user profile retrieval"""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'id': 'test_user_id',
            'localizedFirstName': 'Test',
            'localizedLastName': 'User'
        }
        mock_request.return_value = mock_response
        
        profile = self.service.get_user_profile()
        
        self.assertEqual(profile['id'], 'test_user_id')
        self.assertEqual(profile['localizedFirstName'], 'Test')
        mock_request.assert_called_once_with('GET', 'https://api.linkedin.com/v2/people/~')
    
    @patch('blog.services.linkedin_service.LinkedInAPIService._make_authenticated_request')
    def test_get_user_profile_failure(self, mock_request):
        """Test failed user profile retrieval"""
        # Mock error response
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.headers = {'content-type': 'application/json'}
        mock_response.json.return_value = {
            'message': 'Insufficient permissions',
            'serviceErrorCode': 100
        }
        mock_request.return_value = mock_response
        
        with self.assertRaises(LinkedInAPIError) as context:
            self.service.get_user_profile()
        
        self.assertIn('Insufficient permissions', str(context.exception))
        self.assertEqual(context.exception.status_code, 403)
    
    def test_format_post_content(self):
        """Test post content formatting"""
        title = "Test Title"
        content = "Test content description"
        url = "https://example.com/post"
        
        formatted = self.service._format_post_content(title, content, url)
        
        expected = "Test Title\n\nTest content description\n\nRead more: https://example.com/post"
        self.assertEqual(formatted, expected)
    
    def test_format_post_content_long_content(self):
        """Test post content formatting with long content"""
        title = "Test Title"
        content = "A" * 300  # Long content
        url = "https://example.com/post"
        
        formatted = self.service._format_post_content(title, content, url)
        
        # Should truncate content
        self.assertIn("...", formatted)
        self.assertLess(len(formatted), 300)
    
    def test_format_post_content_very_long_total(self):
        """Test post content formatting with very long total content"""
        title = "A" * 1000
        content = "B" * 2000
        url = "https://example.com/post"
        
        formatted = self.service._format_post_content(title, content, url)
        
        # Should respect 3000 character limit
        self.assertLessEqual(len(formatted), 3000)
        self.assertTrue(formatted.endswith("..."))
    
    @patch('blog.services.linkedin_service.LinkedInAPIService.get_user_profile')
    @patch('blog.services.linkedin_service.LinkedInAPIService._make_authenticated_request')
    def test_create_post_success(self, mock_request, mock_profile):
        """Test successful post creation"""
        # Mock user profile
        mock_profile.return_value = {'id': 'test_user_id'}
        
        # Mock successful post creation
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            'id': 'urn:li:ugcPost:123456789'
        }
        mock_request.return_value = mock_response
        
        result = self.service.create_post(
            title="Test Title",
            content="Test content",
            url="https://example.com/post"
        )
        
        self.assertEqual(result['id'], 'urn:li:ugcPost:123456789')
        
        # Verify API call
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        self.assertEqual(call_args[0][0], 'POST')
        self.assertEqual(call_args[0][1], 'https://api.linkedin.com/v2/ugcPosts')
        
        # Verify post data structure
        post_data = call_args[1]['json']
        self.assertEqual(post_data['author'], 'urn:li:person:test_user_id')
        self.assertEqual(post_data['lifecycleState'], 'PUBLISHED')
        self.assertIn('shareCommentary', post_data['specificContent']['com.linkedin.ugc.ShareContent'])
    
    @patch('blog.services.linkedin_service.LinkedInAPIService.get_user_profile')
    @patch('blog.services.linkedin_service.LinkedInAPIService._make_authenticated_request')
    def test_create_post_failure(self, mock_request, mock_profile):
        """Test failed post creation"""
        # Mock user profile
        mock_profile.return_value = {'id': 'test_user_id'}
        
        # Mock failed post creation
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.headers = {'content-type': 'application/json'}
        mock_response.json.return_value = {
            'message': 'Invalid post content',
            'serviceErrorCode': 'INVALID_CONTENT'
        }
        mock_request.return_value = mock_response
        
        with self.assertRaises(LinkedInAPIError) as context:
            self.service.create_post(
                title="Test Title",
                content="Test content",
                url="https://example.com/post"
            )
        
        self.assertIn('Invalid post content', str(context.exception))
        self.assertEqual(context.exception.error_code, 'INVALID_CONTENT')
    
    def test_create_post_no_content(self):
        """Test post creation with no title or content"""
        with self.assertRaises(LinkedInAPIError) as context:
            self.service.create_post(title="", content="", url="https://example.com/post")
        
        self.assertIn('Either title or content must be provided', str(context.exception))
    
    @patch('blog.services.linkedin_service.LinkedInAPIService.get_user_profile')
    def test_create_post_profile_failure(self, mock_profile):
        """Test post creation when profile retrieval fails"""
        mock_profile.side_effect = LinkedInAPIError("Profile access failed")
        
        with self.assertRaises(LinkedInAPIError) as context:
            self.service.create_post(
                title="Test Title",
                content="Test content",
                url="https://example.com/post"
            )
        
        self.assertIn('Failed to get user profile', str(context.exception))
    
    @patch('blog.services.linkedin_service.LinkedInAPIService.authenticate')
    def test_test_connection_success(self, mock_auth):
        """Test successful connection test"""
        mock_auth.return_value = True
        
        with patch.object(self.service, 'get_user_profile') as mock_profile:
            mock_profile.return_value = {
                'localizedFirstName': 'Test',
                'localizedLastName': 'User'
            }
            
            success, message = self.service.test_connection()
            
            self.assertTrue(success)
            self.assertIn('Successfully connected', message)
            self.assertIn('Test User', message)
    
    def test_test_connection_not_configured(self):
        """Test connection test when not configured"""
        service = LinkedInAPIService(None)
        
        success, message = self.service.test_connection()
        
        self.assertFalse(success)
        self.assertIn('not configured', message)
    
    @patch('blog.services.linkedin_service.LinkedInAPIService.authenticate')
    def test_test_connection_auth_failure(self, mock_auth):
        """Test connection test with authentication failure"""
        mock_auth.return_value = False
        
        success, message = self.service.test_connection()
        
        self.assertFalse(success)
        self.assertIn('Failed to authenticate', message)
    
    @patch('blog.services.linkedin_service.LinkedInAPIService.create_post')
    def test_post_blog_article_success(self, mock_create_post):
        """Test successful blog article posting"""
        # Mock successful post creation
        mock_create_post.return_value = {
            'id': 'urn:li:ugcPost:123456789'
        }
        
        # Mock get_absolute_url method
        self.blog_post.get_absolute_url = Mock(return_value='/blog/test-blog-post/')
        
        with patch('blog.services.linkedin_service.Site.objects.get_current') as mock_site:
            mock_site.return_value = Mock(domain='example.com')
            result = self.service.post_blog_article(self.blog_post)
        
        # Verify LinkedIn post record
        self.assertIsInstance(result, LinkedInPost)
        self.assertEqual(result.post, self.blog_post)
        self.assertEqual(result.status, 'success')
        self.assertEqual(result.linkedin_post_id, 'urn:li:ugcPost:123456789')
        
        # Verify API call
        mock_create_post.assert_called_once()
        call_args = mock_create_post.call_args
        self.assertEqual(call_args[1]['title'], 'Test Blog Post')
        self.assertEqual(call_args[1]['content'], 'This is a test excerpt.')
        self.assertEqual(call_args[1]['url'], 'https://example.com/blog/test-blog-post/')
    
    @patch('blog.services.linkedin_service.LinkedInAPIService.create_post')
    def test_post_blog_article_failure(self, mock_create_post):
        """Test failed blog article posting"""
        # Mock failed post creation
        mock_create_post.side_effect = LinkedInAPIError(
            "Post creation failed",
            error_code="INVALID_CONTENT",
            status_code=400
        )
        
        # Mock get_absolute_url method
        self.blog_post.get_absolute_url = Mock(return_value='/blog/test-blog-post/')
        
        with patch('blog.services.linkedin_service.Site.objects.get_current') as mock_site:
            mock_site.return_value = Mock(domain='example.com')
            with self.assertRaises(LinkedInAPIError):
                self.service.post_blog_article(self.blog_post)
        
        # Verify LinkedIn post record was created and marked as failed
        linkedin_post = LinkedInPost.objects.get(post=self.blog_post)
        self.assertEqual(linkedin_post.status, 'failed')
        self.assertIn('Post creation failed', linkedin_post.error_message)
        self.assertEqual(linkedin_post.error_code, 'INVALID_CONTENT')
    
    def test_post_blog_article_already_posted(self):
        """Test posting blog article that was already posted"""
        # Create existing successful LinkedIn post
        existing_post = LinkedInPost.objects.create(
            post=self.blog_post,
            status='success',
            linkedin_post_id='existing_post_id'
        )
        
        result = self.service.post_blog_article(self.blog_post)
        
        # Should return existing post without making API call
        self.assertEqual(result, existing_post)
        self.assertEqual(result.linkedin_post_id, 'existing_post_id')
    
    @patch('blog.services.linkedin_service.requests.Session.request')
    def test_make_authenticated_request_rate_limit(self, mock_request):
        """Test handling of rate limit responses"""
        # Mock rate limit response
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {'Retry-After': '120'}
        mock_request.return_value = mock_response
        
        with patch.object(self.service, 'authenticate', return_value=True):
            with self.assertRaises(LinkedInAPIError) as context:
                self.service._make_authenticated_request('GET', 'https://api.linkedin.com/v2/test')
            
            self.assertIn('Rate limit exceeded', str(context.exception))
            self.assertIn('120 seconds', str(context.exception))
            self.assertEqual(context.exception.status_code, 429)
    
    @patch('blog.services.linkedin_service.requests.Session.request')
    def test_make_authenticated_request_network_error(self, mock_request):
        """Test handling of network errors"""
        # Mock network error
        mock_request.side_effect = requests.exceptions.ConnectionError("Network error")
        
        with patch.object(self.service, 'authenticate', return_value=True):
            with self.assertRaises(LinkedInAPIError) as context:
                self.service._make_authenticated_request('GET', 'https://api.linkedin.com/v2/test')
            
            self.assertIn('Network error during API request', str(context.exception))


class LinkedInPostModelTestCase(TestCase):
    """Test cases for LinkedInPost model methods"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.blog_post = Post.objects.create(
            title='Test Blog Post',
            slug='test-blog-post',
            author=self.user,
            content='Test content',
            status='published'
        )
    
    def test_can_retry_with_failed_status(self):
        """Test can_retry with failed status and attempts remaining"""
        linkedin_post = LinkedInPost.objects.create(
            post=self.blog_post,
            status='failed',
            attempt_count=1,
            max_attempts=3
        )
        
        self.assertTrue(linkedin_post.can_retry())
    
    def test_can_retry_max_attempts_reached(self):
        """Test can_retry when max attempts reached"""
        linkedin_post = LinkedInPost.objects.create(
            post=self.blog_post,
            status='failed',
            attempt_count=3,
            max_attempts=3
        )
        
        self.assertFalse(linkedin_post.can_retry())
    
    def test_can_retry_with_success_status(self):
        """Test can_retry with successful status"""
        linkedin_post = LinkedInPost.objects.create(
            post=self.blog_post,
            status='success',
            attempt_count=1,
            max_attempts=3
        )
        
        self.assertFalse(linkedin_post.can_retry())
    
    def test_should_retry_now_with_no_retry_time(self):
        """Test should_retry_now when no retry time is set"""
        linkedin_post = LinkedInPost.objects.create(
            post=self.blog_post,
            status='retrying',
            attempt_count=1,
            max_attempts=3
        )
        
        self.assertTrue(linkedin_post.should_retry_now())
    
    def test_should_retry_now_with_future_retry_time(self):
        """Test should_retry_now with future retry time"""
        linkedin_post = LinkedInPost.objects.create(
            post=self.blog_post,
            status='retrying',
            attempt_count=1,
            max_attempts=3,
            next_retry_at=timezone.now() + timedelta(minutes=10)
        )
        
        self.assertFalse(linkedin_post.should_retry_now())
    
    def test_should_retry_now_with_past_retry_time(self):
        """Test should_retry_now with past retry time"""
        linkedin_post = LinkedInPost.objects.create(
            post=self.blog_post,
            status='retrying',
            attempt_count=1,
            max_attempts=3,
            next_retry_at=timezone.now() - timedelta(minutes=10)
        )
        
        self.assertTrue(linkedin_post.should_retry_now())
    
    def test_mark_as_failed_with_retry(self):
        """Test mark_as_failed when retries are allowed"""
        linkedin_post = LinkedInPost.objects.create(
            post=self.blog_post,
            status='pending',
            attempt_count=0,
            max_attempts=3
        )
        
        linkedin_post.mark_as_failed("Test error", "TEST_ERROR", can_retry=True)
        
        self.assertEqual(linkedin_post.status, 'retrying')
        self.assertEqual(linkedin_post.attempt_count, 1)
        self.assertEqual(linkedin_post.error_message, "Test error")
        self.assertEqual(linkedin_post.error_code, "TEST_ERROR")
        self.assertIsNotNone(linkedin_post.next_retry_at)
    
    def test_mark_as_failed_no_retry(self):
        """Test mark_as_failed when retries are not allowed"""
        linkedin_post = LinkedInPost.objects.create(
            post=self.blog_post,
            status='pending',
            attempt_count=0,
            max_attempts=3
        )
        
        linkedin_post.mark_as_failed("Test error", "TEST_ERROR", can_retry=False)
        
        self.assertEqual(linkedin_post.status, 'failed')
        self.assertEqual(linkedin_post.attempt_count, 1)
        self.assertIsNone(linkedin_post.next_retry_at)
    
    def test_mark_as_failed_max_attempts_reached(self):
        """Test mark_as_failed when max attempts are reached"""
        linkedin_post = LinkedInPost.objects.create(
            post=self.blog_post,
            status='retrying',
            attempt_count=2,
            max_attempts=3
        )
        
        linkedin_post.mark_as_failed("Test error", "TEST_ERROR", can_retry=True)
        
        self.assertEqual(linkedin_post.status, 'failed')
        self.assertEqual(linkedin_post.attempt_count, 3)
        self.assertIsNone(linkedin_post.next_retry_at)
    
    def test_mark_as_success(self):
        """Test mark_as_success method"""
        linkedin_post = LinkedInPost.objects.create(
            post=self.blog_post,
            status='pending'
        )
        
        linkedin_post.mark_as_success(
            'urn:li:ugcPost:123456789',
            'https://www.linkedin.com/feed/update/urn:li:ugcPost:123456789/'
        )
        
        self.assertEqual(linkedin_post.status, 'success')
        self.assertEqual(linkedin_post.linkedin_post_id, 'urn:li:ugcPost:123456789')
        self.assertEqual(linkedin_post.linkedin_post_url, 'https://www.linkedin.com/feed/update/urn:li:ugcPost:123456789/')
        self.assertIsNotNone(linkedin_post.posted_at)
        self.assertEqual(linkedin_post.error_message, '')
        self.assertEqual(linkedin_post.error_code, '')
    
    def test_get_posts_ready_for_retry(self):
        """Test get_posts_ready_for_retry class method"""
        # Create posts with different retry states
        ready_post = LinkedInPost.objects.create(
            post=self.blog_post,
            status='retrying',
            next_retry_at=timezone.now() - timedelta(minutes=5)
        )
        
        not_ready_post = LinkedInPost.objects.create(
            post=Post.objects.create(
                title='Another Post',
                slug='another-post',
                author=self.user,
                content='Content',
                status='published'
            ),
            status='retrying',
            next_retry_at=timezone.now() + timedelta(minutes=5)
        )
        
        ready_posts = LinkedInPost.get_posts_ready_for_retry()
        
        self.assertIn(ready_post, ready_posts)
        self.assertNotIn(not_ready_post, ready_posts)