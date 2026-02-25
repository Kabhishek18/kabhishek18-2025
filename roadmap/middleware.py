"""
Middleware for Resume Parser functionality
"""
import time
import logging
from django.core.cache import cache
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
from rest_framework import status

logger = logging.getLogger(__name__)


class ResumeParserRateLimitMiddleware(MiddlewareMixin):
    """
    Rate limiting middleware specifically for Resume Parser endpoints
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)
    
    def process_request(self, request):
        """
        Check rate limits for Resume Parser endpoints
        """
        # Only apply to Resume Parser endpoints
        if not request.path.startswith('/api/roadmap/'):
            return None
        
        # Skip rate limiting for authenticated API clients with higher limits
        if hasattr(request, 'user') and hasattr(request.user, 'client'):
            return None
        
        # Get client IP
        client_ip = self.get_client_ip(request)
        
        # Check rate limits
        if self.is_rate_limited(client_ip, request.path):
            return JsonResponse(
                {
                    'error': {
                        'code': 'RATE_LIMIT_EXCEEDED',
                        'message': 'Rate limit exceeded for Resume Parser API',
                        'details': {
                            'limit': '10 requests per minute for anonymous users',
                            'retry_after': 60
                        }
                    }
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        
        return None
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def is_rate_limited(self, client_ip, path):
        """
        Check if client is rate limited
        """
        # Different limits for different endpoints
        if 'parse-resume' in path:
            limit = 5  # 5 resume parsing requests per minute
            window = 60
        elif 'health' in path:
            limit = 30  # 30 health check requests per minute
            window = 60
        else:
            limit = 10  # 10 general requests per minute
            window = 60
        
        cache_key = f"resume_parser_rate_limit:{client_ip}:{path}"
        
        # Get current count
        current_count = cache.get(cache_key, 0)
        
        if current_count >= limit:
            return True
        
        # Increment count
        cache.set(cache_key, current_count + 1, window)
        return False


class ResumeParserLoggingMiddleware(MiddlewareMixin):
    """
    Logging middleware for Resume Parser requests
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)
    
    def process_request(self, request):
        """Log incoming requests to Resume Parser endpoints"""
        if request.path.startswith('/api/roadmap/'):
            request._resume_parser_start_time = time.time()
            
            # Log request details (without sensitive data)
            client_ip = self.get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', 'Unknown')
            
            logger.info(
                f"Resume Parser API Request - "
                f"Path: {request.path}, "
                f"Method: {request.method}, "
                f"IP: {client_ip}, "
                f"User-Agent: {user_agent[:100]}..."  # Truncate user agent
            )
        
        return None
    
    def process_response(self, request, response):
        """Log response details"""
        if hasattr(request, '_resume_parser_start_time'):
            processing_time = time.time() - request._resume_parser_start_time
            
            # Log response details
            logger.info(
                f"Resume Parser API Response - "
                f"Path: {request.path}, "
                f"Status: {response.status_code}, "
                f"Processing Time: {processing_time:.3f}s"
            )
            
            # Log performance warnings
            if processing_time > 30:  # More than 30 seconds
                logger.warning(
                    f"Slow Resume Parser API Response - "
                    f"Path: {request.path}, "
                    f"Processing Time: {processing_time:.3f}s"
                )
        
        return response
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class ResumeParserSecurityMiddleware(MiddlewareMixin):
    """
    Security middleware for Resume Parser endpoints
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)
    
    def process_request(self, request):
        """Apply security checks for Resume Parser endpoints"""
        if not request.path.startswith('/api/roadmap/'):
            return None
        
        # Check file upload size for parse-resume endpoint
        if 'parse-resume' in request.path and request.method == 'POST':
            content_length = request.META.get('CONTENT_LENGTH')
            if content_length:
                try:
                    content_length = int(content_length)
                    max_size = getattr(settings, 'RESUME_PARSER_SETTINGS', {}).get('MAX_FILE_SIZE_MB', 10) * 1024 * 1024
                    
                    if content_length > max_size:
                        return JsonResponse(
                            {
                                'error': {
                                    'code': 'FILE_TOO_LARGE',
                                    'message': 'File size exceeds maximum limit',
                                    'details': {
                                        'max_size_mb': max_size / (1024 * 1024),
                                        'received_size_mb': content_length / (1024 * 1024)
                                    }
                                }
                            },
                            status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
                        )
                except ValueError:
                    pass
        
        # Add security headers
        return None
    
    def process_response(self, request, response):
        """Add security headers to Resume Parser responses"""
        if request.path.startswith('/api/roadmap/'):
            # Add security headers
            response['X-Content-Type-Options'] = 'nosniff'
            response['X-Frame-Options'] = 'DENY'
            response['X-XSS-Protection'] = '1; mode=block'
            
            # Add CORS headers if needed
            if hasattr(settings, 'CORS_ALLOWED_ORIGINS'):
                origin = request.META.get('HTTP_ORIGIN')
                if origin in settings.CORS_ALLOWED_ORIGINS:
                    response['Access-Control-Allow-Origin'] = origin
                    response['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
                    response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Client-ID, X-API-Key'
        
        return response