"""
LinkedIn API Service for automatic posting of blog content to LinkedIn.

This service handles:
- OAuth 2.0 authentication and token management
- Creating LinkedIn posts via API v2
- Error handling and retry logic
- Content formatting for LinkedIn posts
"""

import requests
import logging
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from django.utils import timezone
from django.conf import settings
from django.urls import reverse
from ..linkedin_models import LinkedInConfig, LinkedInPost
from .linkedin_error_logger import LinkedInErrorLogger


logger = logging.getLogger(__name__)


class LinkedInAPIError(Exception):
    """Custom exception for LinkedIn API errors"""
    def __init__(self, message: str, error_code: str = None, status_code: int = None, 
                 is_retryable: bool = None, retry_after: int = None):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.is_retryable = is_retryable if is_retryable is not None else self._determine_retryable()
        self.retry_after = retry_after
        super().__init__(self.message)
    
    def _determine_retryable(self) -> bool:
        """Determine if error is retryable based on status code and error code"""
        # Authentication errors that might be temporary (token expiration)
        if self.status_code == 401:
            return True
        
        # Rate limiting is retryable
        if self.status_code == 429:
            return True
        
        # Server errors are retryable
        if self.status_code and self.status_code >= 500:
            return True
        
        # Client errors (except auth and rate limit) are not retryable
        if self.status_code and 400 <= self.status_code < 500:
            return False
        
        # Specific error codes that are retryable
        retryable_codes = [
            'RATE_LIMIT_EXCEEDED',
            'INTERNAL_SERVER_ERROR',
            'SERVICE_UNAVAILABLE',
            'TIMEOUT',
            'TOKEN_EXPIRED'
        ]
        
        if self.error_code in retryable_codes:
            return True
        
        # Default to not retryable for unknown errors
        return False


class LinkedInAuthenticationError(LinkedInAPIError):
    """Specific exception for authentication failures"""
    def __init__(self, message: str, error_code: str = None, needs_reauth: bool = False):
        super().__init__(message, error_code, status_code=401, is_retryable=not needs_reauth)
        self.needs_reauth = needs_reauth


class LinkedInRateLimitError(LinkedInAPIError):
    """Specific exception for rate limiting"""
    def __init__(self, message: str, retry_after: int = None, quota_type: str = None):
        super().__init__(message, error_code='RATE_LIMIT_EXCEEDED', status_code=429, 
                        is_retryable=True, retry_after=retry_after)
        self.quota_type = quota_type


class LinkedInContentError(LinkedInAPIError):
    """Specific exception for content validation errors"""
    def __init__(self, message: str, error_code: str = None):
        super().__init__(message, error_code, status_code=400, is_retryable=False)


