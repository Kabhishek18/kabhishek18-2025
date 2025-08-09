"""
Unit tests for LinkedIn API Service - Task 9 Implementation.

This test suite covers:
- Authentication methods and token management
- Content formatting functions with various input scenarios
- Mock tests for LinkedIn API responses
- Error handling and retry logic

Requirements covered: 1.1, 1.4, 1.5, 3.1, 3.2, 3.3, 3.4, 3.5
"""

import json
import requests
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from django.contrib.auth.models import User

from blog.models import Post, Category, Tag
from blog.linkedin_models import LinkedInConfig, LinkedInPost
from blog.services.linkedin_service import (
    LinkedInAPIService, 
    LinkedInAPIError, 
    LinkedInAuthenticationError,
    LinkedInRateLimitError,
    LinkedInContentError
)
from blog.services.linkedin_content_formatter import LinkedInContentFormatter


class LinkedInAPIServiceAuthenticationTest(TransactionTestCase):
    """Test authentication methods and token management."""
    
    def setUp(self):
        """Set up test data."""
        # Clear any existing configurations
        LinkedInConfig.objects.all().delete()
        
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create LinkedIn configuration with proper validation
        self.config = LinkedInConfig(
            client_id='test_client_id_12345',
            is_active=True
        )
        self.config.set_client_secret('test_client_secret_67890')
        self.config.set_access_token('test_access_token_abcdef')
        self.config.token_expires_at = timezone.now() + timedelta(hours=1)
        self.config.save()
        
        self.service = LinkedInAPIService(self.config)
    
    def test_is_configured_valid_config(self):
        """Test is_configured returns True with valid configuration."""
        self.assertTrue(self.service.is_configured())
    
    def test_is_configured_no_config(self):
        """Test is_configured returns False with no configuration."""
        # Clear all configs and create service with None
        LinkedInConfig.objects.all().delete()
        service = LinkedInAPIService(None)
        self.assertFalse(service.is_configured())
    
    def test_is_configured_inactive_config(self):
        """Test is_configured returns False with inactive configuration."""
        self.config.is_active = False
        self.config.save()
        self.assertFalse(self.service.is_configured())
    
    def test_has_valid_token_valid(self):
        """Test has_valid_token returns True with valid token."""
        self.assertTrue(self.service.has_valid_token())
    
    def test_has_valid_token_expired(self):
        """Test has_valid_token returns False with expired token."""
        self.config.token_expires_at = timezone.now() - timedelta(hours=1)
        self.config.save()
        self.assertFalse(self.service.has_valid_token())
    
    def test_has_valid_token_no_token(self):
        """Test has_valid_token returns False with no token."""
        self.config.set_access_token('')
        self.config.save()
        self.assertFalse(self.service.has_valid_token())
    
    def test_get_authorization_url_basic(self):
        """Test basic authorization URL generation."""
        redirect_uri = 'https://example.com/callback'
        
        url = self.service.get_authorization_url(redirect_uri)
        
        self.assertIn('https://www.linkedin.com/oauth/v2/authorization', url)
        self.assertIn('client_id=test_client_id_12345', url)
        self.assertIn('redirect_uri=https%3A//example.com/callback', url)
        self.assertIn('scope=r_liteprofile%20w_member_social', url)
        self.assertIn('response_type=code', url)
    
    def test_get_authorization_url_with_state(self):
        """Test authorization URL generation with state parameter."""
        redirect_uri = 'https://example.com/callback'
        state = 'csrf_protection_token_123'
        
        url = self.service.get_authorization_url(redirect_uri, state)
        
        self.assertIn('state=csrf_protection_token_123', url)
    
    def test_get_authorization_url_not_configured(self):
        """Test authorization URL generation without configuration."""
        # Clear all configs and create service with None
        LinkedInConfig.objects.all().delete()
        service = LinkedInAPIService(None)
        
        with self.assertRaises(LinkedInAPIError) as context:
            service.get_authorization_url('https://example.com/callback')
        
        self.assertIn('not configured', str(context.exception))
    
    @patch('blog.services.linkedin_service.requests.Session.post')
    def test_exchange_code_for_token_success(self, mock_post):
        """Test successful authorization code exchange."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'access_token': 'new_access_token_xyz',
            'expires_in': 3600,
            'refresh_token': 'new_refresh_token_abc'
        }
        mock_post.return_value = mock_response
        
        result = self.service.exchange_code_for_token(
            'auth_code_123', 
            'https://example.com/callback'
        )
        
        # Verify API call
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        self.assertEqual(call_args[0][0], 'https://www.linkedin.com/oauth/v2/accessToken')
        
        # Verify request data
        request_data = call_args[1]['data']
        self.assertEqual(request_data['grant_type'], 'authorization_code')
        self.assertEqual(request_data['code'], 'auth_code_123')
        self.assertEqual(request_data['redirect_uri'], 'https://example.com/callback')
        self.assertEqual(request_data['client_id'], 'test_client_id_12345')
        self.assertEqual(request_data['client_secret'], 'test_client_secret_67890')
        
        # Verify token storage
        self.config.refresh_from_db()
        self.assertEqual(self.config.get_access_token(), 'new_access_token_xyz')
        self.assertEqual(self.config.get_refresh_token(), 'new_refresh_token_abc')
        self.assertIsNotNone(self.config.token_expires_at)
        
        # Verify return value
        self.assertEqual(result['access_token'], 'new_access_token_xyz')
    
    @patch('blog.services.linkedin_service.requests.Session.post')
    def test_exchange_code_for_token_invalid_code(self, mock_post):
        """Test token exchange with invalid authorization code."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.headers = {'content-type': 'application/json'}
        mock_response.json.return_value = {
            'error': 'invalid_grant',
            'error_description': 'Invalid authorization code'
        }
        mock_post.return_value = mock_response
        
        with self.assertRaises(LinkedInAPIError) as context:
            self.service.exchange_code_for_token(
                'invalid_code', 
                'https://example.com/callback'
            )
        
        self.assertIn('Invalid authorization code', str(context.exception))
        self.assertEqual(context.exception.error_code, 'invalid_grant')
        self.assertEqual(context.exception.status_code, 400)
    
    @patch('blog.services.linkedin_service.requests.Session.post')
    def test_refresh_access_token_success(self, mock_post):
        """Test successful token refresh."""
        # Set up refresh token
        self.config.set_refresh_token('test_refresh_token_original')
        self.config.save()
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'access_token': 'refreshed_access_token_new',
            'expires_in': 7200,
            'refresh_token': 'refreshed_refresh_token_new'
        }
        mock_post.return_value = mock_response
        
        result = self.service.refresh_access_token()
        
        # Verify success
        self.assertTrue(result)
        
        # Verify API call
        call_args = mock_post.call_args
        request_data = call_args[1]['data']
        self.assertEqual(request_data['grant_type'], 'refresh_token')
        self.assertEqual(request_data['refresh_token'], 'test_refresh_token_original')
        
        # Verify token update
        self.config.refresh_from_db()
        self.assertEqual(self.config.get_access_token(), 'refreshed_access_token_new')
        self.assertEqual(self.config.get_refresh_token(), 'refreshed_refresh_token_new')
    
    def test_refresh_access_token_no_refresh_token(self):
        """Test token refresh without refresh token."""
        self.config.set_refresh_token('')
        self.config.save()
        
        with self.assertRaises(LinkedInAPIError) as context:
            self.service.refresh_access_token()
        
        self.assertIn('No refresh token available', str(context.exception))
    
    @patch('blog.services.linkedin_service.LinkedInAPIService.has_valid_token')
    def test_authenticate_with_valid_token(self, mock_has_valid_token):
        """Test authentication with valid token."""
        mock_has_valid_token.return_value = True
        
        result = self.service.authenticate()
        
        self.assertTrue(result)
        mock_has_valid_token.assert_called_once()
    
    @patch('blog.services.linkedin_service.LinkedInAPIService.has_valid_token')
    @patch('blog.services.linkedin_service.LinkedInAPIService.refresh_access_token')
    def test_authenticate_with_expired_token_successful_refresh(self, mock_refresh, mock_has_valid_token):
        """Test authentication with expired token but successful refresh."""
        mock_has_valid_token.return_value = False
        mock_refresh.return_value = True
        
        result = self.service.authenticate()
        
        self.assertTrue(result)
        mock_refresh.assert_called_once()
    
    def test_authenticate_not_configured(self):
        """Test authentication when service is not configured."""
        # Clear all configs and create service with None
        LinkedInConfig.objects.all().delete()
        service = LinkedInAPIService(None)
        
        result = service.authenticate()
        
        self.assertFalse(result)


