"""
Middleware for blog security and performance optimizations.

This module provides middleware classes for rate limiting, security headers,
and performance monitoring.
"""

import time
import json
from django.http import HttpResponse, JsonResponse
from django.core.cache import cache
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
from .security import RateLimitTracker, SecurityHeaders, SecurityAuditLogger
from .performance import PerformanceMonitor
from typing import Dict, Optional


class SecurityHeadersMiddleware(MiddlewareMixin):
    """Add security headers to all responses"""
    
    def process_response(self, request, response):
        """Add security headers to response"""
        security_headers = SecurityHeaders.get_security_headers()
        
        for header, value in security_headers.items():
            response[header] = value
        
        return response


class RateLimitMiddleware(MiddlewareMixin):
    """Rate limiting middleware for blog actions"""
    
    def __init__(self, get_response=None):
        super().__init__(get_response)
        self.rate_limiter = RateLimitTracker()
        
        # Rate limit configurations
        self.rate_limits = {
            'comment_submission': {
                'limit': 5,
                'window': 300,  # 5 minutes
                'paths': ['/blog/comment/', '/blog/reply/']
            },
            'newsletter_subscription': {
                'limit': 3,
                'window': 3600,  # 1 hour
                'paths': ['/blog/subscribe/']
            },
            'search_requests': {
                'limit': 30,
                'window': 300,  # 5 minutes
                'paths': ['/blog/search/', '/blog/advanced-search/']
            },
            'social_share_tracking': {
                'limit': 20,
                'window': 300,  # 5 minutes
                'paths': ['/blog/track-share/']
            }
        }
    
    def process_request(self, request):
        """Check rate limits before processing request"""
        # Skip rate limiting for authenticated staff users
        if hasattr(request, 'user') and request.user.is_authenticated and request.user.is_staff:
            return None
        
        # Get client identifier
        client_ip = self._get_client_ip(request)
        
        # Check each rate limit configuration
        for action, config in self.rate_limits.items():
            if any(path in request.path for path in config['paths']):
                if self.rate_limiter.is_rate_limited(
                    client_ip, 
                    action, 
                    config['limit'], 
                    config['window']
                ):
                    # Log rate limit violation
                    SecurityAuditLogger.log_rate_limit_exceeded(
                        request, action, client_ip
                    )
                    
                    # Return rate limit response
                    if request.headers.get('Accept') == 'application/json':
                        return JsonResponse({
                            'error': 'Rate limit exceeded',
                            'retry_after': config['window']
                        }, status=429)
                    else:
                        response = HttpResponse(
                            "Rate limit exceeded. Please try again later.",
                            status=429
                        )
                        response['Retry-After'] = str(config['window'])
                        return response
        
        return None
    
    def _get_client_ip(self, request) -> str:
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip or 'unknown'


class PerformanceMonitoringMiddleware(MiddlewareMixin):
    """Monitor request performance and log slow requests"""
    
    def process_request(self, request):
        """Record request start time"""
        request._performance_start_time = time.time()
        return None
    
    def process_response(self, request, response):
        """Monitor response time and log slow requests"""
        if hasattr(request, '_performance_start_time'):
            duration = time.time() - request._performance_start_time
            
            # Log slow requests (> 2 seconds)
            if duration > 2.0:
                import logging
                logger = logging.getLogger('blog.performance')
                logger.warning(
                    f"Slow request: {request.method} {request.path} "
                    f"took {duration:.2f}s"
                )
            
            # Add performance header for debugging
            if settings.DEBUG:
                response['X-Response-Time'] = f"{duration:.3f}s"
        
        return response


class ContentSecurityMiddleware(MiddlewareMixin):
    """Enhanced content security middleware"""
    
    def __init__(self, get_response=None):
        super().__init__(get_response)
        self.suspicious_patterns = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'vbscript:',
            r'data:text/html',
            r'on\w+\s*=',
        ]
    
    def process_request(self, request):
        """Scan request for malicious content"""
        if request.method in ['POST', 'PUT', 'PATCH']:
            # Check POST data for suspicious patterns
            if self._contains_suspicious_content(request.POST):
                SecurityAuditLogger.log_suspicious_activity(
                    request,
                    'malicious_content_attempt',
                    {'data_type': 'POST'}
                )
                
                return JsonResponse({
                    'error': 'Request contains potentially malicious content'
                }, status=400)
        
        return None
    
    def _contains_suspicious_content(self, data) -> bool:
        """Check if data contains suspicious patterns"""
        import re
        
        for key, value in data.items():
            if isinstance(value, str):
                for pattern in self.suspicious_patterns:
                    if re.search(pattern, value, re.IGNORECASE):
                        return True
        
        return False