class LinkedInAPIService:
    """
    Service class for interacting with LinkedIn API v2.
    Handles authentication, token management, and post creation.
    """
    
    # LinkedIn API endpoints
    BASE_URL = "https://api.linkedin.com/v2"
    AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
    TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
    
    # API endpoints
    PROFILE_URL = f"{BASE_URL}/people/~"
    UGC_POSTS_URL = f"{BASE_URL}/ugcPosts"
    ASSETS_URL = f"{BASE_URL}/assets"
    IMAGES_URL = f"{BASE_URL}/images"
    
    # Required scopes for posting
    REQUIRED_SCOPES = ["r_liteprofile", "w_member_social"]
    
    def __init__(self, config: LinkedInConfig = None):
        """
        Initialize the LinkedIn API service.
        
        Args:
            config: LinkedInConfig instance. If None, will try to get active config.
        """
        self.config = config or LinkedInConfig.get_active_config()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Django-Blog-LinkedIn-Integration/1.0',
            'Content-Type': 'application/json',
        })
        
        # Rate limiting tracking
        self._rate_limit_reset_time = None
        self._daily_quota_used = 0
        self._daily_quota_limit = 100  # LinkedIn's daily posting limit
        self._last_quota_reset = None
        
        # Media upload tracking
        self._media_quota_used = 0
        self._media_quota_limit = 50  # LinkedIn's daily media upload limit
        self._media_quota_reset = None
        
        # Error logging
        self.error_logger = LinkedInErrorLogger()
    
    def is_configured(self) -> bool:
        """Check if LinkedIn integration is properly configured."""
        return (
            self.config is not None and 
            self.config.is_active and 
            self.config.client_id and 
            self.config.get_client_secret()
        )
    
    def _handle_authentication_error(self, response: requests.Response, context: str = "") -> None:
        """
        Handle authentication errors with specific error handling.
        
        Args:
            response: HTTP response object
            context: Context where the error occurred
            
        Raises:
            LinkedInAuthenticationError: With specific authentication error details
        """
        try:
            error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
        except ValueError:
            error_data = {}
        
        error_message = error_data.get('error_description', error_data.get('message', f'HTTP {response.status_code}'))
        error_code = error_data.get('error', error_data.get('serviceErrorCode'))
        
        # Determine if re-authentication is needed
        needs_reauth = False
        if any(term in error_message.lower() for term in ['invalid_token', 'expired_token', 'token_expired']):
            needs_reauth = True
            logger.error(f"LinkedIn authentication failed - token expired or invalid: {error_message}")
        elif any(term in error_message.lower() for term in ['invalid_client', 'unauthorized_client']):
            needs_reauth = True
            logger.error(f"LinkedIn authentication failed - client credentials invalid: {error_message}")
        elif response.status_code == 403:
            logger.error(f"LinkedIn authentication failed - insufficient permissions: {error_message}")
        else:
            logger.error(f"LinkedIn authentication failed in {context}: {error_message}")
        
        # Log the authentication error
        self.error_logger.log_authentication_error(
            error_details={
                'message': error_message,
                'error_code': error_code,
                'status_code': response.status_code,
                'needs_reauth': needs_reauth
            },
            context={'operation': context} if context else None
        )
        
        # Clear tokens if re-authentication is needed
        if needs_reauth and self.config:
            logger.warning("Clearing LinkedIn tokens due to authentication failure")
            self.config.clear_tokens()
        
        raise LinkedInAuthenticationError(
            f"Authentication failed{' in ' + context if context else ''}: {error_message}",
            error_code=error_code,
            needs_reauth=needs_reauth
        )
    
    def _handle_rate_limit_error(self, response: requests.Response) -> None:
        """
        Handle rate limiting errors with quota management.
        
        Args:
            response: HTTP response object
            
        Raises:
            LinkedInRateLimitError: With rate limit details
        """
        retry_after = response.headers.get('Retry-After', '3600')  # Default to 1 hour
        try:
            retry_after_seconds = int(retry_after)
        except ValueError:
            retry_after_seconds = 3600
        
        # Update rate limit tracking
        self._rate_limit_reset_time = timezone.now() + timedelta(seconds=retry_after_seconds)
        
        try:
            error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
        except ValueError:
            error_data = {}
        
        error_message = error_data.get('message', f'Rate limit exceeded. Retry after {retry_after} seconds')
        quota_type = 'daily' if 'daily' in error_message.lower() else 'hourly'
        
        logger.warning(f"LinkedIn rate limit exceeded - {quota_type} quota. Retry after {retry_after_seconds} seconds")
        
        # Log the rate limit error
        self.error_logger.log_rate_limit_error(
            error_details={
                'message': error_message,
                'retry_after': retry_after_seconds,
                'quota_type': quota_type,
                'status_code': response.status_code
            }
        )
        
        # Update quota tracking
        if quota_type == 'daily':
            self._daily_quota_used = self._daily_quota_limit
            self._last_quota_reset = timezone.now()
        
        raise LinkedInRateLimitError(
            error_message,
            retry_after=retry_after_seconds,
            quota_type=quota_type
        )
    
    def _handle_content_error(self, response: requests.Response, content_data: dict = None) -> None:
        """
        Handle content validation errors.
        
        Args:
            response: HTTP response object
            content_data: The content that was being posted
            
        Raises:
            LinkedInContentError: With content error details
        """
        try:
            error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
        except ValueError:
            error_data = {}
        
        error_message = error_data.get('message', f'Content validation failed: HTTP {response.status_code}')
        error_code = error_data.get('serviceErrorCode')
        
        # Log the content error
        self.error_logger.log_content_error(
            error_details={
                'message': error_message,
                'error_code': error_code,
                'status_code': response.status_code
            },
            content_data=content_data
        )
        
        raise LinkedInContentError(error_message, error_code=error_code)
    
    def _handle_server_error(self, response: requests.Response, context: str = "") -> None:
        """
        Handle server errors with appropriate logging.
        
        Args:
            response: HTTP response object
            context: Context where the error occurred
            
        Raises:
            LinkedInAPIError: With server error details
        """
        try:
            error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
        except ValueError:
            error_data = {}
        
        error_message = error_data.get('message', f'LinkedIn server error: HTTP {response.status_code}')
        error_code = error_data.get('serviceErrorCode')
        
        # Log the server error
        self.error_logger.log_server_error(
            error_details={
                'message': error_message,
                'error_code': error_code,
                'status_code': response.status_code
            },
            context={'operation': context} if context else None
        )
        
        raise LinkedInAPIError(
            f"Server error{' in ' + context if context else ''}: {error_message}",
            error_code=error_code,
            status_code=response.status_code,
            is_retryable=True
        )
    
    def _check_quota_limits(self) -> None:
        """
        Check if we're within quota limits before making requests.
        
        Raises:
            LinkedInRateLimitError: If quota limits are exceeded
        """
        now = timezone.now()
        
        # Reset daily quota if it's a new day
        if self._last_quota_reset and (now - self._last_quota_reset).days >= 1:
            self._daily_quota_used = 0
            self._last_quota_reset = now
        
        # Check if we're still rate limited
        if self._rate_limit_reset_time and now < self._rate_limit_reset_time:
            remaining_seconds = int((self._rate_limit_reset_time - now).total_seconds())
            raise LinkedInRateLimitError(
                f"Still rate limited. Retry after {remaining_seconds} seconds",
                retry_after=remaining_seconds
            )
        
        # Check daily quota
        if self._daily_quota_used >= self._daily_quota_limit:
            logger.warning(f"LinkedIn daily quota limit reached: {self._daily_quota_used}/{self._daily_quota_limit}")
            raise LinkedInRateLimitError(
                f"Daily posting quota exceeded: {self._daily_quota_used}/{self._daily_quota_limit}",
                quota_type='daily'
            )
    
    def _update_quota_usage(self) -> None:
        """Update quota usage after successful request."""
        self._daily_quota_used += 1
        if not self._last_quota_reset:
            self._last_quota_reset = timezone.now()
        
        logger.debug(f"LinkedIn quota usage updated: {self._daily_quota_used}/{self._daily_quota_limit}")
    
    def _implement_fallback_mechanism(self, error: LinkedInAPIError, blog_post, attempt_count: int = 1) -> dict:
        """
        Implement enhanced fallback mechanisms for posting failures, including image-related fallbacks.
        
        Args:
            error: The LinkedIn API error that occurred
            blog_post: The blog post that failed to post
            attempt_count: Current attempt number
            
        Returns:
            dict: Fallback result information
        """
        fallback_result = {
            'fallback_used': True,
            'original_error': str(error),
            'fallback_type': None,
            'fallback_success': False,
            'fallback_message': None
        }
        
        # Fallback 1: Text-only posting for image-related failures
        # This is a new fallback specifically for image processing failures
        if 'image' in str(error).lower() or 'media' in str(error).lower():
            try:
                logger.info(f"Attempting text-only fallback for image-related error on post: {blog_post.title}")
                
                # Get simplified content without image optimization
                from .linkedin_content_formatter import LinkedInContentFormatter
                formatter = LinkedInContentFormatter()
                text_only_content = formatter.format_post_content(blog_post, include_excerpt=True, optimize_for_images=False)
                
                # Build URL
                try:
                    from django.contrib.sites.models import Site
                    current_site = Site.objects.get_current()
                    blog_url = f"https://{current_site.domain}{blog_post.get_absolute_url()}"
                except:
                    blog_url = f"https://localhost{blog_post.get_absolute_url()}"
                
                # Attempt posting without image
                response_data = self.create_post(
                    title=blog_post.title,
                    content=blog_post.excerpt or blog_post.content[:300],
                    url=blog_url,
                    image_url=None  # Explicitly no image
                )
                
                fallback_result.update({
                    'fallback_type': 'text_only_posting',
                    'fallback_success': True,
                    'fallback_message': 'Successfully posted as text-only after image failure',
                    'linkedin_post_id': response_data.get('id')
                })
                
                # Log successful fallback
                self.error_logger.log_fallback_attempt(
                    original_error={'message': str(error), 'error_code': getattr(error, 'error_code', None)},
                    fallback_type='text_only_posting',
                    fallback_result=fallback_result,
                    context={'post_title': blog_post.title, 'original_had_image': True}
                )
                
                logger.info(f"Text-only fallback successful for post: {blog_post.title}")
                return fallback_result
                
            except Exception as fallback_error:
                fallback_result['fallback_message'] = f"Text-only fallback failed: {fallback_error}"
                logger.error(f"Text-only fallback failed: {fallback_error}")
        
        # Fallback 2: Content modification for content errors
        elif isinstance(error, LinkedInContentError):
            try:
                logger.info(f"Attempting content modification fallback for post: {blog_post.title}")
                
                # Try with simplified content (no image)
                simplified_content = self._create_simplified_content(blog_post)
                
                # Attempt posting with simplified content
                response_data = self.create_post(
                    title=simplified_content['title'],
                    content=simplified_content['content'],
                    url=simplified_content['url'],
                    image_url=None  # Ensure no image for fallback
                )
                
                fallback_result.update({
                    'fallback_type': 'content_simplification',
                    'fallback_success': True,
                    'fallback_message': 'Successfully posted with simplified content (text-only)',
                    'linkedin_post_id': response_data.get('id')
                })
                
                # Log successful fallback
                self.error_logger.log_fallback_attempt(
                    original_error={'message': str(error), 'error_code': getattr(error, 'error_code', None)},
                    fallback_type='content_simplification',
                    fallback_result=fallback_result,
                    context={'post_title': blog_post.title}
                )
                
                logger.info(f"Content simplification fallback successful for post: {blog_post.title}")
                return fallback_result
                
            except Exception as fallback_error:
                fallback_result['fallback_message'] = f"Content simplification failed: {fallback_error}"
                
                # Log failed fallback
                self.error_logger.log_fallback_attempt(
                    original_error={'message': str(error), 'error_code': getattr(error, 'error_code', None)},
                    fallback_type='content_simplification',
                    fallback_result=fallback_result,
                    context={'post_title': blog_post.title}
                )
                
                logger.error(f"Content simplification fallback failed: {fallback_error}")
        
        # Fallback 3: Delayed retry for rate limiting
        elif isinstance(error, LinkedInRateLimitError):
            fallback_result.update({
                'fallback_type': 'delayed_retry',
                'fallback_message': f"Scheduled for retry after {error.retry_after} seconds",
                'retry_after': error.retry_after
            })
            
            logger.info(f"Delayed retry fallback scheduled for post: {blog_post.title}")
        
        # Fallback 4: Alternative posting strategy for authentication errors
        elif isinstance(error, LinkedInAuthenticationError) and not error.needs_reauth:
            fallback_result.update({
                'fallback_type': 'auth_retry',
                'fallback_message': 'Scheduled for retry after token refresh attempt'
            })
            
            logger.info(f"Authentication retry fallback scheduled for post: {blog_post.title}")
        
        # Fallback 5: Manual intervention notification for critical errors
        else:
            fallback_result.update({
                'fallback_type': 'manual_intervention',
                'fallback_message': 'Manual intervention required - admin notification sent'
            })
            
            # Log for manual intervention
            logger.critical(
                f"LinkedIn posting requires manual intervention for post '{blog_post.title}': "
                f"{error.message} (Error Code: {error.error_code})"
            )
        
        return fallback_result
    
    def _create_simplified_content(self, blog_post) -> dict:
        """
        Create simplified content for fallback posting.
        
        Args:
            blog_post: Blog post instance
            
        Returns:
            dict: Simplified content data
        """
        from django.contrib.sites.models import Site
        
        # Create very basic content
        title = blog_post.title[:100] + '...' if len(blog_post.title) > 100 else blog_post.title
        content = f"New blog post: {title}"
        
        # Build URL
        try:
            current_site = Site.objects.get_current()
            url = f"https://{current_site.domain}{blog_post.get_absolute_url()}"
        except:
            url = f"https://localhost{blog_post.get_absolute_url()}"
        
        return {
            'title': title,
            'content': content,
            'url': url
        }
    
    def has_valid_token(self) -> bool:
        """Check if we have a valid access token."""
        if not self.is_configured():
            return False
        
        return (
            self.config.get_access_token() and 
            not self.config.is_token_expired()
        )
    
    def get_authorization_url(self, redirect_uri: str, state: str = None) -> str:
        """
        Generate LinkedIn OAuth authorization URL.
        
        Args:
            redirect_uri: URL to redirect to after authorization
            state: Optional state parameter for CSRF protection
            
        Returns:
            Authorization URL string
        """
        if not self.is_configured():
            raise LinkedInAPIError("LinkedIn integration is not configured")
        
        params = {
            'response_type': 'code',
            'client_id': self.config.client_id,
            'redirect_uri': redirect_uri,
            'scope': ' '.join(self.REQUIRED_SCOPES),
        }
        
        if state:
            params['state'] = state
        
        # Build URL manually to ensure proper encoding
        param_string = '&'.join([f"{k}={requests.utils.quote(str(v))}" for k, v in params.items()])
        return f"{self.AUTH_URL}?{param_string}"
    
    def exchange_code_for_token(self, code: str, redirect_uri: str) -> Dict:
        """
        Exchange authorization code for access token.
        
        Args:
            code: Authorization code from LinkedIn
            redirect_uri: Same redirect URI used in authorization
            
        Returns:
            Token response dictionary
            
        Raises:
            LinkedInAPIError: If token exchange fails
        """
        if not self.is_configured():
            raise LinkedInAPIError("LinkedIn integration is not configured")
        
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': redirect_uri,
            'client_id': self.config.client_id,
            'client_secret': self.config.get_client_secret(),
        }
        
        try:
            response = self.session.post(
                self.TOKEN_URL,
                data=data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=30
            )
            
            if response.status_code != 200:
                error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                error_msg = error_data.get('error_description', f'HTTP {response.status_code}')
                raise LinkedInAPIError(
                    f"Token exchange failed: {error_msg}",
                    error_code=error_data.get('error'),
                    status_code=response.status_code
                )
            
            token_data = response.json()
            
            # Store the tokens in config
            self.config.set_access_token(token_data['access_token'])
            
            # Calculate expiration time
            expires_in = token_data.get('expires_in', 3600)  # Default to 1 hour
            self.config.token_expires_at = timezone.now() + timedelta(seconds=expires_in)
            
            # Store refresh token if provided
            if 'refresh_token' in token_data:
                self.config.set_refresh_token(token_data['refresh_token'])
            
            self.config.save()
            
            logger.info("Successfully exchanged authorization code for access token")
            return token_data
            
        except requests.RequestException as e:
            logger.error(f"Network error during token exchange: {e}")
            raise LinkedInAPIError(f"Network error during token exchange: {e}")
    
    def refresh_access_token(self) -> bool:
        """
        Refresh the access token using refresh token.
        
        Returns:
            True if refresh was successful, False otherwise
            
        Raises:
            LinkedInAPIError: If refresh fails
        """
        if not self.is_configured():
            raise LinkedInAPIError("LinkedIn integration is not configured")
        
        refresh_token = self.config.get_refresh_token()
        if not refresh_token:
            raise LinkedInAPIError("No refresh token available")
        
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
            'client_id': self.config.client_id,
            'client_secret': self.config.get_client_secret(),
        }
        
        try:
            response = self.session.post(
                self.TOKEN_URL,
                data=data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=30
            )
            
            if response.status_code != 200:
                error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                error_msg = error_data.get('error_description', f'HTTP {response.status_code}')
                logger.error(f"Token refresh failed: {error_msg}")
                raise LinkedInAPIError(
                    f"Token refresh failed: {error_msg}",
                    error_code=error_data.get('error'),
                    status_code=response.status_code
                )
            
            token_data = response.json()
            
            # Update tokens
            self.config.set_access_token(token_data['access_token'])
            
            # Update expiration time
            expires_in = token_data.get('expires_in', 3600)
            self.config.token_expires_at = timezone.now() + timedelta(seconds=expires_in)
            
            # Update refresh token if provided
            if 'refresh_token' in token_data:
                self.config.set_refresh_token(token_data['refresh_token'])
            
            self.config.save()
            
            logger.info("Successfully refreshed access token")
            return True
            
        except requests.RequestException as e:
            logger.error(f"Network error during token refresh: {e}")
            raise LinkedInAPIError(f"Network error during token refresh: {e}")
    
    def authenticate(self) -> bool:
        """
        Ensure we have a valid access token.
        
        Returns:
            True if authentication is successful, False otherwise
        """
        if not self.is_configured():
            logger.warning("LinkedIn integration is not configured")
            return False
        
        # If we have a valid token, we're good
        if self.has_valid_token():
            return True
        
        # Try to refresh the token
        try:
            return self.refresh_access_token()
        except LinkedInAPIError as e:
            logger.error(f"Authentication failed: {e.message}")
            return False
    
    def _make_authenticated_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """
        Make an authenticated request to LinkedIn API with comprehensive error handling.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: API endpoint URL
            **kwargs: Additional arguments for requests
            
        Returns:
            Response object
            
        Raises:
            LinkedInAPIError: If authentication fails or request fails
        """
        # Check quota limits before making request
        self._check_quota_limits()
        
        if not self.authenticate():
            raise LinkedInAuthenticationError("Failed to authenticate with LinkedIn API")
        
        # Add authorization header
        headers = kwargs.get('headers', {})
        headers['Authorization'] = f"Bearer {self.config.get_access_token()}"
        kwargs['headers'] = headers
        
        # Set timeout if not provided
        kwargs.setdefault('timeout', 30)
        
        try:
            logger.debug(f"Making LinkedIn API request: {method} {url}")
            response = self.session.request(method, url, **kwargs)
            
            # Handle different error types with specific error handling
            if response.status_code == 401:
                self._handle_authentication_error(response, f"{method} {url}")
            elif response.status_code == 429:
                self._handle_rate_limit_error(response)
            elif response.status_code == 400:
                self._handle_content_error(response, kwargs.get('json'))
            elif response.status_code >= 500:
                self._handle_server_error(response, f"{method} {url}")
            elif response.status_code >= 400:
                # Other client errors
                try:
                    error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                except ValueError:
                    error_data = {}
                
                error_message = error_data.get('message', f'Client error: HTTP {response.status_code}')
                error_code = error_data.get('serviceErrorCode')
                
                logger.error(f"LinkedIn API client error: {error_message}")
                raise LinkedInAPIError(
                    f"Client error: {error_message}",
                    error_code=error_code,
                    status_code=response.status_code,
                    is_retryable=False
                )
            
            # Update quota usage for successful requests
            if response.status_code in [200, 201]:
                self._update_quota_usage()
            
            logger.debug(f"LinkedIn API request successful: {method} {url} -> {response.status_code}")
            return response
            
        except (LinkedInAPIError, LinkedInAuthenticationError, LinkedInRateLimitError, LinkedInContentError):
            # Re-raise our custom exceptions
            raise
        except requests.Timeout as e:
            self.error_logger.log_network_error(
                error_details={
                    'message': f"Request timeout: {e}",
                    'error_code': 'TIMEOUT'
                },
                context={'method': method, 'url': url}
            )
            raise LinkedInAPIError(
                f"Request timeout: {e}",
                error_code='TIMEOUT',
                is_retryable=True
            )
        except requests.ConnectionError as e:
            self.error_logger.log_network_error(
                error_details={
                    'message': f"Connection error: {e}",
                    'error_code': 'CONNECTION_ERROR'
                },
                context={'method': method, 'url': url}
            )
            raise LinkedInAPIError(
                f"Connection error: {e}",
                error_code='CONNECTION_ERROR',
                is_retryable=True
            )
        except requests.RequestException as e:
            self.error_logger.log_network_error(
                error_details={
                    'message': f"Network error during API request: {e}",
                    'error_code': 'NETWORK_ERROR'
                },
                context={'method': method, 'url': url}
            )
            raise LinkedInAPIError(
                f"Network error during API request: {e}",
                error_code='NETWORK_ERROR',
                is_retryable=True
            )
    
    def get_user_profile(self) -> Dict:
        """
        Get the authenticated user's LinkedIn profile using the userinfo endpoint.
        
        Returns:
            Profile data dictionary
            
        Raises:
            LinkedInAPIError: If request fails
        """
        # Use the /userinfo endpoint which works with OpenID Connect scopes
        userinfo_url = f"{self.BASE_URL}/userinfo"
        response = self._make_authenticated_request('GET', userinfo_url)
        
        if response.status_code != 200:
            error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
            error_msg = error_data.get('message', f'HTTP {response.status_code}')
            raise LinkedInAPIError(
                f"Failed to get user profile: {error_msg}",
                error_code=error_data.get('serviceErrorCode'),
                status_code=response.status_code
            )
        
        user_info = response.json()
        
        # Convert userinfo format to expected profile format
        profile = {
            'id': user_info.get('sub'),  # Use 'sub' as the user ID
            'localizedFirstName': user_info.get('given_name', ''),
            'localizedLastName': user_info.get('family_name', ''),
            'email': user_info.get('email', ''),
            'name': user_info.get('name', ''),
            'picture': user_info.get('picture', '')
        }
        
        return profile
    
    def create_post(self, title: str, content: str, url: str, image_url: str = None) -> Dict:
        """
        Create a LinkedIn post with optional image support.
        
        This method automatically handles image upload if image_url is provided,
        falling back to text-only posting if image upload fails.
        
        Args:
            title: Post title
            content: Post content/description
            url: URL to share
            image_url: Optional image URL to include in the post
            
        Returns:
            LinkedIn post response data
            
        Raises:
            LinkedInAPIError: If post creation fails
        """
        if not title and not content:
            raise LinkedInAPIError("Either title or content must be provided")
        
        # Try to create post with image if image_url is provided
        if image_url:
            try:
                logger.info(f"Attempting to create LinkedIn post with image: {image_url}")
                
                # Upload the image first
                media_urn = self.upload_media(image_url)
                
                # Create post with media
                response_data = self.create_post_with_media(title, content, url, media_urn)
                
                # Add media information to response for tracking
                response_data['_media_info'] = {
                    'media_urn': media_urn,
                    'image_url': image_url,
                    'has_media': True
                }
                
                return response_data
                
            except LinkedInAPIError as e:
                logger.warning(f"Failed to create post with image, falling back to text-only: {e.message}")
                
                # Log the image failure for monitoring
                self.error_logger.log_media_upload_error(
                    error_details={
                        'message': e.message,
                        'error_code': e.error_code,
                        'status_code': e.status_code,
                        'image_url': image_url
                    },
                    context={'fallback_to_text': True}
                )
                
                # Continue with text-only post (fallback)
                # Don't re-raise the exception, just log it and continue
            except Exception as e:
                logger.warning(f"Unexpected error creating post with image, falling back to text-only: {e}")
                
                # Log the unexpected error
                self.error_logger.log_media_upload_error(
                    error_details={
                        'message': f"Unexpected error: {str(e)}",
                        'image_url': image_url
                    },
                    context={'fallback_to_text': True}
                )
        
        # Create text-only post (either as fallback or when no image provided)
        logger.info("Creating text-only LinkedIn post")
        response_data = self._create_text_only_post(title, content, url)
        
        # Add media information to response for tracking
        response_data['_media_info'] = {
            'has_media': False,
            'fallback_used': bool(image_url)  # True if we fell back from image to text-only
        }
        
        return response_data
    
    def _create_text_only_post(self, title: str, content: str, url: str) -> Dict:
        """
        Create a text-only LinkedIn post (original functionality).
        
        Args:
            title: Post title
            content: Post content/description
            url: URL to share
            
        Returns:
            LinkedIn post response data
            
        Raises:
            LinkedInAPIError: If post creation fails
        """
        # Get user profile to get person URN
        try:
            profile = self.get_user_profile()
            person_id = profile['id']
            author_urn = f"urn:li:person:{person_id}"
        except LinkedInAPIError as e:
            logger.error(f"Failed to get user profile for posting: {e.message}")
            raise LinkedInAPIError(f"Failed to get user profile: {e.message}")
        
        # Format the post content
        post_text = self._format_post_content(title, content, url)
        
        # Build the post data
        post_data = {
            "author": author_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": post_text
                    },
                    "shareMediaCategory": "ARTICLE"
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }
        
        # Add media if URL is provided
        if url:
            media_data = {
                "status": "READY",
                "originalUrl": url
            }
            
            if title:
                media_data["title"] = {"text": title}
            
            if content:
                media_data["description"] = {"text": content[:300]}  # LinkedIn limit
            
            post_data["specificContent"]["com.linkedin.ugc.ShareContent"]["media"] = [media_data]
        
        # Make the API request
        try:
            response = self._make_authenticated_request(
                'POST',
                self.UGC_POSTS_URL,
                json=post_data
            )
            
            if response.status_code not in [200, 201]:
                error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                error_msg = error_data.get('message', f'HTTP {response.status_code}')
                
                # Extract more specific error information
                if 'serviceErrorCode' in error_data:
                    error_msg = f"{error_msg} (Code: {error_data['serviceErrorCode']})"
                
                raise LinkedInAPIError(
                    f"Failed to create LinkedIn post: {error_msg}",
                    error_code=error_data.get('serviceErrorCode'),
                    status_code=response.status_code
                )
            
            response_data = response.json()
            logger.info(f"Successfully created LinkedIn post: {response_data.get('id', 'Unknown ID')}")
            
            return response_data
            
        except LinkedInAPIError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating LinkedIn post: {e}")
            raise LinkedInAPIError(f"Unexpected error creating LinkedIn post: {e}")
    
    def upload_media(self, image_url: str) -> str:
        """
        Upload media (image) to LinkedIn and return the media URN.
        
        This method handles the complete media upload process:
        1. Register the upload with LinkedIn
        2. Upload the image binary data
        3. Return the media URN for use in posts
        
        Args:
            image_url: URL of the image to upload
            
        Returns:
            LinkedIn media URN (e.g., "urn:li:image:12345")
            
        Raises:
            LinkedInAPIError: If media upload fails
        """
        if not image_url:
            raise LinkedInAPIError("Image URL is required for media upload")
        
        # Check media upload quota
        self._check_media_quota_limits()
        
        try:
            # Get user profile to get person URN
            profile = self.get_user_profile()
            person_id = profile['id']
            owner_urn = f"urn:li:person:{person_id}"
            
            logger.info(f"Starting media upload process for image: {image_url}")
            
            # Step 1: Register upload with LinkedIn
            media_urn = self._register_media_upload(owner_urn)
            
            # Step 2: Download image data
            image_data = self._download_image_data(image_url)
            
            # Step 3: Upload image binary data to LinkedIn
            self._upload_image_binary(media_urn, image_data)
            
            # Update media quota usage
            self._update_media_quota_usage()
            
            logger.info(f"Successfully uploaded media to LinkedIn: {media_urn}")
            return media_urn
            
        except LinkedInAPIError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error uploading media: {e}")
            raise LinkedInAPIError(f"Unexpected error uploading media: {e}")
    
    def _register_media_upload(self, owner_urn: str) -> str:
        """
        Register a media upload with LinkedIn to get upload URL and media URN.
        
        Args:
            owner_urn: URN of the media owner (person or organization)
            
        Returns:
            Media URN for the registered upload
            
        Raises:
            LinkedInAPIError: If registration fails
        """
        register_data = {
            "registerUploadRequest": {
                "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                "owner": owner_urn,
                "serviceRelationships": [
                    {
                        "relationshipType": "OWNER",
                        "identifier": "urn:li:userGeneratedContent"
                    }
                ]
            }
        }
        
        try:
            response = self._make_authenticated_request(
                'POST',
                self.ASSETS_URL + '?action=registerUpload',
                json=register_data
            )
            
            if response.status_code not in [200, 201]:
                error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                error_msg = error_data.get('message', f'HTTP {response.status_code}')
                raise LinkedInAPIError(
                    f"Failed to register media upload: {error_msg}",
                    error_code=error_data.get('serviceErrorCode'),
                    status_code=response.status_code
                )
            
            response_data = response.json()
            upload_mechanism = response_data['value']['uploadMechanism']
            
            # Extract upload URL and media URN
            upload_url = upload_mechanism['com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest']['uploadUrl']
            media_urn = response_data['value']['asset']
            
            # Store upload URL for later use
            self._upload_url = upload_url
            
            logger.debug(f"Registered media upload: {media_urn}")
            return media_urn
            
        except LinkedInAPIError:
            raise
        except Exception as e:
            logger.error(f"Error registering media upload: {e}")
            raise LinkedInAPIError(f"Error registering media upload: {e}")
    
    def _download_image_data(self, image_url: str) -> bytes:
        """
        Download image data from URL.
        
        Args:
            image_url: URL of the image to download
            
        Returns:
            Image binary data
            
        Raises:
            LinkedInAPIError: If download fails
        """
        try:
            logger.debug(f"Downloading image data from: {image_url}")
            
            # Use a separate session for image download to avoid auth headers
            download_session = requests.Session()
            download_session.headers.update({
                'User-Agent': 'Django-Blog-LinkedIn-Integration/1.0'
            })
            
            response = download_session.get(image_url, timeout=60)
            
            if response.status_code != 200:
                raise LinkedInAPIError(
                    f"Failed to download image: HTTP {response.status_code}",
                    status_code=response.status_code
                )
            
            # Validate content type
            content_type = response.headers.get('content-type', '').lower()
            if not content_type.startswith('image/'):
                raise LinkedInAPIError(f"Invalid content type: {content_type}")
            
            # Validate file size (LinkedIn limit is 20MB)
            content_length = len(response.content)
            max_size = 20 * 1024 * 1024  # 20MB
            if content_length > max_size:
                raise LinkedInAPIError(f"Image too large: {content_length} bytes (max: {max_size})")
            
            logger.debug(f"Downloaded image data: {content_length} bytes, type: {content_type}")
            return response.content
            
        except LinkedInAPIError:
            raise
        except requests.RequestException as e:
            logger.error(f"Network error downloading image: {e}")
            raise LinkedInAPIError(f"Network error downloading image: {e}")
        except Exception as e:
            logger.error(f"Error downloading image data: {e}")
            raise LinkedInAPIError(f"Error downloading image data: {e}")
    
    def _upload_image_binary(self, media_urn: str, image_data: bytes) -> None:
        """
        Upload image binary data to LinkedIn using the upload URL.
        
        Args:
            media_urn: Media URN from registration
            image_data: Binary image data
            
        Raises:
            LinkedInAPIError: If upload fails
        """
        if not hasattr(self, '_upload_url') or not self._upload_url:
            raise LinkedInAPIError("No upload URL available - register upload first")
        
        try:
            logger.debug(f"Uploading {len(image_data)} bytes to LinkedIn")
            
            # Upload binary data using PUT request
            # Note: This request should NOT include authorization headers
            upload_session = requests.Session()
            upload_session.headers.update({
                'User-Agent': 'Django-Blog-LinkedIn-Integration/1.0'
            })
            
            response = upload_session.put(
                self._upload_url,
                data=image_data,
                headers={'Content-Type': 'application/octet-stream'},
                timeout=120
            )
            
            if response.status_code not in [200, 201]:
                raise LinkedInAPIError(
                    f"Failed to upload image binary data: HTTP {response.status_code}",
                    status_code=response.status_code
                )
            
            logger.debug(f"Successfully uploaded image binary data for: {media_urn}")
            
        except LinkedInAPIError:
            raise
        except requests.RequestException as e:
            logger.error(f"Network error uploading image binary: {e}")
            raise LinkedInAPIError(f"Network error uploading image binary: {e}")
        except Exception as e:
            logger.error(f"Error uploading image binary: {e}")
            raise LinkedInAPIError(f"Error uploading image binary: {e}")
        finally:
            # Clean up upload URL
            if hasattr(self, '_upload_url'):
                delattr(self, '_upload_url')
    
    def create_post_with_media(self, title: str, content: str, url: str, media_id: str) -> Dict:
        """
        Create a LinkedIn post with attached media (image).
        
        Args:
            title: Post title
            content: Post content/description
            url: URL to share
            media_id: LinkedIn media URN (from upload_media)
            
        Returns:
            LinkedIn post response data
            
        Raises:
            LinkedInAPIError: If post creation fails
        """
        if not title and not content:
            raise LinkedInAPIError("Either title or content must be provided")
        
        if not media_id:
            raise LinkedInAPIError("Media ID is required for media posts")
        
        # Get user profile to get person URN
        try:
            profile = self.get_user_profile()
            person_id = profile['id']
            author_urn = f"urn:li:person:{person_id}"
        except LinkedInAPIError as e:
            logger.error(f"Failed to get user profile for posting: {e.message}")
            raise LinkedInAPIError(f"Failed to get user profile: {e.message}")
        
        # Format the post content
        post_text = self._format_post_content(title, content, url)
        
        # Build the post data with media
        post_data = {
            "author": author_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": post_text
                    },
                    "shareMediaCategory": "IMAGE",
                    "media": [
                        {
                            "status": "READY",
                            "media": media_id
                        }
                    ]
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }
        
        # Add article link if URL is provided
        if url:
            # For posts with images, we can still include the article link in the media
            post_data["specificContent"]["com.linkedin.ugc.ShareContent"]["media"][0].update({
                "originalUrl": url
            })
            
            if title:
                post_data["specificContent"]["com.linkedin.ugc.ShareContent"]["media"][0]["title"] = {
                    "text": title
                }
            
            if content:
                post_data["specificContent"]["com.linkedin.ugc.ShareContent"]["media"][0]["description"] = {
                    "text": content[:300]  # LinkedIn limit
                }
        
        # Make the API request
        try:
            logger.info(f"Creating LinkedIn post with media: {media_id}")
            
            response = self._make_authenticated_request(
                'POST',
                self.UGC_POSTS_URL,
                json=post_data
            )
            
            if response.status_code not in [200, 201]:
                error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                error_msg = error_data.get('message', f'HTTP {response.status_code}')
                
                # Extract more specific error information
                if 'serviceErrorCode' in error_data:
                    error_msg = f"{error_msg} (Code: {error_data['serviceErrorCode']})"
                
                raise LinkedInAPIError(
                    f"Failed to create LinkedIn post with media: {error_msg}",
                    error_code=error_data.get('serviceErrorCode'),
                    status_code=response.status_code
                )
            
            response_data = response.json()
            logger.info(f"Successfully created LinkedIn post with media: {response_data.get('id', 'Unknown ID')}")
            
            return response_data
            
        except LinkedInAPIError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating LinkedIn post with media: {e}")
            raise LinkedInAPIError(f"Unexpected error creating LinkedIn post with media: {e}")
    
    def _check_media_quota_limits(self) -> None:
        """
        Check if we're within media upload quota limits before making requests.
        
        Raises:
            LinkedInRateLimitError: If media quota limits are exceeded
        """
        now = timezone.now()
        
        # Reset daily media quota if it's a new day
        if self._media_quota_reset and (now - self._media_quota_reset).days >= 1:
            self._media_quota_used = 0
            self._media_quota_reset = now
        
        # Check daily media quota
        if self._media_quota_used >= self._media_quota_limit:
            logger.warning(f"LinkedIn daily media quota limit reached: {self._media_quota_used}/{self._media_quota_limit}")
            raise LinkedInRateLimitError(
                f"Daily media upload quota exceeded: {self._media_quota_used}/{self._media_quota_limit}",
                quota_type='daily_media'
            )
    
    def _update_media_quota_usage(self) -> None:
        """Update media quota usage after successful media upload."""
        self._media_quota_used += 1
        if not self._media_quota_reset:
            self._media_quota_reset = timezone.now()
        
        logger.debug(f"LinkedIn media quota usage updated: {self._media_quota_used}/{self._media_quota_limit}")
    
    def _format_post_content(self, title: str, content: str, url: str) -> str:
        """
        Format content for LinkedIn post.
        
        Args:
            title: Post title
            content: Post content/excerpt
            url: Blog post URL
            
        Returns:
            Formatted post text
        """
        # Use the new content formatter for better formatting
        from .linkedin_content_formatter import LinkedInContentFormatter
        
        formatter = LinkedInContentFormatter()
        
        # Create a mock post object for formatting
        class MockPost:
            def __init__(self, title, content, url):
                self.title = title
                self.excerpt = content
                self.content = content
                self.tags = MockTags()
            
            def get_absolute_url(self):
                from urllib.parse import urlparse
                parsed = urlparse(url)
                return parsed.path
        
        class MockTags:
            def exists(self):
                return False
            
            def values_list(self, field, flat=False):
                return []
        
        mock_post = MockPost(title, content, url)
        
        # Format using the content formatter
        formatted_content = formatter.format_post_content(mock_post, include_excerpt=bool(content))
        
        return formatted_content
    
    def test_connection(self) -> Tuple[bool, str]:
        """
        Test the LinkedIn API connection.
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            if not self.is_configured():
                return False, "LinkedIn integration is not configured"
            
            if not self.authenticate():
                return False, "Failed to authenticate with LinkedIn API"
            
            # Try to get user profile as a test
            profile = self.get_user_profile()
            name = f"{profile.get('localizedFirstName', '')} {profile.get('localizedLastName', '')}".strip()
            
            return True, f"Successfully connected to LinkedIn API. Authenticated as: {name or 'Unknown User'}"
            
        except LinkedInAPIError as e:
            return False, f"LinkedIn API error: {e.message}"
        except Exception as e:
            logger.error(f"Unexpected error testing LinkedIn connection: {e}")
            return False, f"Unexpected error: {str(e)}"
    
    def post_blog_article(self, blog_post, attempt_count: int = 1) -> LinkedInPost:
        """
        Post a blog article to LinkedIn with comprehensive error handling and fallback mechanisms.
        
        Args:
            blog_post: Blog Post model instance
            attempt_count: Current attempt number for retry tracking
            
        Returns:
            LinkedInPost instance with posting result
            
        Raises:
            LinkedInAPIError: If posting fails after all fallback attempts
        """
        try:
            from django.contrib.sites.models import Site
        except ImportError:
            # Fallback if sites framework is not installed
            Site = None
        
        # Get or create LinkedIn post tracking record
        linkedin_post, created = LinkedInPost.objects.get_or_create(
            post=blog_post,
            defaults={'status': 'pending'}
        )
        
        if not created and linkedin_post.is_successful():
            logger.info(f"Blog post '{blog_post.title}' already posted to LinkedIn")
            return linkedin_post
        
        # Build the full URL to the blog post
        try:
            if Site:
                current_site = Site.objects.get_current()
                blog_url = f"https://{current_site.domain}{blog_post.get_absolute_url()}"
            else:
                # Fallback to using settings.ALLOWED_HOSTS or a default domain
                from django.conf import settings
                domain = getattr(settings, 'ALLOWED_HOSTS', ['localhost'])[0]
                if domain == '*':
                    domain = 'localhost'
                blog_url = f"https://{domain}{blog_post.get_absolute_url()}"
        except Exception as e:
            logger.error(f"Failed to build blog URL for '{blog_post.title}': {e}")
            blog_url = f"https://localhost{blog_post.get_absolute_url()}"
        
        # Use the content formatter to format the post and get image with enhanced integration
        try:
            from .linkedin_content_formatter import LinkedInContentFormatter
            from .linkedin_image_service import LinkedInImageService
            
            formatter = LinkedInContentFormatter()
            
            # Get comprehensive image information for LinkedIn posting
            image_info = LinkedInImageService.get_image_for_linkedin_post(blog_post, validate=True)
            
            # Format content with image optimization
            formatted_content = formatter.format_post_content(
                blog_post, 
                include_excerpt=True, 
                optimize_for_images=bool(image_info)
            )
            
            # Extract image URL if available
            image_url = image_info.get('url') if image_info else None
            
            if image_info:
                logger.info(f"Found LinkedIn-compatible image for post '{blog_post.title}': {image_url}")
                logger.debug(f"Image metadata: {image_info.get('metadata', {}).get('format')} "
                           f"{image_info.get('metadata', {}).get('width')}x{image_info.get('metadata', {}).get('height')}")
            else:
                logger.info(f"No LinkedIn-compatible image found for post '{blog_post.title}'")
                
        except Exception as e:
            logger.error(f"Failed to format content or get image for '{blog_post.title}': {e}")
            # Fallback to basic formatting
            formatted_content = f"{blog_post.title}\n\n{blog_post.excerpt or blog_post.content[:200]}...\n\nRead more: {blog_url}"
            image_url = None
            image_info = None
        
        # Record the posting attempt
        linkedin_post.record_posting_attempt(
            title=blog_post.title,
            content=formatted_content,
            url=blog_url
        )
        
        # Track comprehensive image information if available
        if image_info and image_url:
            # Store detailed image information
            linkedin_post.image_urls = [image_url]
            linkedin_post.image_upload_status = 'pending'
            
            # Store compatibility information in error message field temporarily for tracking
            compatibility_info = f"Compatible: {image_info.get('linkedin_compatible', False)}"
            if image_info.get('compatibility_issues'):
                compatibility_info += f" | Issues: {', '.join(image_info['compatibility_issues'])}"
            
            linkedin_post.save(update_fields=['image_urls', 'image_upload_status'])
            logger.debug(f"Image tracking info for post '{blog_post.title}': {compatibility_info}")
        else:
            # Determine why no image was selected
            if image_info is None:
                linkedin_post.mark_image_upload_skipped("No suitable image found for post")
            else:
                linkedin_post.mark_image_upload_skipped("Image found but not LinkedIn-compatible")
        
        try:
            logger.info(f"Attempting to post blog article '{blog_post.title}' to LinkedIn (attempt {attempt_count})")
            
            # Enhanced posting workflow with integrated image processing
            if image_url:
                logger.info(f"Posting with image integration for '{blog_post.title}'")
                
                # Validate image one more time before upload (safety check)
                try:
                    is_valid, validation_issues = LinkedInImageService.validate_image_for_linkedin(image_url)
                    if not is_valid:
                        logger.warning(f"Image validation failed during posting for '{blog_post.title}': {validation_issues}")
                        # Continue with text-only posting
                        image_url = None
                        linkedin_post.mark_image_upload_failed(f"Pre-upload validation failed: {', '.join(validation_issues)}")
                except Exception as validation_error:
                    logger.error(f"Image validation error during posting for '{blog_post.title}': {validation_error}")
                    # Continue with text-only posting
                    image_url = None
                    linkedin_post.mark_image_upload_failed(f"Validation error: {str(validation_error)}")
            
            # Create the LinkedIn post using the formatted content and validated image
            response_data = self.create_post(
                title=blog_post.title,
                content=blog_post.excerpt or blog_post.content[:300],
                url=blog_url,
                image_url=image_url
            )
            
            # Extract LinkedIn post ID and URL
            linkedin_post_id = response_data.get('id')
            linkedin_post_url = f"https://www.linkedin.com/feed/update/{linkedin_post_id}/" if linkedin_post_id else None
            
            # Handle comprehensive media information from response
            media_info = response_data.get('_media_info', {})
            
            if media_info.get('has_media'):
                # Post was created with media - record success details
                media_urn = media_info.get('media_urn')
                image_url_used = media_info.get('image_url')
                
                # Store media URNs for tracking
                media_ids = [media_urn] if media_urn else []
                image_urls_used = [image_url_used] if image_url_used else []
                
                linkedin_post.mark_image_upload_success(media_ids, image_urls_used)
                logger.info(f"LinkedIn post created successfully with image: {image_url_used}")
                
            elif media_info.get('fallback_used'):
                # We attempted image upload but fell back to text-only
                linkedin_post.mark_image_upload_failed("Image upload failed during posting, fell back to text-only")
                logger.warning(f"LinkedIn post created without image due to upload failure - fallback successful")
                
            elif image_url:
                # We had an image URL but something went wrong in the posting process
                linkedin_post.mark_image_upload_failed("Image processing failed during LinkedIn post creation")
                logger.warning(f"Image processing failed during posting for '{blog_post.title}'")
            else:
                # No image was provided (expected for text-only posts)
                logger.debug(f"LinkedIn post created as text-only (no image provided) for '{blog_post.title}'")
            
            # Mark the overall posting as successful
            linkedin_post.mark_as_success(linkedin_post_id, linkedin_post_url)
            
            # Log comprehensive success information
            posting_type = "with image" if media_info.get('has_media') else "text-only"
            if media_info.get('fallback_used'):
                posting_type += " (fallback from image failure)"
                
            logger.info(f"Successfully posted blog article '{blog_post.title}' to LinkedIn {posting_type} on attempt {attempt_count}")
            return linkedin_post
            
        except (LinkedInAPIError, LinkedInAuthenticationError, LinkedInRateLimitError, LinkedInContentError) as e:
            logger.error(f"LinkedIn API error posting '{blog_post.title}' (attempt {attempt_count}): {e.message}")
            
            # Enhanced error handling for image-related failures
            error_context = {
                'had_image': bool(image_url),
                'image_url': image_url,
                'error_type': type(e).__name__,
                'error_code': getattr(e, 'error_code', None),
                'is_retryable': getattr(e, 'is_retryable', False)
            }
            
            # Mark image upload as failed if we had an image
            if image_url:
                linkedin_post.mark_image_upload_failed(f"LinkedIn API error during image posting: {e.message}")
            
            # Attempt fallback mechanisms with enhanced context
            fallback_result = self._implement_fallback_mechanism(e, blog_post, attempt_count)
            
            if fallback_result.get('fallback_success'):
                # Fallback succeeded
                linkedin_post_id = fallback_result.get('linkedin_post_id')
                linkedin_post_url = f"https://www.linkedin.com/feed/update/{linkedin_post_id}/" if linkedin_post_id else None
                
                linkedin_post.mark_as_success(linkedin_post_id, linkedin_post_url)
                
                # Enhanced error message with image context
                error_msg = f"Posted via fallback: {fallback_result['fallback_message']}"
                if error_context['had_image']:
                    error_msg += f" | Original error with image: {e.message}"
                
                linkedin_post.error_message = error_msg
                linkedin_post.save(update_fields=['error_message'])
                
                logger.info(f"Successfully posted '{blog_post.title}' via fallback mechanism: {fallback_result['fallback_type']}")
                return linkedin_post
            else:
                # Fallback failed or not applicable - provide comprehensive error information
                error_msg = f"{e.message} | Fallback: {fallback_result.get('fallback_message', 'No fallback available')}"
                if error_context['had_image']:
                    error_msg += f" | Image processing: Failed during posting"
                
                linkedin_post.mark_as_failed(
                    error_message=error_msg,
                    error_code=e.error_code,
                    can_retry=e.is_retryable
                )
                
                logger.error(f"Failed to post '{blog_post.title}' after fallback attempt: {fallback_result.get('fallback_message')}")
                raise
        
        except Exception as e:
            logger.error(f"Unexpected error posting blog article '{blog_post.title}' to LinkedIn: {e}")
            
            # Mark image upload as failed if we had an image
            if image_url:
                linkedin_post.mark_image_upload_failed(f"Unexpected error during image posting: {str(e)}")
            
            # Try basic fallback for unexpected errors with enhanced error handling
            try:
                fallback_result = self._implement_fallback_mechanism(
                    LinkedInAPIError(f"Unexpected error: {str(e)}", is_retryable=True),
                    blog_post,
                    attempt_count
                )
                
                error_msg = f"Unexpected error: {str(e)} | Fallback: {fallback_result.get('fallback_message', 'No fallback available')}"
                if image_url:
                    error_msg += f" | Image processing: Failed due to unexpected error"
                
                linkedin_post.mark_as_failed(
                    error_message=error_msg,
                    can_retry=True
                )
            except:
                error_msg = f"Unexpected error: {str(e)}"
                if image_url:
                    error_msg += f" | Image processing: Failed due to unexpected error"
                    
                linkedin_post.mark_as_failed(
                    error_message=error_msg,
                    can_retry=True
                )
            
            raise LinkedInAPIError(f"Unexpected error: {str(e)}", is_retryable=True)