class LinkedInContentFormattingTest(TransactionTestCase):
    """Test content formatting functions with various input scenarios."""
    
    def setUp(self):
        """Set up test data."""
        # Clear any existing configurations
        LinkedInConfig.objects.all().delete()
        
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create tags for testing
        self.tag1 = Tag.objects.create(name='Python', slug='python')
        self.tag2 = Tag.objects.create(name='Django Framework', slug='django-framework')
        self.tag3 = Tag.objects.create(name='Web Development', slug='web-development')
        
        # Create category
        self.category = Category.objects.create(name='Technology', slug='technology')
        
        # Create test blog post
        self.blog_post = Post.objects.create(
            title='Test Blog Post About Django Development',
            slug='test-blog-post',
            author=self.user,
            content='<p>This is a test blog post content with <strong>HTML tags</strong>.</p>',
            excerpt='This is a test excerpt for the blog post.',
            status='published'
        )
        self.blog_post.tags.add(self.tag1, self.tag2, self.tag3)
        
        # Create LinkedIn configuration
        self.config = LinkedInConfig(
            client_id='test_client_id',
            is_active=True
        )
        self.config.set_client_secret('test_client_secret')
        self.config.set_access_token('test_access_token')
        self.config.token_expires_at = timezone.now() + timedelta(hours=1)
        self.config.save()
        
        self.service = LinkedInAPIService(self.config)
        self.formatter = LinkedInContentFormatter()
    
    def test_format_post_content_basic(self):
        """Test basic post content formatting."""
        title = "Test Blog Post"
        content = "This is the blog post content."
        url = "https://example.com/blog/test-post/"
        
        formatted = self.service._format_post_content(title, content, url)
        
        # The service uses LinkedInContentFormatter which has its own format
        # It should contain the title, content, and URL
        self.assertIn(title, formatted)
        self.assertIn(content, formatted)
        self.assertIn("/blog/test-post/", formatted)  # URL path should be present
    
    def test_format_post_content_empty_content(self):
        """Test formatting with empty content."""
        title = "Test Blog Post"
        content = ""
        url = "https://example.com/blog/test-post/"
        
        formatted = self.service._format_post_content(title, content, url)
        
        expected = "Test Blog Post\n\nRead more: https://example.com/blog/test-post/"
        self.assertEqual(formatted, expected)
    
    def test_format_post_content_long_content(self):
        """Test formatting with content that exceeds limits."""
        title = "Test Blog Post"
        content = "A" * 300  # Long content
        url = "https://example.com/blog/test-post/"
        
        formatted = self.service._format_post_content(title, content, url)
        
        # Should handle long content appropriately
        self.assertIn(title, formatted)
        self.assertIn("/blog/test-post/", formatted)  # URL path should be preserved
        # Content should be truncated if it exceeds formatter limits
        if len(content) > 300:  # LinkedInContentFormatter.MAX_EXCERPT_LENGTH
            self.assertIn("...", formatted)
        else:
            self.assertIn(content[:50], formatted)  # At least part of content should be there
    
    def test_format_post_content_very_long_total(self):
        """Test formatting when total content exceeds LinkedIn limit."""
        title = "A" * 1000
        content = "B" * 2000
        url = "https://example.com/blog/test-post/"
        
        formatted = self.service._format_post_content(title, content, url)
        
        # Should respect 3000 character limit
        self.assertLessEqual(len(formatted), 3000)
        self.assertTrue(formatted.endswith("..."))
        # URL should still be preserved
        self.assertIn("example.com", formatted)
    
    def test_format_post_content_special_characters(self):
        """Test formatting with special characters."""
        title = 'Post with "Quotes" & Special Characters!'
        content = "Content with émojis 🚀 and special chars: @#$%"
        url = "https://example.com/blog/special-post/"
        
        formatted = self.service._format_post_content(title, content, url)
        
        # Should preserve special characters
        self.assertIn('Post with "Quotes" & Special Characters!', formatted)
        self.assertIn("Content with émojis 🚀", formatted)
        self.assertIn("/blog/special-post/", formatted)  # URL path should be present
    
    def test_format_post_content_html_in_content(self):
        """Test formatting with HTML content."""
        title = "HTML Content Test"
        content = "<p>This has <strong>HTML</strong> tags and <a href='#'>links</a>.</p>"
        url = "https://example.com/blog/html-test/"
        
        formatted = self.service._format_post_content(title, content, url)
        
        # HTML should be stripped in the content
        self.assertNotIn("<p>", formatted)
        self.assertNotIn("<strong>", formatted)
        self.assertIn("This has HTML tags", formatted)
    
    def test_create_simplified_content(self):
        """Test simplified content creation for fallback."""
        simplified = self.service._create_simplified_content(self.blog_post)
        
        self.assertIn('title', simplified)
        self.assertIn('content', simplified)
        self.assertIn('url', simplified)
        
        # Title should be truncated if too long
        self.assertLessEqual(len(simplified['title']), 103)  # 100 + "..."
        
        # Content should be simple
        self.assertIn("New blog post:", simplified['content'])
        
        # URL should be valid
        self.assertTrue(simplified['url'].startswith('https://'))
    
    def test_formatter_hashtag_generation(self):
        """Test hashtag generation from blog post tags."""
        hashtags = self.formatter._generate_hashtags(self.blog_post)
        
        # Should contain hashtags for the assigned tags
        self.assertIn('#python', hashtags)
        self.assertIn('#djangoFramework', hashtags)
        self.assertIn('#webDevelopment', hashtags)
        
        # Should not exceed maximum hashtags
        hashtag_count = len(hashtags.split())
        self.assertLessEqual(hashtag_count, self.formatter.MAX_HASHTAGS)
    
    def test_formatter_content_validation(self):
        """Test content validation with various scenarios."""
        # Valid content
        valid_content = "Test Title\n\nTest content\n\nhttps://example.com/blog/test/\n\n#python #django"
        is_valid, errors = self.formatter.validate_content(valid_content)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
        
        # Content too long
        long_content = 'A' * 3500
        is_valid, errors = self.formatter.validate_content(long_content)
        self.assertFalse(is_valid)
        self.assertIn('exceeds LinkedIn limit', errors[0])
        
        # Empty content
        is_valid, errors = self.formatter.validate_content('')
        self.assertFalse(is_valid)
        self.assertIn('cannot be empty', errors[0])
        
        # No URL
        content_no_url = "Test Title\n\nTest content\n\n#python"
        is_valid, errors = self.formatter.validate_content(content_no_url)
        self.assertFalse(is_valid)
        self.assertIn('should include a URL', errors[0])