class CacheControlMiddleware(MiddlewareMixin):
    """Add appropriate cache control headers"""
    
    def __init__(self, get_response=None):
        super().__init__(get_response)
        
        # Cache control configurations for different URL patterns
        self.cache_configs = {
            '/blog/': {
                'max_age': 300,  # 5 minutes
                'public': True
            },
            '/blog/category/': {
                'max_age': 600,  # 10 minutes
                'public': True
            },
            '/blog/tag/': {
                'max_age': 600,  # 10 minutes
                'public': True
            },
            '/blog/author/': {
                'max_age': 1800,  # 30 minutes
                'public': True
            },
            '/static/': {
                'max_age': 86400,  # 1 day
                'public': True
            },
            '/media/': {
                'max_age': 3600,  # 1 hour
                'public': True
            }
        }
    
    def process_response(self, request, response):
        """Add cache control headers based on URL patterns"""
        # Skip for authenticated users or POST requests
        if (hasattr(request, 'user') and request.user.is_authenticated) or request.method != 'GET':
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            return response
        
        # Find matching cache configuration
        for url_pattern, config in self.cache_configs.items():
            if request.path.startswith(url_pattern):
                cache_control_parts = []
                
                if config.get('public'):
                    cache_control_parts.append('public')
                else:
                    cache_control_parts.append('private')
                
                if config.get('max_age'):
                    cache_control_parts.append(f"max-age={config['max_age']}")
                
                response['Cache-Control'] = ', '.join(cache_control_parts)
                break
        
        return response


class CommentSpamProtectionMiddleware(MiddlewareMixin):
    """Additional spam protection for comments"""
    
    def __init__(self, get_response=None):
        super().__init__(get_response)
        self.spam_indicators = [
            'viagra', 'cialis', 'casino', 'poker', 'lottery',
            'make money', 'earn money', 'get rich', 'work from home',
            'click here', 'visit now', 'act now', 'limited time'
        ]
    
    def process_request(self, request):
        """Check comment submissions for spam"""
        if (request.method == 'POST' and 
            '/blog/comment/' in request.path):
            
            content = request.POST.get('content', '').lower()
            
            # Check for spam indicators
            spam_score = 0
            for indicator in self.spam_indicators:
                if indicator in content:
                    spam_score += 1
            
            # If high spam score, block the request
            if spam_score >= 3:
                SecurityAuditLogger.log_spam_attempt(
                    request, 'comment', content[:100]
                )
                
                return JsonResponse({
                    'error': 'Comment appears to be spam'
                }, status=400)
        
        return None


class CSRFEnhancementMiddleware(MiddlewareMixin):
    """Enhanced CSRF protection"""
    
    def process_request(self, request):
        """Additional CSRF validation for sensitive operations"""
        # Skip for GET requests
        if request.method == 'GET':
            return None
        
        # Check for AJAX requests without proper CSRF token
        if (request.headers.get('X-Requested-With') == 'XMLHttpRequest' and
            not request.META.get('HTTP_X_CSRFTOKEN')):
            
            SecurityAuditLogger.log_suspicious_activity(
                request,
                'missing_csrf_token',
                {'path': request.path}
            )
        
        return None


class RequestLoggingMiddleware(MiddlewareMixin):
    """Log requests for security monitoring"""
    
    def __init__(self, get_response=None):
        super().__init__(get_response)
        self.logged_paths = [
            '/blog/comment/',
            '/blog/subscribe/',
            '/blog/track-share/'
        ]
    
    def process_request(self, request):
        """Log sensitive requests"""
        if any(path in request.path for path in self.logged_paths):
            import logging
            logger = logging.getLogger('blog.security')
            
            log_data = {
                'method': request.method,
                'path': request.path,
                'ip': self._get_client_ip(request),
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'timestamp': time.time()
            }
            
            logger.info(f"Request logged: {log_data}")
        
        return None
    
    def _get_client_ip(self, request) -> str:
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip or 'unknown'