class LinkedInAPIErrorHandlingTest(TransactionTestCase):
    """Test error handling and retry logic."""
    
    def setUp(self):
        """Set up test data."""
        # Clear any existing configurations
        LinkedInConfig.objects.all().delete()
        
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
            excerpt='Test excerpt',
            status='published'
        )
        
        self.config = LinkedInConfig(
            client_id='test_client_id',
            is_active=True
        )
        self.config.set_client_secret('test_client_secret')
        self.config.set_access_token('test_access_token')
        self.config.token_expires_at = timezone.now() + timedelta(hours=1)
        self.config.save()
        
        self.service = LinkedInAPIService(self.config)
    
    def test_linkedin_api_error_retryable_determination(self):
        """Test LinkedInAPIError retryable logic."""
        # Authentication errors are retryable
        auth_error = LinkedInAPIError("Token expired", status_code=401)
        self.assertTrue(auth_error.is_retryable)
        
        # Rate limit errors are retryable
        rate_error = LinkedInAPIError("Rate limit exceeded", status_code=429)
        self.assertTrue(rate_error.is_retryable)
        
        # Server errors are retryable
        server_error = LinkedInAPIError("Internal server error", status_code=500)
        self.assertTrue(server_error.is_retryable)
        
        # Client errors (except auth and rate limit) are not retryable
        client_error = LinkedInAPIError("Bad request", status_code=400)
        self.assertFalse(client_error.is_retryable)
        
        # Specific retryable error codes
        timeout_error = LinkedInAPIError("Timeout", error_code='TIMEOUT')
        self.assertTrue(timeout_error.is_retryable)
    
    def test_linkedin_authentication_error_needs_reauth(self):
        """Test LinkedInAuthenticationError reauth logic."""
        # Error that needs reauth
        reauth_error = LinkedInAuthenticationError(
            "Invalid token", 
            needs_reauth=True
        )
        self.assertTrue(reauth_error.needs_reauth)
        self.assertFalse(reauth_error.is_retryable)
        
        # Error that doesn't need reauth
        temp_error = LinkedInAuthenticationError(
            "Temporary auth issue", 
            needs_reauth=False
        )
        self.assertFalse(temp_error.needs_reauth)
        self.assertTrue(temp_error.is_retryable)
    
    def test_linkedin_rate_limit_error_properties(self):
        """Test LinkedInRateLimitError properties."""
        rate_error = LinkedInRateLimitError(
            "Daily quota exceeded",
            retry_after=3600,
            quota_type='daily'
        )
        
        self.assertEqual(rate_error.retry_after, 3600)
        self.assertEqual(rate_error.quota_type, 'daily')
        self.assertTrue(rate_error.is_retryable)
        self.assertEqual(rate_error.status_code, 429)
    
    def test_linkedin_content_error_not_retryable(self):
        """Test LinkedInContentError is not retryable."""
        content_error = LinkedInContentError(
            "Content violates policy",
            error_code="CONTENT_VIOLATION"
        )
        
        self.assertFalse(content_error.is_retryable)
        self.assertEqual(content_error.status_code, 400)
        self.assertEqual(content_error.error_code, "CONTENT_VIOLATION")
    
    @patch('blog.services.linkedin_service.requests.Session.request')
    def test_handle_network_timeout_error(self, mock_request):
        """Test handling of network timeout errors."""
        mock_request.side_effect = requests.Timeout("Request timed out")
        
        with patch.object(self.service, 'authenticate', return_value=True):
            with self.assertRaises(LinkedInAPIError) as context:
                self.service._make_authenticated_request('GET', 'https://api.linkedin.com/v2/test')
            
            self.assertTrue(context.exception.is_retryable)
            self.assertEqual(context.exception.error_code, 'TIMEOUT')
            self.assertIn('Request timeout', str(context.exception))
    
    @patch('blog.services.linkedin_service.requests.Session.request')
    def test_handle_connection_error(self, mock_request):
        """Test handling of connection errors."""
        mock_request.side_effect = requests.ConnectionError("Connection refused")
        
        with patch.object(self.service, 'authenticate', return_value=True):
            with self.assertRaises(LinkedInAPIError) as context:
                self.service._make_authenticated_request('GET', 'https://api.linkedin.com/v2/test')
            
            self.assertTrue(context.exception.is_retryable)
            self.assertEqual(context.exception.error_code, 'CONNECTION_ERROR')
            self.assertIn('Connection error', str(context.exception))
    
    def test_quota_limit_checking(self):
        """Test quota limit checking logic."""
        # Test within limits
        self.service._daily_quota_used = 50
        self.service._daily_quota_limit = 100
        
        # Should not raise error
        try:
            self.service._check_quota_limits()
        except LinkedInRateLimitError:
            self.fail("Should not raise error when within limits")
        
        # Test quota exceeded
        self.service._daily_quota_used = 100
        
        with self.assertRaises(LinkedInRateLimitError) as context:
            self.service._check_quota_limits()
        
        self.assertEqual(context.exception.quota_type, 'daily')
        self.assertIn('Daily posting quota exceeded', str(context.exception))


class LinkedInAPIMockResponseTest(TransactionTestCase):
    """Test LinkedIn API responses with comprehensive mocking."""
    
    def setUp(self):
        """Set up test data."""
        # Clear any existing configurations
        LinkedInConfig.objects.all().delete()
        
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
            excerpt='Test excerpt',
            status='published'
        )
        
        self.config = LinkedInConfig(
            client_id='test_client_id',
            is_active=True
        )
        self.config.set_client_secret('test_client_secret')
        self.config.set_access_token('test_access_token')
        self.config.token_expires_at = timezone.now() + timedelta(hours=1)
        self.config.save()
        
        self.service = LinkedInAPIService(self.config)
    
    @patch('blog.services.linkedin_service.LinkedInAPIService.get_user_profile')
    @patch('blog.services.linkedin_service.LinkedInAPIService._make_authenticated_request')
    def test_create_post_success_response(self, mock_request, mock_profile):
        """Test successful post creation with proper API response."""
        # Mock user profile
        mock_profile.return_value = {
            'id': 'test_user_id_12345',
            'localizedFirstName': 'Test',
            'localizedLastName': 'User'
        }
        
        # Mock successful post creation
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            'id': 'urn:li:ugcPost:6789012345678901234'
        }
        mock_request.return_value = mock_response
        
        result = self.service.create_post(
            title="Test Title",
            content="Test content",
            url="https://example.com/post"
        )
        
        # Verify result
        self.assertEqual(result['id'], 'urn:li:ugcPost:6789012345678901234')
        
        # Verify API call structure
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        self.assertEqual(call_args[0][0], 'POST')
        self.assertEqual(call_args[0][1], 'https://api.linkedin.com/v2/ugcPosts')
        
        # Verify post data structure
        post_data = call_args[1]['json']
        self.assertEqual(post_data['author'], 'urn:li:person:test_user_id_12345')
        self.assertEqual(post_data['lifecycleState'], 'PUBLISHED')
        
        # Verify content structure
        share_content = post_data['specificContent']['com.linkedin.ugc.ShareContent']
        self.assertIn('shareCommentary', share_content)
        self.assertIn('shareMediaCategory', share_content)
        self.assertEqual(share_content['shareMediaCategory'], 'ARTICLE')
    
    @patch('blog.services.linkedin_service.LinkedInAPIService._make_authenticated_request')
    def test_get_user_profile_success_response(self, mock_request):
        """Test successful user profile retrieval."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'id': 'test_user_id_12345',
            'localizedFirstName': 'John',
            'localizedLastName': 'Doe',
            'profilePicture': {
                'displayImage': 'urn:li:digitalmediaAsset:C4D03AQHqWAuFvPd-Kg'
            }
        }
        mock_request.return_value = mock_response
        
        profile = self.service.get_user_profile()
        
        # Verify profile data
        self.assertEqual(profile['id'], 'test_user_id_12345')
        self.assertEqual(profile['localizedFirstName'], 'John')
        self.assertEqual(profile['localizedLastName'], 'Doe')
        self.assertIn('profilePicture', profile)
        
        # Verify API call
        mock_request.assert_called_once_with('GET', 'https://api.linkedin.com/v2/people/~')
    
    @patch('blog.services.linkedin_service.LinkedInAPIService.authenticate')
    def test_test_connection_success_response(self, mock_auth):
        """Test successful connection test."""
        mock_auth.return_value = True
        
        with patch.object(self.service, 'get_user_profile') as mock_profile:
            mock_profile.return_value = {
                'localizedFirstName': 'Jane',
                'localizedLastName': 'Smith',
                'id': 'test_user_id'
            }
            
            success, message = self.service.test_connection()
            
            self.assertTrue(success)
            self.assertIn('Successfully connected', message)
            self.assertIn('Jane Smith', message)
    
    @patch('blog.services.linkedin_service.LinkedInAPIService.authenticate')
    def test_test_connection_auth_failure_response(self, mock_auth):
        """Test connection test with authentication failure."""
        mock_auth.return_value = False
        
        success, message = self.service.test_connection()
        
        self.assertFalse(success)
        self.assertIn('Failed to authenticate', message)


if __name__ == '__main__':
    import django
    from django.conf import settings
    from django.test.utils import get_runner
    
    if not settings.configured:
        settings.configure(
            DEBUG=True,
            DATABASES={
                'default': {
                    'ENGINE': 'django.db.backends.sqlite3',
                    'NAME': ':memory:',
                }
            },
            INSTALLED_APPS=[
                'django.contrib.auth',
                'django.contrib.contenttypes',
                'blog',
            ],
            SECRET_KEY='test-secret-key',
        )
    
    django.setup()
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(["__main__"])